"""Feature engine: composes indicators into a feature DataFrame.

Implements core features used by the ML pipeline:
- EMA20, EMA50, EMA200
- RSI(14), ATR(14)
- trend_strength, volatility_regime
- market structure (HH/HL/LH/LL simplified -> -1/0/1)
"""
import pandas as pd
from .indicators import ema, rsi, atr
from .structure import structure_state


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    df['EMA20'] = ema(df['Close'], 20)
    df['EMA50'] = ema(df['Close'], 50)
    df['EMA200'] = ema(df['Close'], 200)

    df['RSI'] = rsi(df['Close'], 14)
    df['ATR'] = atr(df, 14)

    df['trend_strength'] = (df['EMA20'] - df['EMA50']) / df['ATR']
    df['volatility_regime'] = df['ATR'] / df['EMA200']

    # simplified structure label: 1 = bullish (HH+HL), -1 = bearish (LH+LL), 0 = neutral
    df['structure'] = structure_state(df)

    # Additional features: slopes and ATR z-score
    # RSI slope (4-bar difference chosen)
    df['RSI_slope'] = df['RSI'].diff(4) / 4.0

    # EMA20 slope and EMA20-EMA50 crossover distance
    df['EMA20_slope'] = df['EMA20'].diff(3) / 3.0
    df['EMA20_EMA50_diff'] = df['EMA20'] - df['EMA50']

    # ATR z-score relative to 200-bar history
    atr_mean = df['ATR'].rolling(200).mean()
    atr_std = df['ATR'].rolling(200).std()
    df['ATR_zscore'] = (df['ATR'] - atr_mean) / atr_std

    return df.dropna()
