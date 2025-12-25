"""Run end-to-end: download, resample, features, labeling, predict, backtest.

Produces:
- data/processed/sp500_features_H4.csv
- data/processed/sp500_features_labeled.csv
- experiments/exp_001_baseline/trades.csv
- experiments/exp_001_baseline/equity.csv
- experiments/exp_001_baseline/metrics.json
"""
from pathlib import Path
import json
import pandas as pd

from src.data.pipeline import run as download_run
from src.features.feature_engine import build_features
from src.labeling.dataset_builder import create_labels
from src.models.predict import predict_signals
from src.backtest.simulator_core import simulate_trades
from src.backtest.metrics import compute_basic_stats


def main():
    Path('data/processed').mkdir(parents=True, exist_ok=True)
    Path('experiments/exp_001_baseline').mkdir(parents=True, exist_ok=True)

    print('1) Downloading and resampling')
    raw, h4, h1 = download_run()

    print('2) Building features on H4')
    df_h4 = pd.read_csv('data/resampled/sp500_H4.csv', index_col=0)
    df_h4.index = pd.to_datetime(df_h4.index)
    feats = build_features(df_h4)
    feats.to_csv('data/processed/sp500_features_H4.csv')
    print('Saved data/processed/sp500_features_H4.csv')

    print('3) Creating labels')
    labeled = create_labels(feats, horizon=6, atr_mult_tp=2.0, atr_mult_sl=1.0)
    labeled.to_csv('data/processed/sp500_features_labeled.csv')
    print('Saved data/processed/sp500_features_labeled.csv')

    print('4) Predicting signals (model fallback rules if no model)')
    sig = predict_signals(labeled, model_path='models/xgb_sp500_v1.pkl', conf_thresh=0.6)
    labeled['signal'] = sig
    labeled.to_csv('data/processed/sp500_features_labeled.csv')

    print('5) Backtesting signals')
    trades, equity = simulate_trades(labeled, signal_col='signal', sl_atr=1.0, tp_atr=2.0, risk_per_trade=0.01)
    trades.to_csv('experiments/exp_001_baseline/trades.csv', index=False)
    equity.to_csv('experiments/exp_001_baseline/equity.csv')

    stats = compute_basic_stats(trades, equity)
    with open('experiments/exp_001_baseline/metrics.json', 'w') as f:
        json.dump(stats, f, indent=2)

    print('Backtest summary:')
    print(json.dumps(stats, indent=2))


if __name__ == '__main__':
    main()
