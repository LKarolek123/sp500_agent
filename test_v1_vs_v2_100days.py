"""
V1 vs V2 comparison over 100-day period.

Compares:
  - V1: 5 max positions, no indicators, TP/SL only
  - V2: 10 max positions, ML indicators, TP/SL only

Metrics:
  - Total P&L%
  - Win rate
  - Total trades
  - Max drawdown (peak-to-trough)
  - Average trade duration

Usage:
    python test_v1_vs_v2_100days.py --symbols TSLA DIS GOOGL JNJ JPM LLY META AMZN SPY
"""
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from src.backtest.ema_backtest import download_data
from src.live.technical_indicators import (
    calculate_rsi, calculate_macd, calculate_volume_ma, score_trade
)


def calculate_max_drawdown(equity_curve: List[float]) -> float:
    """Calculate maximum drawdown from equity curve."""
    if not equity_curve or len(equity_curve) < 2:
        return 0.0
    
    peak = equity_curve[0]
    max_dd = 0.0
    
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak
        if dd > max_dd:
            max_dd = dd
    
    return max_dd * 100  # Return as percentage


def backtest_v1(
    symbols: List[str],
    lookback: int = 100,
    max_positions: int = 5,
    tp_pct: float = 0.06,
    sl_pct: float = 0.03,
    initial_equity: float = 100000.0
) -> dict:
    """
    V1: Baseline EMA crossover, TP/SL only, no indicators.
    """
    # Download and prepare data
    data = {}
    for symbol in symbols:
        df = download_data(symbol, days=lookback + 100)  # Extra buffer for EMA calculation
        if df is None or len(df) < 110:
            continue
        
        # EMA signals
        df["EMA_fast"] = df["Close"].ewm(span=10, adjust=False).mean()
        df["EMA_slow"] = df["Close"].ewm(span=100, adjust=False).mean()
        df["EMA_signal"] = 0
        df.loc[df["EMA_fast"] > df["EMA_slow"], "EMA_signal"] = 1
        df.loc[df["EMA_fast"] < df["EMA_slow"], "EMA_signal"] = -1
        
        # Detect crossovers
        df["Signal_prev"] = df["EMA_signal"].shift(1).fillna(0)
        df["Crossover"] = (df["EMA_signal"] != df["Signal_prev"]) & (df["EMA_signal"] != 0)
        
        # Keep only last lookback days
        df = df.tail(lookback).copy()
        data[symbol] = df
    
    if not data:
        return {"total_trades": 0, "total_pnl_pct": 0.0, "win_rate": 0.0, "max_drawdown": 0.0, "avg_holding_days": 0.0}
    
    # Get all dates
    all_dates = set()
    for df in data.values():
        all_dates.update(df["Date"].tolist())
    all_dates = sorted(all_dates)
    
    # Portfolio simulation
    open_positions = []
    completed_trades = []
    equity_curve = [initial_equity]
    current_equity = initial_equity
    
    for date in all_dates:
        # Check exits
        for pos in open_positions[:]:
            symbol, entry_date, entry_price, entry_signal, position_size = pos
            df = data[symbol]
            current_bar = df[df["Date"] == date]
            
            if current_bar.empty:
                continue
            
            current_price = current_bar.iloc[0]["Close"]
            pnl_pct = (current_price - entry_price) / entry_price
            
            exit_triggered = False
            
            # TP/SL
            if entry_signal == 1:
                if pnl_pct >= tp_pct:
                    exit_triggered = True
                elif pnl_pct <= -sl_pct:
                    exit_triggered = True
            elif entry_signal == -1:
                if pnl_pct <= -tp_pct:
                    exit_triggered = True
                elif pnl_pct >= sl_pct:
                    exit_triggered = True
            
            if exit_triggered:
                pnl_dollars = position_size * pnl_pct
                current_equity += pnl_dollars
                
                holding_days = (date - entry_date).days
                completed_trades.append({
                    "symbol": symbol,
                    "pnl_pct": pnl_pct,
                    "pnl_dollars": pnl_dollars,
                    "holding_days": holding_days
                })
                open_positions.remove(pos)
        
        # Check entries
        for symbol, df in data.items():
            current_bar = df[df["Date"] == date]
            
            if current_bar.empty:
                continue
            
            row = current_bar.iloc[0]
            
            if row["Crossover"]:
                # Check if already in position
                if any(p[0] == symbol for p in open_positions):
                    continue
                
                # Check max_positions limit
                if len(open_positions) >= max_positions:
                    continue
                
                # Calculate position size (0.8% risk)
                position_size = current_equity * 0.008
                
                open_positions.append((symbol, date, row["Close"], row["EMA_signal"], position_size))
        
        equity_curve.append(current_equity)
    
    # Metrics
    if len(completed_trades) == 0:
        return {"total_trades": 0, "total_pnl_pct": 0.0, "win_rate": 0.0, "max_drawdown": 0.0, "avg_holding_days": 0.0}
    
    total_trades = len(completed_trades)
    wins = sum(1 for t in completed_trades if t["pnl_pct"] > 0)
    win_rate = wins / total_trades * 100
    total_pnl_dollars = sum(t["pnl_dollars"] for t in completed_trades)
    total_pnl_pct = (total_pnl_dollars / initial_equity) * 100
    avg_holding_days = sum(t["holding_days"] for t in completed_trades) / total_trades
    max_drawdown = calculate_max_drawdown(equity_curve)
    
    return {
        "total_trades": total_trades,
        "total_pnl_pct": total_pnl_pct,
        "win_rate": win_rate,
        "max_drawdown": max_drawdown,
        "avg_holding_days": avg_holding_days
    }


def backtest_v2(
    symbols: List[str],
    lookback: int = 100,
    max_positions: int = 10,
    min_score: int = 40,
    tp_pct: float = 0.06,
    sl_pct: float = 0.03,
    initial_equity: float = 100000.0
) -> dict:
    """
    V2: EMA + ML indicators, TP/SL only, 10 max positions.
    """
    # Download and prepare data
    data = {}
    for symbol in symbols:
        df = download_data(symbol, days=lookback + 100)
        if df is None or len(df) < 110:
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
        
        # S/R
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
        
        # Keep only last lookback days
        df = df.tail(lookback).copy()
        data[symbol] = df
    
    if not data:
        return {"total_trades": 0, "total_pnl_pct": 0.0, "win_rate": 0.0, "max_drawdown": 0.0, "avg_holding_days": 0.0}
    
    # Get all dates
    all_dates = set()
    for df in data.values():
        all_dates.update(df["Date"].tolist())
    all_dates = sorted(all_dates)
    
    # Portfolio simulation
    open_positions = []
    completed_trades = []
    equity_curve = [initial_equity]
    current_equity = initial_equity
    
    for date in all_dates:
        # Check exits
        for pos in open_positions[:]:
            symbol, entry_date, entry_price, entry_signal, position_size = pos
            df = data[symbol]
            current_bar = df[df["Date"] == date]
            
            if current_bar.empty:
                continue
            
            current_price = current_bar.iloc[0]["Close"]
            pnl_pct = (current_price - entry_price) / entry_price
            
            exit_triggered = False
            
            # TP/SL
            if entry_signal == 1:
                if pnl_pct >= tp_pct:
                    exit_triggered = True
                elif pnl_pct <= -sl_pct:
                    exit_triggered = True
            elif entry_signal == -1:
                if pnl_pct <= -tp_pct:
                    exit_triggered = True
                elif pnl_pct >= sl_pct:
                    exit_triggered = True
            
            if exit_triggered:
                pnl_dollars = position_size * pnl_pct
                current_equity += pnl_dollars
                
                holding_days = (date - entry_date).days
                completed_trades.append({
                    "symbol": symbol,
                    "pnl_pct": pnl_pct,
                    "pnl_dollars": pnl_dollars,
                    "holding_days": holding_days
                })
                open_positions.remove(pos)
        
        # Check entries (with score filter)
        for symbol, df in data.items():
            current_bar = df[df["Date"] == date]
            
            if current_bar.empty:
                continue
            
            row = current_bar.iloc[0]
            
            if row["Crossover"] and row["Score"] >= min_score:
                # Check if already in position
                if any(p[0] == symbol for p in open_positions):
                    continue
                
                # Check max_positions limit
                if len(open_positions) >= max_positions:
                    continue
                
                # Calculate position size (1.5% risk for V2)
                position_size = current_equity * 0.015
                
                open_positions.append((symbol, date, row["Close"], row["EMA_signal"], position_size))
        
        equity_curve.append(current_equity)
    
    # Metrics
    if len(completed_trades) == 0:
        return {"total_trades": 0, "total_pnl_pct": 0.0, "win_rate": 0.0, "max_drawdown": 0.0, "avg_holding_days": 0.0}
    
    total_trades = len(completed_trades)
    wins = sum(1 for t in completed_trades if t["pnl_pct"] > 0)
    win_rate = wins / total_trades * 100
    total_pnl_dollars = sum(t["pnl_dollars"] for t in completed_trades)
    total_pnl_pct = (total_pnl_dollars / initial_equity) * 100
    avg_holding_days = sum(t["holding_days"] for t in completed_trades) / total_trades
    max_drawdown = calculate_max_drawdown(equity_curve)
    
    return {
        "total_trades": total_trades,
        "total_pnl_pct": total_pnl_pct,
        "win_rate": win_rate,
        "max_drawdown": max_drawdown,
        "avg_holding_days": avg_holding_days
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="V1 vs V2 comparison over 100 days")
    parser.add_argument("--symbols", nargs="+", required=True, help="Symbols to test")
    parser.add_argument("--lookback", type=int, default=100, help="Days to backtest")
    args = parser.parse_args()
    
    print(f"\n{'='*80}")
    print(f"V1 vs V2 COMPARISON - {args.lookback} DAY PERIOD")
    print(f"{'='*80}")
    print(f"Symbols: {len(args.symbols)} | Period: Last {args.lookback} days")
    print(f"{'='*80}\n")
    
    print(f"[TEST] V1 (5 positions, no indicators)... ", end="", flush=True)
    v1_results = backtest_v1(symbols=args.symbols, lookback=args.lookback, max_positions=5)
    print(f"✓")
    
    print(f"[TEST] V2 (10 positions, ML indicators)... ", end="", flush=True)
    v2_results = backtest_v2(symbols=args.symbols, lookback=args.lookback, max_positions=10, min_score=40)
    print(f"✓\n")
    
    # Results table
    print(f"{'='*80}")
    print(f"RESULTS")
    print(f"{'='*80}")
    print(f"{'Metric':<25} {'V1 (5 pos)':<20} {'V2 (10 pos)':<20} {'Delta':<15}")
    print(f"{'-'*80}")
    
    print(f"{'Total Trades':<25} {v1_results['total_trades']:<20} {v2_results['total_trades']:<20} {v2_results['total_trades'] - v1_results['total_trades']:+<15}")
    print(f"{'Total P&L%':<25} {v1_results['total_pnl_pct']:<20.2f} {v2_results['total_pnl_pct']:<20.2f} {v2_results['total_pnl_pct'] - v1_results['total_pnl_pct']:+<15.2f}")
    print(f"{'Win Rate%':<25} {v1_results['win_rate']:<20.1f} {v2_results['win_rate']:<20.1f} {v2_results['win_rate'] - v1_results['win_rate']:+<15.1f}")
    print(f"{'Max Drawdown%':<25} {v1_results['max_drawdown']:<20.2f} {v2_results['max_drawdown']:<20.2f} {v2_results['max_drawdown'] - v1_results['max_drawdown']:+<15.2f}")
    print(f"{'Avg Holding Days':<25} {v1_results['avg_holding_days']:<20.1f} {v2_results['avg_holding_days']:<20.1f} {v2_results['avg_holding_days'] - v1_results['avg_holding_days']:+<15.1f}")
    
    # Analysis
    print(f"\n{'='*80}")
    print(f"ANALYSIS")
    print(f"{'='*80}")
    
    if v2_results['total_pnl_pct'] > v1_results['total_pnl_pct']:
        improvement = ((v2_results['total_pnl_pct'] - v1_results['total_pnl_pct']) / abs(v1_results['total_pnl_pct'])) * 100 if v1_results['total_pnl_pct'] != 0 else float('inf')
        print(f"✅ V2 OUTPERFORMS V1 by {v2_results['total_pnl_pct'] - v1_results['total_pnl_pct']:+.2f}% P&L")
        if improvement != float('inf'):
            print(f"   ({improvement:+.1f}% relative improvement)")
    else:
        decline = ((v1_results['total_pnl_pct'] - v2_results['total_pnl_pct']) / abs(v1_results['total_pnl_pct'])) * 100 if v1_results['total_pnl_pct'] != 0 else float('inf')
        print(f"⚠️  V1 OUTPERFORMS V2 by {v1_results['total_pnl_pct'] - v2_results['total_pnl_pct']:+.2f}% P&L")
        if decline != float('inf'):
            print(f"   ({decline:+.1f}% relative difference)")
    
    if v2_results['win_rate'] > v1_results['win_rate']:
        print(f"✅ V2 has BETTER win rate (+{v2_results['win_rate'] - v1_results['win_rate']:.1f}%)")
    else:
        print(f"⚠️  V1 has BETTER win rate (+{v1_results['win_rate'] - v2_results['win_rate']:.1f}%)")
    
    if v2_results['max_drawdown'] < v1_results['max_drawdown']:
        print(f"✅ V2 has LOWER drawdown (-{v1_results['max_drawdown'] - v2_results['max_drawdown']:.2f}% safer)")
    else:
        print(f"⚠️  V1 has LOWER drawdown (-{v2_results['max_drawdown'] - v1_results['max_drawdown']:.2f}% safer)")
    
    if v2_results['total_trades'] > v1_results['total_trades']:
        print(f"📊 V2 executed MORE trades (+{v2_results['total_trades'] - v1_results['total_trades']}) - more active")
    else:
        print(f"📊 V1 executed MORE trades (+{v1_results['total_trades'] - v2_results['total_trades']}) - more active")
    
    # Winner
    print(f"\n{'='*80}")
    v1_score = 0
    v2_score = 0
    
    if v1_results['total_pnl_pct'] > v2_results['total_pnl_pct']:
        v1_score += 2
    else:
        v2_score += 2
    
    if v1_results['win_rate'] > v2_results['win_rate']:
        v1_score += 1
    else:
        v2_score += 1
    
    if v1_results['max_drawdown'] < v2_results['max_drawdown']:
        v1_score += 1
    else:
        v2_score += 1
    
    if v1_score > v2_score:
        print(f"🏆 WINNER: V1 (score: {v1_score} vs {v2_score})")
    elif v2_score > v1_score:
        print(f"🏆 WINNER: V2 (score: {v2_score} vs {v1_score})")
    else:
        print(f"🤝 TIE (score: {v1_score} vs {v2_score})")
    
    print(f"{'='*80}\n")
