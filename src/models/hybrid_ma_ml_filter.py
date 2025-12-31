"""
Hybrid strategy: MA20/MA50 crossovers filtered by ML signal validity detector.

Combines best of both worlds:
- Rule-based: MA20/MA50 crossovers (simple, ~365 trades/year, -0.61 exp)
- ML: Train classifier to predict if crossover will be winning trade
- Result: Only trade high-confidence crossovers (~100-150 trades/year)
- Goal: Reduce trades but improve expectancy (filter out false breakouts)
"""
import os
import json
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import precision_score, recall_score

from src.features.feature_engine import build_features
from src.backtest.simulator_core import simulate_trades
from src.backtest.metrics import compute_basic_stats


def generate_ma_signals(df: pd.DataFrame) -> pd.Series:
    """Generate MA20/MA50 crossover signals."""
    df = df.copy()
    if 'EMA20' not in df.columns:
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    if 'EMA50' not in df.columns:
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    signals = np.where(df['EMA20'] > df['EMA50'], 1, 
                      np.where(df['EMA20'] < df['EMA50'], -1, 0))
    return pd.Series(signals, index=df.index)


def create_signal_validity_labels(df: pd.DataFrame, signal_col: str, horizon: int = 6) -> pd.Series:
    """
    Create labels for signal validity: did this crossover lead to a winning trade?
    
    Returns: Series with 1 = winning trade eventually, 0 = losing/neutral
    """
    labels = []
    close = df['Close'].values
    high = df['High'].values
    low = df['Low'].values
    signals = df[signal_col].values
    atr = df['ATR'].values if 'ATR' in df.columns else (high - low)
    
    n = len(df)
    for i in range(n):
        if i + horizon >= n:
            labels.append(np.nan)
            continue
        
        signal = signals[i]
        if signal == 0:  # neutral signal
            labels.append(np.nan)
            continue
        
        entry = close[i]
        atr_val = atr[i]
        
        # Look ahead horizon bars
        max_ret = high[i+1:i+horizon+1].max() - entry
        min_ret = low[i+1:i+horizon+1].min() - entry
        
        # LONG signal: winning if reaches 2x ATR up before 1x ATR down
        if signal == 1:
            if max_ret >= 2*atr_val and min_ret >= -1*atr_val:
                labels.append(1)
            else:
                labels.append(0)
        # SHORT signal: winning if reaches 2x ATR down before 1x ATR up
        else:
            if min_ret <= -2*atr_val and max_ret <= 1*atr_val:
                labels.append(1)
            else:
                labels.append(0)
    
    return pd.Series(labels, index=df.index)


# Load and prepare data
data_path = 'data/processed/sp500_features_H4.csv'
print(f"Loading data from {data_path}...")
df_raw = pd.read_csv(data_path, index_col=0, parse_dates=True)
df_raw = df_raw.sort_index()
print(f"Data shape: {df_raw.shape}")

# Build features
print("Building features...")
df_features = build_features(df_raw)
print(f"Features shape: {df_features.shape}")

# Generate MA signals
print("Generating MA20/MA50 crossover signals...")
df_features['signal'] = generate_ma_signals(df_features)
print(f"Signal distribution: {pd.Series(df_features['signal']).value_counts().to_dict()}")

# Create labels for signal validity
print("Creating signal validity labels...")
df_features['signal_valid'] = create_signal_validity_labels(df_features, 'signal', horizon=6)
valid_trades = df_features[df_features['signal_valid'].notna()]
print(f"Valid signal trades: {len(valid_trades)}")
print(f"Winning signals: {valid_trades[valid_trades['signal_valid']==1].shape[0]} ({valid_trades['signal_valid'].mean()*100:.1f}%)")

# Walk-forward validation
FOLD_SIZE = 1219  # ~4 months
N_FOLDS = 20
TEST_FOLD_SIZE = int(FOLD_SIZE * 0.15)

results = []
fold_idx = 0

for start_idx in range(0, len(df_features) - FOLD_SIZE, TEST_FOLD_SIZE):
    fold_idx += 1
    if fold_idx > N_FOLDS:
        break
    
    fold_end_idx = start_idx + FOLD_SIZE
    train_end_idx = start_idx + int(FOLD_SIZE * 0.70)
    test_end_idx = fold_end_idx
    
    df_train = df_features.iloc[start_idx:train_end_idx].copy()
    df_test = df_features.iloc[train_end_idx:test_end_idx].copy()
    
    print(f"Fold {fold_idx}/{N_FOLDS}: train={len(df_train)}, test={len(df_test)}", end=" ")
    
    # Prepare training data (only on signals)
    train_signals = df_train[df_train['signal'] != 0].copy()
    if len(train_signals) == 0:
        print("- No signals in train, skip")
        continue
    
    # Create labels if not exist
    if train_signals['signal_valid'].isna().sum() == len(train_signals):
        train_signals['signal_valid'] = create_signal_validity_labels(df_train, 'signal', horizon=6)
    
    train_signals = train_signals[train_signals['signal_valid'].notna()].copy()
    if len(train_signals) < 10:
        print("- Too few labeled signals, skip")
        continue
    
    # Prepare features for ML (exclude OHLC, signal, regime, etc.)
    exclude_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'ATR', 'signal', 'signal_valid', 
                    'regime', 'structure', 'EMA20', 'EMA50', 'EMA200']
    feature_cols = [c for c in train_signals.columns if c not in exclude_cols]
    
    X_train = train_signals[feature_cols].values
    y_train = train_signals['signal_valid'].values.astype(int)
    
    # Train ML filter
    filter_model = xgb.XGBClassifier(
        n_estimators=50,
        max_depth=3,
        learning_rate=0.1,
        reg_alpha=1.0,
        reg_lambda=1.0,
        random_state=42,
        tree_method='hist'
    )
    filter_model.fit(X_train, y_train, verbose=False)
    
    # Apply filter to test signals
    test_signals = df_test[df_test['signal'] != 0].copy()
    if len(test_signals) == 0:
        print("- No signals in test")
        continue
    
    X_test = test_signals[feature_cols].values
    y_test_pred_proba = filter_model.predict_proba(X_test)
    
    # Only keep high-confidence signals (prob > 0.6)
    high_conf_mask = y_test_pred_proba[:, 1] > 0.6
    df_test_filtered = df_test.copy()
    df_test_filtered['signal'] = 0  # neutral all
    
    # Set filtered signals back
    signal_idx_in_test = np.where(df_test['signal'] != 0)[0]
    for idx_pos, orig_idx in enumerate(signal_idx_in_test):
        if high_conf_mask[idx_pos]:
            df_test_filtered.loc[df_test_filtered.index[orig_idx], 'signal'] = df_test.loc[df_test.index[orig_idx], 'signal']
    
    # Run backtest
    try:
        trades_log, equity = simulate_trades(
            df_test_filtered,
            signal_col='signal',
            sl_atr=1.0,
            tp_atr=2.0,
            initial_capital=10000,
            risk_per_trade=0.005,
            max_notional_per_trade=0.02,
            slippage_pct=0.0001,
            commission_per_trade=1.0,
            max_qty=100,
            min_stop_distance_pct=0.005,
            max_notional_absolute=50000,
            dynamic_notional=False
        )
        
        metrics = compute_basic_stats(trades_log, equity)
        win_rate = metrics.get('win_rate', 0.0)
        total_trades = metrics.get('total_trades', 0)
        net_pnl = metrics.get('net_pnl', 0.0)
        max_dd = metrics.get('max_drawdown', 0.0)
        expectancy = metrics.get('expectancy', 0.0)
    except Exception as e:
        print(f"- Error: {e}")
        continue
    
    result = {
        'fold': fold_idx,
        'test_size': len(df_test),
        'filtered_signals': high_conf_mask.sum(),
        'total_trades': total_trades,
        'win_rate': win_rate,
        'net_pnl': net_pnl,
        'expectancy': expectancy,
        'max_drawdown': max_dd,
    }
    results.append(result)
    
    print(f"- Signals: {high_conf_mask.sum()}/{len(test_signals)}, Trades: {total_trades}, Win: {win_rate:.2%}, Exp: {expectancy:.2f}")

# Summary
print("\n" + "="*70)
print("HYBRID STRATEGY SUMMARY (MA + ML Filter):")
print("="*70)

if results:
    df_results = pd.DataFrame(results)
    
    summary = {
        'n_folds': len(results),
        'avg_filtered_signals': df_results['filtered_signals'].mean(),
        'avg_total_trades': df_results['total_trades'].mean(),
        'avg_win_rate': df_results['win_rate'].mean(),
        'avg_expectancy': df_results['expectancy'].mean(),
        'avg_max_drawdown': df_results['max_drawdown'].mean(),
        'total_pnl': df_results['net_pnl'].sum(),
    }
    
    for key, val in summary.items():
        if 'pnl' in key.lower():
            print(f"{key}: {val:.2f} PLN")
        elif 'win' in key.lower():
            print(f"{key}: {val:.4f} ({val*100:.2f}%)")
        else:
            print(f"{key}: {val:.4f}")
    
    # Save results
    os.makedirs('experiments/exp_011_hybrid_ma_ml', exist_ok=True)
    
    df_results.to_csv('experiments/exp_011_hybrid_ma_ml/wf_results.csv', index=False)
    with open('experiments/exp_011_hybrid_ma_ml/wf_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nResults saved to experiments/exp_011_hybrid_ma_ml/")
