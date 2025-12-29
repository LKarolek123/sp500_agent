#!/usr/bin/env python3
"""Generate parameter heatmap visualization"""
import pandas as pd
import numpy as np

df = pd.read_csv('experiments/exp_026_subperiod_sensitivity/sensitivity_results.csv')

# Pivot: TP vs SL (aggregate total P&L)
pivot_total = df.pivot_table(
    index='tp_mult',
    columns='sl_mult',
    values='total_pnl',
    aggfunc='sum'
)

print("="*80)
print("PARAMETER HEATMAP: Total P&L by TP × SL (all 7 subperiods)")
print("="*80)
print("\nTP \ SL", end="")
for sl in sorted(df['sl_mult'].unique()):
    print(f"        {sl:.3f}", end="")
print()
print("-" * 80)

for tp in sorted(df['tp_mult'].unique()):
    print(f"{tp:.2f}   ", end="")
    for sl in sorted(df['sl_mult'].unique()):
        val = pivot_total.loc[tp, sl]
        print(f"  {val:+7.0f} PLN", end="")
    print()

# Pivot: Win periods by parameter
pivot_wins = df.pivot_table(
    index='tp_mult',
    columns='sl_mult',
    values='total_pnl',
    aggfunc=lambda x: (x > 0).sum()
)

print("\n" + "="*80)
print("WIN RATE HEATMAP: Profitable Periods / 7 Total")
print("="*80)
print("\nTP \ SL", end="")
for sl in sorted(df['sl_mult'].unique()):
    print(f"      {sl:.3f}", end="")
print()
print("-" * 80)

for tp in sorted(df['tp_mult'].unique()):
    print(f"{tp:.2f}   ", end="")
    for sl in sorted(df['sl_mult'].unique()):
        wins = pivot_wins.loc[tp, sl]
        print(f"     {int(wins)}/7   ", end="")
    print()

print("\n" + "="*80)
print("BEST & WORST PARAMETERS")
print("="*80)

param_totals = df.groupby(['tp_mult', 'sl_mult'])['total_pnl'].agg(['sum', 'mean', 'std', 'count'])
param_totals['profitable'] = df.groupby(['tp_mult', 'sl_mult'])['total_pnl'].apply(lambda x: (x > 0).sum())
param_totals = param_totals.sort_values('sum', ascending=False)

print("\nTop 5:")
for i, (idx, row) in enumerate(param_totals.head(5).iterrows(), 1):
    tp, sl = idx
    print(f"{i}. TP={tp:.2f} SL={sl:.3f}: {row['sum']:+7.0f} PLN (profitable {int(row['profitable'])}/7 periods)")

print("\nBottom 5:")
for i, (idx, row) in enumerate(param_totals.tail(5).iterrows(), 1):
    tp, sl = idx
    print(f"{i}. TP={tp:.2f} SL={sl:.3f}: {row['sum']:+7.0f} PLN (profitable {int(row['profitable'])}/7 periods)")

print("\n" + "="*80)
print("PERIOD PROFITABILITY MATRIX")
print("="*80)

for period in sorted(df['period'].unique()):
    period_data = df[df['period'] == period]
    pivot_period = period_data.pivot_table(
        index='tp_mult',
        columns='sl_mult',
        values='total_pnl',
        aggfunc='first'
    )
    
    print(f"\n{period}:")
    print("TP \ SL", end="")
    for sl in sorted(period_data['sl_mult'].unique()):
        print(f"     {sl:.3f}", end="")
    print()
    
    for tp in sorted(period_data['tp_mult'].unique()):
        print(f"{tp:.2f}   ", end="")
        for sl in sorted(period_data['sl_mult'].unique()):
            val = pivot_period.loc[tp, sl]
            status = "+" if val > 0 else ""
            print(f" {status}{val:6.0f} ", end="")
        print()
