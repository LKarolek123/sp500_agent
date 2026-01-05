#!/usr/bin/env python
"""Quick backtest comparison: EMA 10/100 vs 20/100 with new TP/SL."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.backtest.ema_backtest import download_data, backtest_ema_crossover

symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
lookback = 730  # 2 years

print("\n[CONFIG] TP=6%, SL=2.5% (NEW)")
print("=" * 90)

# Test 1: EMA 10/100
print("\n[TEST 1] EMA 10/100 (fast strategy)")
print("-" * 90)
print(f"{'Symbol':<10} {'Trades':>8} {'Win%':>8} {'P&L%':>10} {'Sharpe':>10}")
print("-" * 90)

results_10_100 = {}
for sym in symbols:
    df = download_data(sym, days=lookback)
    if df is not None:
        m = backtest_ema_crossover(df, fast=10, slow=100, tp_pct=0.06, sl_pct=0.025)
        if m:
            results_10_100[sym] = m
            print(f"{sym:<10} {m['total_trades']:>8} {m['win_rate']:>7.1f}% {m['total_pnl_pct']:>9.2f}% {m['sharpe']:>9.2f}")

# Test 2: EMA 20/100
print("\n[TEST 2] EMA 20/100 (slower strategy)")
print("-" * 90)
print(f"{'Symbol':<10} {'Trades':>8} {'Win%':>8} {'P&L%':>10} {'Sharpe':>10}")
print("-" * 90)

results_20_100 = {}
for sym in symbols:
    df = download_data(sym, days=lookback)
    if df is not None:
        m = backtest_ema_crossover(df, fast=20, slow=100, tp_pct=0.06, sl_pct=0.025)
        if m:
            results_20_100[sym] = m
            print(f"{sym:<10} {m['total_trades']:>8} {m['win_rate']:>7.1f}% {m['total_pnl_pct']:>9.2f}% {m['sharpe']:>9.2f}")

# Comparison
print("\n[COMPARISON] 10/100 vs 20/100")
print("-" * 90)
print(f"{'Symbol':<10} {'Trades':<8} {'Win% 10/100':>12} {'P&L% 10/100':>12} {'Win% 20/100':>12} {'P&L% 20/100':>12} {'Better':>10}")
print("-" * 90)

for sym in symbols:
    if sym in results_10_100 and sym in results_20_100:
        m1 = results_10_100[sym]
        m2 = results_20_100[sym]
        better = "20/100" if m2['total_pnl_pct'] > m1['total_pnl_pct'] else "10/100"
        print(f"{sym:<10} {m1['total_trades']:<8} {m1['win_rate']:>11.1f}% {m1['total_pnl_pct']:>11.2f}% {m2['win_rate']:>11.1f}% {m2['total_pnl_pct']:>11.2f}% {better:>10}")

print("\n[VERDICT] Wybierz lepszą strategię dla wdrożenia na serwerze!")
