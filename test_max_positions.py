"""
Test impact of max_positions limit on portfolio performance.

Simulates trading with position limits (5, 8, 10, 15, unlimited) to see
if allowing more concurrent positions improves total returns.

Usage:
    python test_max_positions.py --symbols TSLA DIS GOOGL JNJ JPM LLY META AMZN SPY --lookback 900
"""
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from src.backtest.ema_backtest import download_data
from src.live.technical_indicators import (
    calculate_rsi, calculate_macd, calculate_volume_ma, score_trade
)


def backtest_portfolio_with_limit(
    symbols: List[str],
    lookback: int = 900,
    max_positions: int = None,
    min_score: int = 40,
    tp_pct: float = 0.06,
    sl_pct: float = 0.03,
    initial_equity: float = 100000.0
) -> dict:
    """
    Backtest portfolio with max concurrent positions limit.
    
    Args:
        symbols: List of symbols to trade
        lookback: Days of historical data
        max_positions: Max concurrent trades (None = unlimited)
        min_score: Minimum indicator score to enter
        tp_pct: Take profit percentage
        sl_pct: Stop loss percentage
        initial_equity: Starting portfolio value
    
    Returns:
        dict with metrics: total_trades, total_pnl_pct, win_rate, avg_holding_days
    """
    
    # Download and prepare all data
    data = {}
    for symbol in symbols:
        df = download_data(symbol, days=lookback)
        if df is None or len(df) < 110:
            print(f"[SKIP] {symbol} - insufficient data")
            continue
        
        # Add indicators
        df["RSI"] = calculate_rsi(df["Close"], period=14)
        macd_line, signal_line, histogram = calculate_macd(df["Close"])
        df["MACD_Hist"] = histogram
        df["Volume_MA"] = calculate_volume_ma(df["Volume"], period=20)
        df["Volume_Ratio"] = df["Volume"] / (df["Volume_MA"] + 1e-8)
        
        # EMA signals
        df["EMA_fast"] = df["Close"].ewm(span=10, adjust=False).mean()
        df["EMA_slow"] = df["Close"].ewm(span=100, adjust=False).mean()
        df["EMA_signal"] = 0
        df.loc[df["EMA_fast"] > df["EMA_slow"], "EMA_signal"] = 1
        df.loc[df["EMA_fast"] < df["EMA_slow"], "EMA_signal"] = -1
        
        # Support/Resistance
        support_list = []
        resistance_list = []
        for i in range(len(df)):
            if i < 20:
                support_list.append(None)
                resistance_list.append(None)
            else:
                recent = df.iloc[max(0, i-20):i]
                support_list.append(recent["Low"].min())
                resistance_list.append(recent["High"].max())
        df["Support"] = support_list
        df["Resistance"] = resistance_list
        
        # S/R signal
        def detect_sr(row):
            if pd.isna(row["Support"]) or pd.isna(row["Resistance"]):
                return 0
            price = row["Close"]
            support = row["Support"]
            resistance = row["Resistance"]
            threshold = 0.02
            if abs(price - support) / support < threshold:
                return 1
            elif abs(price - resistance) / resistance < threshold:
                return -1
            return 0
        
        df["SR_signal"] = df.apply(detect_sr, axis=1)
        
        # Score each bar
        scores = []
        for idx, row in df.iterrows():
            ema_sig = row["EMA_signal"]
            rsi = row["RSI"] if not pd.isna(row["RSI"]) else 50.0
            macd_hist = row["MACD_Hist"] if not pd.isna(row["MACD_Hist"]) else 0.0
            sr_sig = row["SR_signal"]
            vol_ratio = row["Volume_Ratio"] if not pd.isna(row["Volume_Ratio"]) else 1.0
            
            s = score_trade(df, ema_sig, rsi, macd_hist, sr_sig, vol_ratio)
            scores.append(s)
        
        df["Score"] = scores
        
        # Detect crossovers
        df["Signal_prev"] = df["EMA_signal"].shift(1).fillna(0)
        df["Crossover"] = (df["EMA_signal"] != df["Signal_prev"]) & (df["EMA_signal"] != 0)
        
        data[symbol] = df
    
    if not data:
        return {"total_trades": 0, "total_pnl_pct": 0.0, "win_rate": 0.0, "avg_holding_days": 0.0, "max_concurrent": 0}
    
    # Merge all dates
    all_dates = set()
    for df in data.values():
        all_dates.update(df["Date"].tolist())
    all_dates = sorted(all_dates)
    
    # Portfolio simulation with equity tracking
    open_positions = []  # [(symbol, entry_date, entry_price, entry_signal, position_size)]
    completed_trades = []
    equity_curve = [initial_equity]
    current_equity = initial_equity
    
    for date in all_dates:
        # Check exits for open positions
        for pos in open_positions[:]:
            symbol, entry_date, entry_price, entry_signal, position_size = pos
            df = data[symbol]
            current_bar = df[df["Date"] == date]
            
            if current_bar.empty:
                continue
            
            current_price = current_bar.iloc[0]["Close"]
            pnl_pct = (current_price - entry_price) / entry_price
            
            exit_triggered = False
            reason = None
            
            # TP/SL
            if entry_signal == 1:
                if pnl_pct >= tp_pct:
                    exit_triggered = True
                    reason = "TP"
                elif pnl_pct <= -sl_pct:
                    exit_triggered = True
                    reason = "SL"
            elif entry_signal == -1:
                if pnl_pct <= -tp_pct:
                    exit_triggered = True
                    reason = "TP"
                elif pnl_pct >= sl_pct:
                    exit_triggered = True
                    reason = "SL"
            
            if exit_triggered:
                pnl_dollars = position_size * pnl_pct
                current_equity += pnl_dollars
                
                holding_days = (date - entry_date).days
                completed_trades.append({
                    "symbol": symbol,
                    "entry_date": entry_date,
                    "exit_date": date,
                    "pnl_pct": pnl_pct,
                    "pnl_dollars": pnl_dollars,
                    "holding_days": holding_days,
                    "reason": reason
                })
                open_positions.remove(pos)
        
        # Check entries (respect max_positions limit)
        for symbol, df in data.items():
            current_bar = df[df["Date"] == date]
            
            if current_bar.empty:
                continue
            
            row = current_bar.iloc[0]
            
            # Check if crossover + score >= min_score
            if row["Crossover"] and row["Score"] >= min_score:
                # Check if already in position for this symbol
                if any(p[0] == symbol for p in open_positions):
                    continue
                
                # Check max_positions limit
                if max_positions is not None and len(open_positions) >= max_positions:
                    continue
                
                # Calculate position size (1.5% risk)
                position_size = current_equity * 0.015
                
                # Enter position
                open_positions.append((symbol, date, row["Close"], row["EMA_signal"], position_size))
        
        equity_curve.append(current_equity)
    
    # Metrics
    if len(completed_trades) == 0:
        return {"total_trades": 0, "total_pnl_pct": 0.0, "win_rate": 0.0, "avg_holding_days": 0.0, "max_concurrent": 0}
    
    total_trades = len(completed_trades)
    wins = sum(1 for t in completed_trades if t["pnl_pct"] > 0)
    win_rate = wins / total_trades * 100
    
    # REALISTIC P&L: (final equity - initial equity) / initial equity
    total_pnl_dollars = sum(t["pnl_dollars"] for t in completed_trades)
    total_pnl_pct = (total_pnl_dollars / initial_equity) * 100
    
    avg_holding_days = sum(t["holding_days"] for t in completed_trades) / total_trades
    
    # Calculate max concurrent positions ever reached
    # Re-simulate to track this
    open_count_by_date = {}
    for trade in completed_trades:
        for d in pd.date_range(trade["entry_date"], trade["exit_date"]):
            open_count_by_date[d] = open_count_by_date.get(d, 0) + 1
    
    max_concurrent = max(open_count_by_date.values()) if open_count_by_date else 0
    
    return {
        "total_trades": total_trades,
        "total_pnl_pct": total_pnl_pct,
        "win_rate": win_rate,
        "avg_holding_days": avg_holding_days,
        "max_concurrent": max_concurrent
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test max_positions impact on portfolio")
    parser.add_argument("--symbols", nargs="+", required=True, help="Symbols to trade")
    parser.add_argument("--lookback", type=int, default=900, help="Days to backtest")
    parser.add_argument("--min-score", type=int, default=40, help="Minimum score to enter (0-100)")
    args = parser.parse_args()
    
    print(f"\n{'='*80}")
    print(f"TESTING MAX_POSITIONS IMPACT")
    print(f"{'='*80}")
    print(f"Symbols: {len(args.symbols)} | Lookback: {args.lookback} days | Min Score: {args.min_score}")
    print(f"{'='*80}\n")
    
    limits = [5, 8, 10, 15, None]  # Test different position limits
    results = {}
    
    for limit in limits:
        limit_str = str(limit) if limit is not None else "Unlimited"
        print(f"[TEST] Max Positions = {limit_str}... ", end="", flush=True)
        
        result = backtest_portfolio_with_limit(
            symbols=args.symbols,
            lookback=args.lookback,
            max_positions=limit,
            min_score=args.min_score
        )
        
        results[limit_str] = result
        print(f"✓ {result['total_trades']} trades, {result['total_pnl_pct']:.2f}% P&L, {result['win_rate']:.1f}% WR")
    
    # Summary table
    print(f"\n{'='*80}")
    print(f"RESULTS SUMMARY")
    print(f"{'='*80}")
    print(f"{'Max Pos':<12} {'Trades':<10} {'Total P&L%':<12} {'Win%':<10} {'Avg Days':<10} {'Peak Concurrent':<15}")
    print(f"{'-'*80}")
    
    for limit_str, r in results.items():
        print(f"{limit_str:<12} {r['total_trades']:<10} {r['total_pnl_pct']:<12.2f} {r['win_rate']:<10.1f} {r['avg_holding_days']:<10.1f} {r['max_concurrent']:<15}")
    
    # Analysis
    print(f"\n{'='*80}")
    print(f"ANALYSIS")
    print(f"{'='*80}")
    
    unlimited_pnl = results["Unlimited"]["total_pnl_pct"]
    limit_5_pnl = results["5"]["total_pnl_pct"]
    limit_8_pnl = results["8"]["total_pnl_pct"]
    
    print(f"📊 Unlimited vs 5 positions: {unlimited_pnl - limit_5_pnl:+.2f}% difference")
    print(f"📊 Unlimited vs 8 positions: {unlimited_pnl - limit_8_pnl:+.2f}% difference")
    print(f"📊 8 vs 5 positions: {limit_8_pnl - limit_5_pnl:+.2f}% difference")
    
    if limit_8_pnl > limit_5_pnl:
        improvement = ((limit_8_pnl - limit_5_pnl) / abs(limit_5_pnl)) * 100 if limit_5_pnl != 0 else 0
        print(f"\n✅ Increasing from 5→8 positions IMPROVES returns by {improvement:.1f}%")
    else:
        decline = ((limit_5_pnl - limit_8_pnl) / abs(limit_5_pnl)) * 100 if limit_5_pnl != 0 else 0
        print(f"\n⚠️  Increasing from 5→8 positions REDUCES returns by {decline:.1f}%")
    
    if results["Unlimited"]["total_pnl_pct"] > results["8"]["total_pnl_pct"]:
        print(f"✅ Removing limit further improves returns - consider 10 or 15 positions")
    else:
        print(f"⚠️  Position limit is NOT the bottleneck - focus on signal quality instead")
    
    print(f"{'='*80}\n")
