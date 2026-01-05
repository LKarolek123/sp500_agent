#!/usr/bin/env python
"""Backtest all 18 symbols - EMA 10/100, TP=6%, SL=2%."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.backtest.ema_backtest import download_data, backtest_ema_crossover
from src.live.sp500_screener import get_sp500_symbols

symbols = [s for s in get_sp500_symbols() if s != "SPX"]  # exclude index
lookback = 730  # 2 years

print("\n[FINAL TEST] EMA 10/100, TP=6%, SL=3% (2 years, 18 symbols)")
print("=" * 95)
print(f"{'Symbol':<10} {'Trades':>8} {'Win%':>8} {'P&L%':>10} {'Sharpe':>10}")
print("-" * 95)

results = {}
total_pnl = 0
total_trades = 0
profitable_symbols = 0

for sym in symbols:
    df = download_data(sym, days=lookback)
    if df is not None:
        m = backtest_ema_crossover(df, fast=10, slow=100, tp_pct=0.06, sl_pct=0.03)
        if m:
            results[sym] = m
            total_pnl += m['total_pnl_pct']
            total_trades += m['total_trades']
            if m['total_pnl_pct'] > 0:
                profitable_symbols += 1
            status = "[+]" if m['total_pnl_pct'] > 0 else "[-]"
            print(f"{sym:<10} {m['total_trades']:>8} {m['win_rate']:>7.1f}% {m['total_pnl_pct']:>9.2f}% {m['sharpe']:>9.2f} {status}")

print("=" * 95)
if results:
    avg_pnl = total_pnl / len(results)
    avg_trades = total_trades / len(results)
    print(f"\n[SUMMARY]")
    print(f"  Total symbols tested: {len(results)}")
    print(f"  Profitable symbols:   {profitable_symbols}/{len(results)} ({profitable_symbols/len(results)*100:.0f}%)")
    print(f"  Average P&L%:         {avg_pnl:.2f}%")
    print(f"  Average trades/sym:   {avg_trades:.1f}")
    print(f"  Total portfolio P&L:  {total_pnl:.2f}% (avg)")
    
    best = max(results.items(), key=lambda x: x[1]['total_pnl_pct'])
    worst = min(results.items(), key=lambda x: x[1]['total_pnl_pct'])
    print(f"\n[BEST]  {best[0]}: +{best[1]['total_pnl_pct']:.2f}% ({best[1]['total_trades']} trades, {best[1]['win_rate']:.1f}% WR)")
    print(f"[WORST] {worst[0]}: {worst[1]['total_pnl_pct']:.2f}% ({worst[1]['total_trades']} trades, {worst[1]['win_rate']:.1f}% WR)")
    
    if avg_pnl > 0:
        print(f"\n[VERDICT] READY FOR DEPLOYMENT - Strategy is PROFITABLE!")
    else:
        print(f"\n[VERDICT] Strategy needs optimization - average loss")
