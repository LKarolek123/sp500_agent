"""Regime detection: identify bull/bear/sideways market conditions."""
import pandas as pd
import numpy as np


def detect_regime(df: pd.DataFrame, lookback: int = 50) -> pd.Series:
    """
    Detect market regime using multiple signals:
    - EMA trend alignment (close above/below EMA200)
    - Slope of EMA20 vs EMA50
    - Volatility regime (ATR relative to history)
    
    Returns: Series with regime codes
    - 1 = BULL (price > EMA200, EMA20 > EMA50, volatility normal/low)
    - 0 = SIDEWAYS (price near EMA200, conflicting signals)
    - -1 = BEAR (price < EMA200, EMA20 < EMA50, volatility elevated)
    """
    df = df.copy()
    
    # Ensure required columns
    for col in ['Close', 'EMA20', 'EMA50', 'EMA200', 'ATR']:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    
    regime = pd.Series(0, index=df.index)
    
    # Signal 1: Price above/below EMA200
    price_above_ema200 = df['Close'] > df['EMA200']
    
    # Signal 2: EMA20 above/below EMA50 (trend direction)
    ema20_above_ema50 = df['EMA20'] > df['EMA50']
    
    # Signal 3: Volatility regime (ATR percentile over lookback)
    atr_pctl = df['ATR'].rolling(lookback).apply(
        lambda x: (x.iloc[-1] - x.min()) / (x.max() - x.min() + 1e-8) if len(x) > 1 else 0.5
    )
    high_volatility = atr_pctl > 0.65
    
    # BULL: Price > EMA200, EMA20 > EMA50, volatility not too high
    bull = price_above_ema200 & ema20_above_ema50 & ~high_volatility
    regime[bull] = 1
    
    # BEAR: Price < EMA200, EMA20 < EMA50, volatility elevated signals correction
    bear = ~price_above_ema200 & ~ema20_above_ema50 & high_volatility
    regime[bear] = -1
    
    # SIDEWAYS: conflict between signals (everything else)
    regime[(~bull) & (~bear)] = 0
    
    return regime


def regime_adjusted_atr_target(df: pd.DataFrame, regime_col: str = 'regime') -> tuple:
    """
    Return (atr_mult_tp, atr_mult_sl) adjusted for regime.
    
    BULL: TP=2.5x ATR (greedy for upside), SL=0.8x ATR (tight stop)
    BEAR: TP=2.5x ATR (symmetric), SL=1.2x ATR (wider for noise)
    SIDEWAYS: TP=1.5x ATR (conservative), SL=1.0x ATR (balanced)
    """
    if regime_col not in df.columns:
        return 2.0, 1.0  # fallback
    
    regime = df[regime_col].iloc[-1] if len(df) > 0 else 0
    
    if regime == 1:  # BULL
        return 2.5, 0.8
    elif regime == -1:  # BEAR
        return 2.5, 1.2
    else:  # SIDEWAYS
        return 1.5, 1.0
