#!/usr/bin/env python3
"""
Analyze detailed trades CSV and print top N trades and per-symbol best trades.
Usage:
    python src/tools/analyze_trades.py results/backtest_quick_trades_YYYYMMDD_HHMMSS.csv --top 5
"""
import argparse
import pandas as pd


def analyze(csv_path: str, top: int = 5, period: str = 'year'):
    df = pd.read_csv(csv_path)
    if 'pnl' not in df.columns:
        print("CSV missing 'pnl' column")
        return

    df['pnl'] = pd.to_numeric(df['pnl'], errors='coerce').fillna(0)
    df['entry_value'] = pd.to_numeric(df.get('entry_value', df['entry'] * df.get('shares', 0)), errors='coerce').fillna(0)
    df['percent_of_equity_at_entry'] = pd.to_numeric(df.get('percent_of_equity_at_entry', 0), errors='coerce').fillna(0)
    df['risk_amount_usd'] = pd.to_numeric(df.get('risk_amount_usd', 0), errors='coerce').fillna(0)
    df['risk_pct_of_equity'] = pd.to_numeric(df.get('risk_pct_of_equity', 0), errors='coerce').fillna(0)
    
    if 'entry_date' in df.columns:
        df['entry_date'] = pd.to_datetime(df['entry_date'], errors='coerce')
    else:
        df['entry_date'] = pd.NaT
    df['entry_year'] = df['entry_date'].dt.year
    df['entry_quarter'] = df['entry_date'].dt.to_period('Q').astype(str)
    df['entry_month'] = df['entry_date'].dt.to_period('M').astype(str)

    print("\nTop trades overall:")
    top_trades = df.sort_values('pnl', ascending=False).head(top)
    for _, r in top_trades.iterrows():
        print(
            f"- {r.get('symbol')} | Entry {r.entry:.2f} -> Exit {r.exit:.2f} | Shares: {int(r.get('shares', 0))} | "
            f"Entry value: ${r.entry_value:.2f} | % equity at entry: {r.percent_of_equity_at_entry}% | "
            f"Risk: ${r.risk_amount_usd:.2f} ({r.risk_pct_of_equity}%) | PnL: ${r.pnl:.2f} ({r.pnl_percent:.2f}%) | Reason: {r.get('exit_reason')}"
        )

    print("\nTop trade per symbol:")
    for sym in sorted(df['symbol'].unique()):
        best = df[df['symbol'] == sym].sort_values('pnl', ascending=False).head(1)
        if len(best) == 0:
            continue
        r = best.iloc[0]
        print(
            f"- {sym}: PnL ${r.pnl:.2f} | Entry {r.entry:.2f} | Shares {int(r.get('shares', 0))} | "
            f"% equity at entry: {r.percent_of_equity_at_entry}% | Risk ${r.risk_amount_usd:.2f} ({r.risk_pct_of_equity}%)"
        )

    print("\nSummary per symbol (PnL, trades, win rate if available):")
    for sym, g in df.groupby('symbol'):
        total_trades = len(g)
        wins = (g['pnl'] > 0).sum()
        win_rate = wins / total_trades * 100 if total_trades > 0 else 0
        total_pnl = g['pnl'].sum()
        print(f"- {sym}: Trades={total_trades}, Wins={wins}, WinRate={win_rate:.2f}%, TotalPnL=${total_pnl:.2f}")

    if period in ['year', 'quarter', 'month']:
        key = {
            'year': 'entry_year',
            'quarter': 'entry_quarter',
            'month': 'entry_month'
        }[period]
        print(f"\nTrades by {period}:")
        counts = df.groupby(key).size().reset_index(name='count').sort_values(key)
        for _, row in counts.iterrows():
            print(f"- {row[key]}: {row['count']} trades")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", help="Path to trades CSV")
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--period", choices=['year', 'quarter', 'month'], default='year', help="Subperiod to count trades")
    args = parser.parse_args()
    analyze(args.csv, args.top, args.period)
