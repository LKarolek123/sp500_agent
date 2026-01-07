"""
Test V2 strategy with ML-optimized indicator scoring.

Compares:
  - V1: baseline EMA crossover
  - V2: EMA + reversal + time-stop (NO indicators)
  - V2+Indicators: EMA + reversal + time-stop + ML scoring

Usage:
    python test_v2_indicators.py --symbols TSLA DIS GOOGL JNJ JPM LLY META AMZN SPY --lookback 900
"""
import sys
from pathlib import Path
from typing import List, Dict
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from src.backtest.ema_backtest import download_data
from src.live.technical_indicators import (
    calculate_rsi, calculate_macd, calculate_volume_ma, score_trade
)


def backtest_v2_with_indicators(
    symbols: List[str],
    lookback: int = 900,
    tp_pct: float = 0.06,
    sl_pct: float = 0.03,
    time_stop_days: int = None,
    use_reversal: bool = False,
    min_score: int = 40
) -> Dict[str, dict]:
    """
    Backtest V2 with indicator scoring.
    
    Entry: EMA crossover + score >= min_score
    Exit: TP/SL [+ optional reversal] [+ optional time-stop]
    """
    results = {}
    
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
                return 1  # Near support, bounce up
            elif abs(price - resistance) / resistance < threshold:
                return -1  # Near resistance, bounce down
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
        
        # Simulate trades
        trades = []
        in_position = False
        entry_price = 0.0
        entry_date = None
        entry_signal = 0
        
        for idx, row in df.iterrows():
            if not in_position:
                # Entry: crossover + score >= min_score
                if row["Crossover"] and row["Score"] >= min_score:
                    in_position = True
                    entry_price = row["Close"]
                    entry_date = row["Date"]
                    entry_signal = row["EMA_signal"]
            else:
                # Exit conditions
                pnl_pct = (row["Close"] - entry_price) / entry_price
                
                # TP/SL
                if entry_signal == 1:
                    if pnl_pct >= tp_pct:
                        trades.append({"entry": entry_date, "exit": row["Date"], "pnl_pct": pnl_pct, "reason": "TP"})
                        in_position = False
                        continue
                    elif pnl_pct <= -sl_pct:
                        trades.append({"entry": entry_date, "exit": row["Date"], "pnl_pct": pnl_pct, "reason": "SL"})
                        in_position = False
                        continue
                elif entry_signal == -1:
                    if pnl_pct <= -tp_pct:
                        trades.append({"entry": entry_date, "exit": row["Date"], "pnl_pct": pnl_pct, "reason": "TP"})
                        in_position = False
                        continue
                    elif pnl_pct >= sl_pct:
                        trades.append({"entry": entry_date, "exit": row["Date"], "pnl_pct": pnl_pct, "reason": "SL"})
                        in_position = False
                        continue
                
                # Reversal exit (optional)
                if use_reversal and row["EMA_signal"] != entry_signal and row["EMA_signal"] != 0:
                    trades.append({"entry": entry_date, "exit": row["Date"], "pnl_pct": pnl_pct, "reason": "REV"})
                    in_position = False
                    continue
                
                # Time-stop (optional)
                if time_stop_days is not None:
                    days_held = (row["Date"] - entry_date).days
                    if days_held >= time_stop_days:
                        trades.append({"entry": entry_date, "exit": row["Date"], "pnl_pct": pnl_pct, "reason": "TIME"})
                        in_position = False
        
        # Metrics
        if len(trades) == 0:
            print(f"[SKIP] {symbol} - no trades with score >= {min_score}")
            continue
        
        total_trades = len(trades)
        wins = sum(1 for t in trades if t["pnl_pct"] > 0)
        win_rate = wins / total_trades * 100 if total_trades > 0 else 0
        total_pnl_pct = sum(t["pnl_pct"] for t in trades) * 100
        
        results[symbol] = {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "total_pnl_pct": total_pnl_pct,
            "trades": trades
        }
        
        print(f"[TEST] {symbol}... [OK] {total_trades} tr, {win_rate:.0f}% wr, {total_pnl_pct:.2f}%")
    
    return results


def summarize(label: str, results: dict):
    if not results:
        print(f"[SUMMARY] {label}: no results")
        return
    
    print("\n" + "=" * 80)
    print(f"SUMMARY: {label}")
    print("=" * 80)
    
    total_pnl_pct = sum(m["total_pnl_pct"] for m in results.values())
    avg_pnl_pct = total_pnl_pct / max(1, len(results))
    avg_win_rate = sum(m["win_rate"] for m in results.values()) / max(1, len(results))
    
    print(f"Symbols: {len(results)} | Avg P&L%: {avg_pnl_pct:.2f}% | Avg Win%: {avg_win_rate:.1f}%")
    
    # Detail table
    print("\nSymbol       Trades     Win%       P&L%")
    print("-" * 50)
    for symbol in sorted(results.keys()):
        m = results[symbol]
        print(f"{symbol:<12} {m['total_trades']:>6}    {m['win_rate']:>5.1f}%    {m['total_pnl_pct']:>7.2f}%")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test V2 with ML-optimized indicators")
    parser.add_argument("--symbols", nargs="+", required=True, help="Symbols to test")
    parser.add_argument("--lookback", type=int, default=900, help="Days to backtest")
    parser.add_argument("--min-score", type=int, default=40, help="Minimum score to enter (0-100)")
    parser.add_argument("--use-reversal", action="store_true", help="Enable reversal exits")
    parser.add_argument("--time-stop", type=int, default=None, help="Time-stop in days (default: disabled)")
    args = parser.parse_args()
    
    print(f"\n[TEST] V2 + ML Indicators (min score: {args.min_score}, reversal: {args.use_reversal}, time-stop: {args.time_stop}d)")
    print("=" * 80)
    
    results = backtest_v2_with_indicators(
        symbols=args.symbols,
        lookback=args.lookback,
        min_score=args.min_score,
        use_reversal=args.use_reversal,
        time_stop_days=args.time_stop
    )
    
    summarize("V2 + ML Indicators", results)
    
    print("\n" + "=" * 80)
    print("COMPARISON (from previous runs):")
    print("  V1 (baseline):        12.65% avg P&L, 50.3% WR")
    print("  V2 (no indicators):    0.65% avg P&L, 51.8% WR")
    print(f"  V2 + Indicators:      {sum(m['total_pnl_pct'] for m in results.values()) / max(1, len(results)):.2f}% avg P&L, {sum(m['win_rate'] for m in results.values()) / max(1, len(results)):.1f}% WR")
    print("=" * 80)
