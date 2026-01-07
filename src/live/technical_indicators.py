"""
Technical indicators for multi-symbol trading: RSI, MACD, Support/Resistance, Volume.

Scoring system (0-100):
  EMA Crossover:     35%
  RSI Confirmation:  20%
  MACD Histogram:    20%
  S/R Bounce:        20%
  Volume Confirm:    5%
  
Score breakdown:
  < 40: SKIP
  40-59: MICRO (0.4% risk)
  60-79: NORMAL (0.8% risk)
  80-100: AGGRESSIVE (1.2% risk)
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple


def calculate_rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index."""
    delta = closes.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(closes: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD (line, signal, histogram)."""
    ema_fast = closes.ewm(span=fast, adjust=False).mean()
    ema_slow = closes.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_support_resistance(df: pd.DataFrame, lookback: int = 20) -> Tuple[float, float]:
    """
    Calculate support and resistance from recent highs/lows.
    
    Returns: (support, resistance)
    """
    if len(df) < lookback:
        return None, None
    
    recent = df.iloc[-lookback:]
    support = float(recent["Low"].min())
    resistance = float(recent["High"].max())
    
    return support, resistance


def detect_support_resistance_signal(price: float, support: float, resistance: float, threshold_pct: float = 0.02) -> int:
    """
    Detect if price is near support (buy) or resistance (sell).
    
    Returns: 1 (near support, bullish), -1 (near resistance, bearish), 0 (neutral)
    """
    if support is None or resistance is None:
        return 0
    
    distance_to_support = (price - support) / support
    distance_to_resistance = (resistance - price) / resistance
    
    if distance_to_support < threshold_pct:  # price bounced off support
        return 1
    elif distance_to_resistance < threshold_pct:  # price rejected at resistance
        return -1
    else:
        return 0


def calculate_volume_ma(volumes: pd.Series, period: int = 20) -> pd.Series:
    """Calculate volume moving average."""
    return volumes.rolling(window=period).mean()


def score_trade(
    df: pd.DataFrame,
    ema_signal: int,
    rsi: float,
    macd_hist: float,
    sr_signal: int,
    volume_ratio: float,
    verbose: bool = False
) -> int:
    """
    Score a trade from 0-100 based on multiple indicators.
    
    Args:
        ema_signal: 1 (long), -1 (short), 0 (neutral)
        rsi: RSI value (0-100)
        macd_hist: MACD histogram value
        sr_signal: 1 (near support), -1 (near resistance), 0 (neutral)
        volume_ratio: current_vol / vol_ma (1.0 = average)
        verbose: print breakdown
    
    Returns: score 0-100
    """
    score = 0
    
    # EMA (33.57%) - ML optimized from 50 trials
    if ema_signal != 0:
        ema_score = 33.57  # EMA crossover is the main signal
    else:
        ema_score = 0
    score += ema_score
    
    # RSI (24.04%) - ML optimized from 50 trials
    if ema_signal == 1:
        # Long: want RSI 30-50 (not overbought, momentum building)
        if rsi < 30:
            rsi_score = 12.02  # Oversold, reversal candidate
        elif rsi < 50:
            rsi_score = 24.04  # Perfect zone
        elif rsi < 70:
            rsi_score = 12.02  # Momentum but approaching overbought
        else:
            rsi_score = 0  # Overbought, avoid
    elif ema_signal == -1:
        # Short: want RSI 50-70 (not oversold, momentum building down)
        if rsi > 70:
            rsi_score = 12.02  # Overbought, reversal candidate
        elif rsi > 50:
            rsi_score = 24.04  # Perfect zone
        elif rsi > 30:
            rsi_score = 12.02  # Momentum but approaching oversold
        else:
            rsi_score = 0  # Oversold, avoid
    else:
        rsi_score = 0
    score += rsi_score
    
    # MACD (8.59%) - ML optimized from 50 trials
    if ema_signal == 1 and macd_hist > 0:
        macd_score = 8.59  # MACD positive, uptrend confirmed
    elif ema_signal == -1 and macd_hist < 0:
        macd_score = 8.59  # MACD negative, downtrend confirmed
    elif ema_signal != 0:
        macd_score = 2.15  # Signal present but MACD disagrees
    else:
        macd_score = 0
    score += macd_score
    
    # S/R (19.79%) - ML optimized from 50 trials
    if sr_signal == ema_signal and sr_signal != 0:
        sr_score = 19.79  # Strong: EMA and S/R aligned
    elif sr_signal == 0 and ema_signal != 0:
        sr_score = 9.90  # Weak: EMA signal but S/R neutral
    elif sr_signal != ema_signal and sr_signal != 0:
        sr_score = 0  # Conflict: avoid
    else:
        sr_score = 0
    score += sr_score
    
    # Volume (4.01%) - ML optimized from 50 trials
    if volume_ratio >= 1.0:
        vol_score = 4.01  # Above average volume
    else:
        vol_score = 0  # Below average, weak signal
    score += vol_score
    
    if verbose:
        print(f"    Score breakdown: EMA={ema_score:.1f}, RSI={rsi_score:.1f}, MACD={macd_score:.1f}, S/R={sr_score:.1f}, Vol={vol_score:.1f} → Total={score:.0f}/100")
    
    return int(score)


def risk_sizing_from_score(score: int, equity: float, base_risk: float = 0.015) -> float:
    """
    Adjust risk based on score confidence.
    
    score < 40: skip
    40-59: 0.75% risk
    60-79: 1.5% risk (base)
    80-100: 2.25% risk
    """
    if score < 40:
        return 0.0  # Skip
    elif score < 60:
        return equity * 0.0075
    elif score < 80:
        return equity * base_risk  # 1.5%
    else:
        return equity * 0.0225  # 2.25%
