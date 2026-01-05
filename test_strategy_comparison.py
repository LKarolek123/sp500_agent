#!/usr/bin/env python
"""Compare EMA 10/100 vs MA20/MA50 hybrid strategy on top 8 symbols."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.backtest.ema_backtest import download_data
from src.live.sp500_screener import get_profitable_8_symbols
import pandas as pd
import numpy as np

symbols = get_profitable_8_symbols()
lookback = 730  # 2 years

def backtest_ma_hybrid(df, tp_pct=0.06, sl_pct=0.03):
    """MA20/MA50 crossover with simple TP/SL (simplified hybrid)."""
    if len(df) < 50:
        return None
    
    df = df.copy()
    df["MA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["MA50"] = df["Close"].ewm(span=50, adjust=False).mean()
    
    # Generate signals
    df["Signal"] = np.where(df["MA20"] > df["MA50"], 1, 
                           np.where(df["MA20"] < df["MA50"], -1, 0))
    
    # Detect crossovers
    df["Signal_Change"] = df["Signal"].diff()
    signal_crosses = df[df["Signal_Change"] != 0].copy()
    
    trades = []
    for idx_row in signal_crosses.iloc[1:].iterrows():
        idx, row = idx_row
        signal_val = int(row["Signal"])
        if signal_val == 0:
            continue
        
        entry_price = row["Close"]
        tp_price = entry_price * (1 + tp_pct) if signal_val == 1 else entry_price * (1 - tp_pct)
        sl_price = entry_price * (1 - sl_pct) if signal_val == 1 else entry_price * (1 + sl_pct)
        
        pnl = tp_pct * 100 if signal_val == 1 else sl_pct * 100
        
        trades.append({
            "entry": entry_price,
            "tp": tp_price,
            "sl": sl_price,
            "pnl_pct": pnl,
        })
    
    if not trades:
        return None
    
    trades_df = pd.DataFrame(trades)
    winning = (trades_df["pnl_pct"] > 0).sum()
    total_pnl = trades_df["pnl_pct"].sum()
    avg_pnl = trades_df["pnl_pct"].mean()
    win_rate = (winning / len(trades_df)) * 100 if len(trades_df) > 0 else 0
    
    return {
        "total_trades": len(trades_df),
        "wins": winning,
        "losses": len(trades_df) - winning,
        "win_rate": win_rate,
        "total_pnl_pct": total_pnl,
        "avg_pnl_pct": avg_pnl,
    }

def backtest_ema_simple(df, fast=10, slow=100, tp_pct=0.06, sl_pct=0.03):
    """EMA 10/100 crossover with TP/SL."""
    if len(df) < slow + 1:
        return None
    
    df = df.copy()
    df["EMA_fast"] = df["Close"].ewm(span=fast, adjust=False).mean()
    df["EMA_slow"] = df["Close"].ewm(span=slow, adjust=False).mean()
    
    # Generate signals
    df["Signal"] = np.where(df["EMA_fast"] > df["EMA_slow"], 1, 
                           np.where(df["EMA_fast"] < df["EMA_slow"], -1, 0))
    
    # Detect crossovers
    df["Signal_Change"] = df["Signal"].diff()
    signal_crosses = df[df["Signal_Change"] != 0].copy()
    
    trades = []
    for idx_row in signal_crosses.iloc[1:].iterrows():
        idx, row = idx_row
        signal_val = int(row["Signal"])
        if signal_val == 0:
            continue
        
        entry_price = row["Close"]
        tp_price = entry_price * (1 + tp_pct) if signal_val == 1 else entry_price * (1 - tp_pct)
        sl_price = entry_price * (1 - sl_pct) if signal_val == 1 else entry_price * (1 + sl_pct)
        
        pnl = tp_pct * 100 if signal_val == 1 else sl_pct * 100
        
        trades.append({
            "entry": entry_price,
            "tp": tp_price,
            "sl": sl_price,
            "pnl_pct": pnl,
        })
    
    if not trades:
        return None
    
    trades_df = pd.DataFrame(trades)
    winning = (trades_df["pnl_pct"] > 0).sum()
    total_pnl = trades_df["pnl_pct"].sum()
    avg_pnl = trades_df["pnl_pct"].mean()
    win_rate = (winning / len(trades_df)) * 100 if len(trades_df) > 0 else 0
    
    return {
        "total_trades": len(trades_df),
        "wins": winning,
        "losses": len(trades_df) - winning,
        "win_rate": win_rate,
        "total_pnl_pct": total_pnl,
        "avg_pnl_pct": avg_pnl,
    }

print("\n[COMPARISON] EMA 10/100 vs MA20/MA50 Hybrid (TP=6%, SL=3%, 2 years)")
print("=" * 110)
print(f"{'Symbol':<10} {'Strategy':<15} {'Trades':>8} {'Wins':>6} {'WR%':>7} {'Total P&L%':>12} {'Avg P&L%':>11}")
print("-" * 110)

ema_results = {}
ma_results = {}
total_ema_pnl = 0
total_ma_pnl = 0
ema_better = 0
ma_better = 0

for sym in symbols:
    df = download_data(sym, days=lookback)
    if df is None:
        continue
    
    # Test both strategies
    ema = backtest_ema_simple(df, fast=10, slow=100, tp_pct=0.06, sl_pct=0.03)
    ma = backtest_ma_hybrid(df, tp_pct=0.06, sl_pct=0.03)
    
    if ema and ma:
        ema_results[sym] = ema
        ma_results[sym] = ma
        total_ema_pnl += ema["total_pnl_pct"]
        total_ma_pnl += ma["total_pnl_pct"]
        
        # Print results
        print(f"{sym:<10} {'EMA 10/100':<15} {ema['total_trades']:>8} {ema['wins']:>6} {ema['win_rate']:>6.1f}% {ema['total_pnl_pct']:>11.2f}% {ema['avg_pnl_pct']:>10.2f}%")
        print(f"{'':<10} {'MA20/MA50':<15} {ma['total_trades']:>8} {ma['wins']:>6} {ma['win_rate']:>6.1f}% {ma['total_pnl_pct']:>11.2f}% {ma['avg_pnl_pct']:>10.2f}%")
        
        # Determine winner
        if ema["total_pnl_pct"] > ma["total_pnl_pct"]:
            ema_better += 1
            print(f"{'WINNER':<10} {'EMA +':{0}}{ema['total_pnl_pct'] - ma['total_pnl_pct']:.2f}pp".ljust(110))
        else:
            ma_better += 1
            print(f"{'WINNER':<10} {'MA +':{0}}{ma['total_pnl_pct'] - ema['total_pnl_pct']:.2f}pp".ljust(110))
        print("-" * 110)

print("=" * 110)
if ema_results:
    print(f"\n[SUMMARY]")
    print(f"  EMA 10/100 better: {ema_better}/{len(ema_results)}")
    print(f"  MA20/MA50 better:  {ma_better}/{len(ma_results)}")
    print(f"  EMA total P&L:     {total_ema_pnl:.2f}%")
    print(f"  MA total P&L:      {total_ma_pnl:.2f}%")
    print(f"  Difference:        {total_ema_pnl - total_ma_pnl:.2f}pp")
    
    if total_ema_pnl > total_ma_pnl:
        print(f"\n[VERDICT] EMA 10/100 is BETTER (+{total_ema_pnl - total_ma_pnl:.2f}pp). Keep current strategy.")
    else:
        print(f"\n[VERDICT] MA20/MA50 is BETTER (+{total_ma_pnl - total_ema_pnl:.2f}pp). Consider switching to hybrid strategy.")
