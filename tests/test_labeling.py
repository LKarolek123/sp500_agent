import pandas as pd
import numpy as np

from src.features.feature_engine import build_features
from src.labeling.dataset_builder import create_labels


def test_create_labels_synthetic():
    # build synthetic OHLCV
    idx = pd.date_range("2020-01-01", periods=300, freq="D")
    base = np.linspace(100, 150, 300)
    noise = np.sin(np.linspace(0, 20, 300)) * 1.2
    close = base + noise
    rng = np.random.RandomState(5)
    high = close + rng.rand(300) * 1.0
    low = close - rng.rand(300) * 1.0
    open_ = close + (rng.rand(300) - 0.5) * 0.6
    vol = rng.randint(100, 1000, 300)

    df = pd.DataFrame({
        'Open': open_,
        'High': high,
        'Low': low,
        'Close': close,
        'Volume': vol
    }, index=idx)

    feats = build_features(df)
    labeled = create_labels(feats, horizon=6, atr_mult_tp=2.0, atr_mult_sl=1.0)

    # labels should be integers and in {-1,0,1}
    assert 'label' in labeled.columns
    assert labeled['label'].dtype.kind in ('i', 'u')
    assert set(np.unique(labeled['label'])).issubset({-1, 0, 1})

    # there should be fewer rows than features (tail removed)
    assert len(labeled) <= len(feats)
    assert len(labeled) >= len(feats) - 10  # sanity (not all rows dropped)
