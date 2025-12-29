"""Backtest metrics helpers: compute PnL, drawdown, expectancy."""
import pandas as pd
import numpy as np


def compute_basic_stats(trades_df: pd.DataFrame, equity_series: pd.Series):
    stats = {}
    if trades_df is None or trades_df.empty:
        stats.update({
            'total_trades': 0,
            'net_pnl': 0.0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'expectancy': 0.0,
            'max_drawdown': 0.0,
        })
        return stats

    total = len(trades_df)
    pnl = trades_df['pl'].sum()
    wins = trades_df[trades_df['pl'] > 0]
    losses = trades_df[trades_df['pl'] <= 0]
    win_rate = len(wins) / total if total > 0 else 0.0
    avg_win = wins['pl'].mean() if not wins.empty else 0.0
    avg_loss = losses['pl'].mean() if not losses.empty else 0.0
    expectancy = win_rate * avg_win + (1 - win_rate) * avg_loss

    # drawdown
    eq = equity_series.ffill().fillna(0)
    peak = eq.cummax()
    dd = (eq - peak) / peak
    max_dd = dd.min() if not dd.empty else 0.0

    stats.update({
        'total_trades': int(total),
        'net_pnl': float(pnl),
        'win_rate': float(win_rate),
        'avg_win': float(avg_win),
        'avg_loss': float(avg_loss),
        'expectancy': float(expectancy),
        'max_drawdown': float(max_dd),
    })

    return stats
