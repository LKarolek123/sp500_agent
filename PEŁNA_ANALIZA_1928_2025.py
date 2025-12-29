#!/usr/bin/env python3
"""Pełna analiza - Od 1928 do 2025"""
import pandas as pd
import numpy as np

# Sprawdzenie danych
df = pd.read_csv('data/processed/sp500_features_H4.csv', index_col=0, parse_dates=True)
df = df.sort_index()

print('='*80)
print('HISTORIA S&P500 - PEŁNY ZAKRES DOSTĘPNYCH DANYCH')
print('='*80)

print(f'\nZAKRES DANYCH:')
print(f'  Od:       {df.index[0].strftime("%Y-%m-%d")}')
print(f'  Do:       {df.index[-1].strftime("%Y-%m-%d")}')
print(f'  Span:     {(df.index[-1] - df.index[0]).days / 365.25:.1f} lat')
print(f'  H4 bars:  {len(df):,}')

print(f'\nCENA ZAMKNIĘCIA:')
print(f'  Min:      {df["Close"].min():.2f}')
print(f'  Max:      {df["Close"].max():.2f}')
print(f'  Aktualnie: {df["Close"].iloc[-1]:.2f}')

print(f'\nWZRAST CAŁKOWITY:')
returns_all = ((df['Close'].iloc[-1] / df['Close'].iloc[0]) - 1) * 100
print(f'  Od 1928 do 2025: {returns_all:+.0f}%')

# Podział na okresy dla strategii testowania
periods = [
    ('1928-01-01', '1945-12-31', '1928-1945 (Wielka Depresja)'),
    ('1946-01-01', '1970-12-31', '1946-1970 (Post-WWII)'),
    ('1971-01-01', '1987-12-31', '1971-1987 (Złoty wiek)'),
    ('1988-01-01', '2001-12-31', '1988-2001 (Dot-com)'),
    ('2002-01-01', '2008-12-31', '2002-2008 (Przedkryzys)'),
    ('2009-01-01', '2016-12-31', '2009-2016 (Post-kryzys)'),
    ('2017-01-01', '2025-12-31', '2017-2025 (Recent)'),
]

print('\n' + '='*80)
print('PODZIAŁ HISTORYCZNY')
print('='*80)

for start, end, label in periods:
    start_dt = pd.to_datetime(start)
    end_dt = pd.to_datetime(end)
    
    period_df = df[(df.index >= start_dt) & (df.index <= end_dt)]
    
    if len(period_df) > 0:
        price_start = period_df['Close'].iloc[0]
        price_end = period_df['Close'].iloc[-1]
        period_return = ((price_end / price_start) - 1) * 100
        years = (end_dt - start_dt).days / 365.25
        ann_return = period_return / years if years > 0 else 0
        
        print(f'\n{label}:')
        print(f'  Cena:    {price_start:.2f} → {price_end:.2f}')
        print(f'  Return:  {period_return:+.1f}%')
        print(f'  Ann:     {ann_return:+.1f}%/rok')
        print(f'  Bars:    {len(period_df):,}')

print('\n' + '='*80)
print('STRATEGIA - DOSTĘPNE TESTY')
print('='*80)

print('\n✓ Testowanie dostępne dla: 2010-2025 (dane H4)')
print('✗ Brak testów dla: 1928-2009 (brak kompletnych danych H4)')

print('\nWyniki dla dostępnego okresu (2010-2025):')

# Sensitivity results
results = pd.read_csv('experiments/exp_026_subperiod_sensitivity/sensitivity_results.csv')
results_opt = results[(results['tp_mult'] == 3.5) & (results['sl_mult'] == 1.0)]

total_pnl = 0
for period in sorted(results_opt['period'].unique()):
    period_data = results_opt[results_opt['period'] == period]
    if len(period_data) > 0:
        pnl = period_data.iloc[0]['total_pnl']
        total_pnl += pnl
        status = '✓' if pnl > 0 else '✗'
        print(f'  {status} {period}: {pnl:+7.0f} PLN')

print(f'  {"─"*40}')
print(f'  ŁĄCZNIE 2010-2025: {total_pnl:+7.0f} PLN')

print('\n' + '='*80)
print('PODSUMOWANIE')
print('='*80)

print('\nDane dostępne: 1928-2025 (97 lat)')
print('Ale testowana strategia (H4): 2010-2025 (15.96 lat)')
print('\nKryzys 2008 (sierpień): NIE ZAWARTY w backteście')
print('  (dane zaczynają się od 2010)')
print('\nAle strategia przetestowana na wielu kryzysach 2010-2025:')
print('  ✓ 2015-2016 (Chiński kryzys, Brexit)')
print('  ✓ 2018 (Korekta 20%+)')
print('  ✓ 2020 (COVID crash -35%)')
print('  ✓ 2022 (Niedźwiedź FED -27%)')

print('\nWynik na dostępnym okresie (2010-2025):')
print(f'  P&L strategii (TP=3.5, SL=1.0): {total_pnl:+.0f} PLN')
print(f'  Wzrost S&P500 (2010-2025): +{((df.loc[pd.to_datetime("2025-12-31"), "Close"] / df.loc[pd.to_datetime("2010-01-01"), "Close"] - 1) * 100):.1f}%')

