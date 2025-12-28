"""Regime-aware labeling: create trading labels with different targets per regime."""
import pandas as pd
import numpy as np
from ..features.indicators import atr as compute_atr
from ..features.regime_detection import detect_regime


def create_labels_regime_aware(
    df: pd.DataFrame,
    horizon: int = 6,
    atr_mult_tp_bull: float = 2.5,
    atr_mult_sl_bull: float = 0.8,
    atr_mult_tp_bear: float = 2.5,
    atr_mult_sl_bear: float = 1.2,
    atr_mult_tp_side: float = 1.5,
    atr_mult_sl_side: float = 1.0,
) -> pd.DataFrame:
    """
    Create labels with regime-adjusted TP/SL:
    
    BULL regime: aggressive TP (2.5x), tight SL (0.8x) - chase the trend
    BEAR regime: symmetric TP (2.5x), wider SL (1.2x) - respect volatility
    SIDEWAYS regime: conservative TP (1.5x), balanced SL (1.0x)
    
    Args:
        df: DataFrame with OHLC + ATR + regime columns
        horizon: lookback bars for label decision (default 6 = ~24h in 4H)
        atr_mult_*: multipliers for each regime
    
    Returns:
        DataFrame with 'label' column (1=LONG, 0=NEUTRAL, -1=SHORT)
    """
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    # Ensure ATR exists
    if 'ATR' not in df.columns:
        df['ATR'] = compute_atr(df, n=14)
    
    # Ensure regime exists
    if 'regime' not in df.columns:
        df['regime'] = detect_regime(df)

    labels = []
    n = len(df)

    for i in range(n):
        if i + horizon >= n:
            labels.append(np.nan)
            continue

        entry = df['Close'].iloc[i]
        atr = df['ATR'].iloc[i]
        regime = df['regime'].iloc[i]
        
        if pd.isna(atr) or atr == 0 or pd.isna(regime):
            labels.append(np.nan)
            continue

        # Select TP/SL based on regime
        if regime == 1:  # BULL
            tp_mult = atr_mult_tp_bull
            sl_mult = atr_mult_sl_bull
        elif regime == -1:  # BEAR
            tp_mult = atr_mult_tp_bear
            sl_mult = atr_mult_sl_bear
        else:  # SIDEWAYS (0)
            tp_mult = atr_mult_tp_side
            sl_mult = atr_mult_sl_side

        future = df.iloc[i+1:i+horizon+1]
        max_ret = future['High'].max() - entry
        min_ret = future['Low'].min() - entry

        # LONG: reach TP (positive) without breaching SL (negative)
        if (max_ret >= tp_mult * atr) and (min_ret >= -sl_mult * atr):
            labels.append(1)
        # SHORT: reach negative TP without breaching positive SL
        elif (min_ret <= -tp_mult * atr) and (max_ret <= sl_mult * atr):
            labels.append(-1)
        else:
            labels.append(0)

    df['label'] = labels

    # drop unlabeled tail rows
    df = df.dropna(subset=['label']).copy()
    df['label'] = df['label'].astype(int)

    return df
