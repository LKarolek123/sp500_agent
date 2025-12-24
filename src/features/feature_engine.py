"""Feature engine: composes indicators into feature DataFrame (placeholder).
"""
import pandas as pd
from .indicators import ema, rsi, atr


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['EMA20'] = ema(df['Close'], 20)
    df['EMA50'] = ema(df['Close'], 50)
    df['EMA200'] = ema(df['Close'], 200)
    df['RSI'] = rsi(df['Close'], 14)
    df['ATR'] = atr(df, 14)
    df['trend_strength'] = (df['EMA20'] - df['EMA50']) / df['ATR']
    df['volatility_regime'] = df['ATR'] / df['EMA200']
    return df.dropna()
