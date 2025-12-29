#!/usr/bin/env python3
"""Obliczenie średnich zwrotów procentowych dla różnych okresów"""
import pandas as pd
import numpy as np

# Wczytaj wyniki subperiodów
results = pd.read_csv('experiments/exp_026_subperiod_sensitivity/sensitivity_results.csv')

# Weź optymalną kombinację
results_opt = results[(results['tp_mult'] == 3.5) & (results['sl_mult'] == 1.0)].copy()

# Capital inicial w symulatorze (sprawdzony w simulator_core.py)
INITIAL_CAPITAL = 10000  # PLN

print('='*80)
print('ŚREDNIE ZWROTY STRATEGII (TP=3.5, SL=1.0) - Dla różnych okresów')
print('='*80)

print(f'\nCapital Initial: {INITIAL_CAPITAL} PLN\n')

# Definicje okresów
periods_config = [
    {
        'name': '15 lat (2010-2025)',
        'periods': ['2010-2012', '2013-2015', '2016-2017', '2018-2019', '2020-2021', '2022-2023', '2024-2025'],
        'years': 15.96
    },
    {
        'name': '10 lat (2015-2025)',
        'periods': ['2013-2015', '2016-2017', '2018-2019', '2020-2021', '2022-2023', '2024-2025'],
        'years': 10.96
    },
    {
        'name': '5 lat (2020-2025)',
        'periods': ['2020-2021', '2022-2023', '2024-2025'],
        'years': 5.96
    },
    {
        'name': '3 lata (2022-2025)',
        'periods': ['2022-2023', '2024-2025'],
        'years': 2.96
    },
    {
        'name': '1 rok (2024-2025)',
        'periods': ['2024-2025'],
        'years': 1.0
    },
]

results_list = []

for config in periods_config:
    # Filtruj dane dla tego okresu
    period_results = results_opt[results_opt['period'].isin(config['periods'])]
    
    if len(period_results) > 0:
        total_pnl = period_results['total_pnl'].sum()
        num_trades = period_results['total_trades'].sum()
        avg_profit_per_trade = total_pnl / num_trades if num_trades > 0 else 0
        
        # Oblicz procent zwrotu
        pct_return = (total_pnl / INITIAL_CAPITAL) * 100
        
        # Annualizowany zwrot
        ann_return = pct_return / config['years']
        
        # Compounded annualized growth rate (CAGR)
        if pct_return > -100:
            cagr = (((INITIAL_CAPITAL + total_pnl) / INITIAL_CAPITAL) ** (1/config['years']) - 1) * 100
        else:
            cagr = None
        
        print(f"{config['name']}:")
        print(f"  Okresy:          {', '.join(config['periods'])}")
        print(f"  Całkowity P&L:   {total_pnl:+.0f} PLN")
        print(f"  Liczba tradów:   {int(num_trades)}")
        print(f"  Zysk na trade:   {avg_profit_per_trade:+.1f} PLN")
        print(f"  Zwrot %:         {pct_return:+.2f}%")
        print(f"  Roczna zwrot:    {ann_return:+.2f}%/rok")
        if cagr is not None:
            print(f"  CAGR:            {cagr:+.2f}%/rok")
        print()
        
        results_list.append({
            'Okres': config['name'],
            'P&L (PLN)': total_pnl,
            'Trades': int(num_trades),
            'Zwrot (%)': pct_return,
            'Roczny (%)': ann_return,
            'CAGR (%)': cagr if cagr is not None else np.nan
        })

print('='*80)
print('PODSUMOWANIE TABELARYCZNE')
print('='*80)

summary_df = pd.DataFrame(results_list)
print('\n', summary_df.to_string(index=False))

print('\n' + '='*80)
print('INTERPRETACJA')
print('='*80)

best_roi = summary_df.loc[summary_df['Zwrot (%)'].idxmax()]
print(f'\nNajlepszy zwrot (bezwzględny):')
print(f'  {best_roi["Okres"]}')
print(f'  {best_roi["Zwrot (%)"]:.2f}% ({best_roi["P&L (PLN)"]:.0f} PLN)')

best_ann = summary_df[summary_df['Roczny (%)'].notna()].loc[summary_df[summary_df['Roczny (%)'].notna()]['Roczny (%)'].idxmax()]
print(f'\nNajlepszy zwrot (roczny):')
print(f'  {best_ann["Okres"]}')
print(f'  {best_ann["Roczny (%)"]:.2f}%/rok')

print(f'\nWniosek:')
print(f'  Strategia zarabia, ale wyniki są zmienne.')
print(f'  W ostatnich latach (2024-2025) pokazuje potencjał.')
print(f'  Wcześniejsze okresy (2010-2020) były trudne ze względu na trendy niedźwiedzich.')

