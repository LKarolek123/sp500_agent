"""Dataset builder: create trading labels for ML based on ATR-backed TP/SL rules.

Labeling rule (per H4 bar): look `horizon` bars ahead and compute whether
future price action would have hit a TP equal to `atr_mult_tp * ATR` while
not violating a SL of `-atr_mult_sl * ATR` (and vice-versa for SHORT).

Returns the DataFrame with a new integer `label` column in {-1,0,1} and
drops rows at the end that cannot be labeled due to insufficient future bars.
"""
import pandas as pd
import numpy as np
from ..features.indicators import atr as compute_atr


def create_labels(df: pd.DataFrame, horizon: int = 6, atr_mult_tp: float = 2.0, atr_mult_sl: float = 1.0) -> pd.DataFrame:
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    # Ensure ATR exists
    if 'ATR' not in df.columns:
        df['ATR'] = compute_atr(df, n=14)

    labels = []
    n = len(df)

    for i in range(n):
        if i + horizon >= n:
            labels.append(np.nan)
            continue

        entry = df['Close'].iloc[i]
        atr = df['ATR'].iloc[i]
        if pd.isna(atr) or atr == 0:
            labels.append(np.nan)
            continue

        future = df.iloc[i+1:i+horizon+1]
        max_ret = future['High'].max() - entry
        min_ret = future['Low'].min() - entry

        # LONG: reach TP (positive) without breaching SL (negative)
        if (max_ret >= atr_mult_tp * atr) and (min_ret >= -atr_mult_sl * atr):
            labels.append(1)
        # SHORT: reach negative TP without breaching positive SL
        elif (min_ret <= -atr_mult_tp * atr) and (max_ret <= atr_mult_sl * atr):
            labels.append(-1)
        else:
            labels.append(0)

    df['label'] = labels

    # drop unlabeled tail rows
    df = df.dropna(subset=['label']).copy()
    df['label'] = df['label'].astype(int)

    return df
