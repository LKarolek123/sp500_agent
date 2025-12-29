#!/usr/bin/env python3
"""Analyze subperiod sensitivity results"""
import pandas as pd
import numpy as np

df = pd.read_csv('experiments/exp_026_subperiod_sensitivity/sensitivity_results.csv')

print(f'Total rows: {len(df)}')
print(f'Columns: {df.columns.tolist()}')
print(f'\nFirst 10 rows:')
print(df.head(10))

print('\n' + '='*80)
print('SUMMARY BY PERIOD')
print('='*80)

total_all_periods = 0
for period in sorted(df['period'].unique()):
    subset = df[df['period'] == period]
    period_total = subset['total_pnl'].sum()
    total_all_periods += period_total
    best_idx = subset['total_pnl'].idxmax()
    best = subset.loc[best_idx]
    worst_idx = subset['total_pnl'].idxmin()
    worst = subset.loc[worst_idx]
    
    print(f'{period}:')
    print(f'  Total P&L: {period_total:+.0f} PLN')
    print(f'  Best: TP={best["tp_mult"]:.2f} SL={best["sl_mult"]:.3f} -> {best["total_pnl"]:+.0f} PLN')
    print(f'  Worst: TP={worst["tp_mult"]:.2f} SL={worst["sl_mult"]:.3f} -> {worst["total_pnl"]:+.0f} PLN')

print(f'\nTotal P&L (all subperiods): {total_all_periods:+.0f} PLN')

print('\n' + '='*80)
print('SUMMARY BY PARAMETER COMBINATION')
print('='*80)

param_summary = []
for tp in sorted(df['tp_mult'].unique()):
    for sl in sorted(df['sl_mult'].unique()):
        subset = df[(df['tp_mult'] == tp) & (df['sl_mult'] == sl)]
        param_summary.append({
            'TP': tp,
            'SL': sl,
            'Total_PLN': subset['total_pnl'].sum(),
            'Mean_PLN': subset['total_pnl'].mean(),
            'Std_PLN': subset['total_pnl'].std(),
            'Profitable_Periods': (subset['total_pnl'] > 0).sum(),
            'Total_Periods': len(subset),
        })

param_df = pd.DataFrame(param_summary).sort_values('Total_PLN', ascending=False)
print(f'\nTop 10 Parameter Combos:')
print(param_df.head(10).to_string(index=False))

print('\n' + '='*80)
print('BASELINE RESULTS (TP=3.0, SL=1.0)')
print('='*80)

baseline = df[(df['tp_mult'] == 3.0) & (df['sl_mult'] == 1.0)]
print(baseline[['period', 'total_pnl', 'total_trades', 'win_rate']].to_string(index=False))
print(f'\nBaseline Total: {baseline["total_pnl"].sum():+.0f} PLN')

print('\n' + '='*80)
print('BEST COMBO VS BASELINE')
print('='*80)

best_combo = param_df.iloc[0]
print(f'Best: TP={best_combo["TP"]:.2f} SL={best_combo["SL"]:.3f} -> {best_combo["Total_PLN"]:+.0f} PLN')
print(f'Baseline: TP=3.0 SL=1.0 -> {baseline["total_pnl"].sum():+.0f} PLN')
print(f'Difference: {best_combo["Total_PLN"] - baseline["total_pnl"].sum():+.0f} PLN')
