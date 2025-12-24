import pandas as pd
import numpy as np

from src.features.feature_engine import build_features


def test_build_features_synthetic():
    # synthetic OHLCV series (no network required)
    idx = pd.date_range("2020-01-01", periods=300, freq="D")
    base = np.linspace(100, 150, 300)
    noise = np.sin(np.linspace(0, 20, 300)) * 1.5
    close = base + noise
    high = close + np.random.RandomState(1).rand(300) * 0.8
    low = close - np.random.RandomState(2).rand(300) * 0.8
    open_ = close + (np.random.RandomState(3).rand(300) - 0.5) * 0.5
    vol = np.random.RandomState(4).randint(100, 1000, 300)

    df = pd.DataFrame({
        'Open': open_,
        'High': high,
        'Low': low,
        'Close': close,
        'Volume': vol
    }, index=idx)

    feats = build_features(df)

    required = ['EMA20', 'EMA50', 'EMA200', 'RSI', 'ATR', 'trend_strength', 'volatility_regime', 'structure']
    for c in required:
        assert c in feats.columns

    # after dropna there should be rows and required columns should not contain NaN
    assert len(feats) > 0
    assert not feats[required].isnull().any().any()
