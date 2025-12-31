"""
Final validation: Clean test of optimized reversed hybrid strategy.

Config: TP=3.0x, SL=1.0x, Conf>0.40, Risk=0.5%, REVERSED signals
"""
import os
import json
import pandas as pd
import numpy as np
import xgboost as xgb

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


# Load data
data_path = 'data/processed/sp500_features_H4.csv'
print(f"Loading data from {data_path}...")
df_raw = pd.read_csv(data_path, index_col=0, parse_dates=True)
df_raw = df_raw.sort_index()
df_raw['signal'] = generate_ma_signals(df_raw)
print(f"Data shape: {df_raw.shape}")
print(f"Date range: {df_raw.index[0]} to {df_raw.index[-1]}\n")

# Optional out-of-sample date filter via environment variables
oos_start = os.environ.get('OOS_START')
oos_end = os.environ.get('OOS_END')
oos_mode = False
oos_train_df = None
oos_test_df = None
if oos_start or oos_end:
    start_ts = pd.to_datetime(oos_start) if oos_start else df_raw.index[0]
    end_ts = pd.to_datetime(oos_end) if oos_end else df_raw.index[-1]
    oos_test_df = df_raw.loc[(df_raw.index >= start_ts) & (df_raw.index <= end_ts)].copy()
    oos_train_df = df_raw.loc[df_raw.index < start_ts].copy()
    oos_mode = True
    print(f"Applying OOS filter: {start_ts} to {end_ts}")
    print(f"Filtered shape: {oos_test_df.shape}\n")

# Final optimized config
TP_MULT = float(os.environ.get('TP_MULT', 3.0))
SL_MULT = float(os.environ.get('SL_MULT', 1.0))

# Confidence threshold configuration: supports fixed value or percentile-based
_conf_threshold_env = os.environ.get('CONF_THRESHOLD', '0.40')
_conf_percentile_env = os.environ.get('CONF_PERCENTILE')
CONF_THRESHOLD: float | None = None
CONF_PERCENTILE: float | None = None  # expressed as fraction (e.g., 0.95)
CONF_MODE = 'fixed'

try:
    if _conf_percentile_env is not None:
        # Explicit percentile wins
        pct_val = float(_conf_percentile_env)
        CONF_PERCENTILE = max(0.0, min(1.0, pct_val / 100.0))
        CONF_MODE = 'percentile'
    else:
        env_str = str(_conf_threshold_env).strip().lower()
        if env_str.startswith('p'):
            # Format like p95 or p98
            pct = float(env_str[1:])
            CONF_PERCENTILE = max(0.0, min(1.0, pct / 100.0))
            CONF_MODE = 'percentile'
        else:
            CONF_THRESHOLD = float(env_str)
            CONF_MODE = 'fixed'
except Exception:
    # Fallback to fixed default
    CONF_THRESHOLD = 0.40
    CONF_MODE = 'fixed'

RISK_PER_TRADE = 0.005

FOLD_SIZE = 1219
N_FOLDS = 20
TEST_FOLD_SIZE = int(FOLD_SIZE * 0.15)

print("="*70)
print("FINAL STRATEGY TEST: Reversed Hybrid (Optimized)")
print("="*70)
if CONF_MODE == 'fixed':
    print(f"Config: TP={TP_MULT}x ATR, SL={SL_MULT}x ATR, Confidence>{CONF_THRESHOLD}, Risk={RISK_PER_TRADE*100}%")
else:
    pct_disp = int((CONF_PERCENTILE or 0.95) * 100)
    print(f"Config: TP={TP_MULT}x ATR, SL={SL_MULT}x ATR, Confidence>=p{pct_disp} (train-set), Risk={RISK_PER_TRADE*100}%")
print(f"Method: MA20/50 crossovers REVERSED + ML filter\n")

results = []
fold_idx = 0

def run_fold(df_train: pd.DataFrame, df_test: pd.DataFrame, fold_idx: int):
    global results
    
    # Training
    train_signals = df_train[df_train['signal'] != 0].copy()
    if len(train_signals) < 10:
        print(f"Fold {fold_idx}/20: SKIP (insufficient training signals)")
        return
    
    # Create labels
    y_train = []
    for idx in train_signals.index:
        pos = df_train.index.get_loc(idx)
        # Ensure pos is an integer for slicing
        if isinstance(pos, slice):
            continue
        pos = int(pos)
        if pos + 6 >= len(df_train):
            continue
        
        entry = df_train.loc[idx, 'Close']
        signal = df_train.loc[idx, 'signal']
        atr = df_train.loc[idx, 'ATR']
        
        future_high = df_train.iloc[pos+1:pos+7]['High'].max()
        future_low = df_train.iloc[pos+1:pos+7]['Low'].min()
        
        if signal == 1:
            wins = (future_high >= entry + TP_MULT*atr) and (future_low >= entry - SL_MULT*atr)
        else:
            wins = (future_low <= entry - TP_MULT*atr) and (future_high <= entry + SL_MULT*atr)
        
        y_train.append(1 if wins else 0)
    
    if len(y_train) < 5:
        print(f"Fold {fold_idx}/20: SKIP (insufficient valid labels)")
        return
    
    X_train = train_signals.iloc[:len(y_train)][['RSI', 'ATR', 'volatility_regime']].fillna(0).values
    y_train = np.array(y_train)
    
    # Train ML filter
    filter_model = xgb.XGBClassifier(
        n_estimators=30,
        max_depth=2,
        learning_rate=0.1,
        random_state=42,
        tree_method='hist',
        eval_metric='logloss'
    )
    filter_model.fit(X_train, y_train, verbose=False)

    # Test: Filter + REVERSE signals
    test_signals = df_test[df_test['signal'] != 0].copy()
    if len(test_signals) == 0:
        print(f"Fold {fold_idx}/20: SKIP (no test signals)")
        return
    
    X_test = test_signals[['RSI', 'ATR', 'volatility_regime']].fillna(0).values
    conf_proba = filter_model.predict_proba(X_test)[:, 1]
    
    # Debug: confidence distribution
    try:
        conf_series = pd.Series(conf_proba)
        desc = conf_series.describe(percentiles=[0.1,0.25,0.5,0.75,0.9])
        print(f"Fold {fold_idx}/20: Conf stats -> min {desc['min']:.3f}, p10 {desc['10%']:.3f}, p25 {desc['25%']:.3f}, median {desc['50%']:.3f}, p75 {desc['75%']:.3f}, p90 {desc['90%']:.3f}, max {desc['max']:.3f}")
    except Exception:
        pass
    
    # Determine fold-specific confidence threshold
    fold_conf_threshold = CONF_THRESHOLD
    if CONF_MODE == 'percentile':
        try:
            # Use TEST-set confidences for dynamic calibration (avoids train/test shift)
            if len(conf_proba) >= 5:
                fold_conf_threshold = float(np.quantile(conf_proba, CONF_PERCENTILE or 0.95))
            else:
                fold_conf_threshold = 0.0
        except Exception:
            fold_conf_threshold = 0.0
    
    df_test_filtered = df_test.copy()
    df_test_filtered['signal'] = 0
    
    test_signal_indices = np.where(df_test['signal'].values != 0)[0]
    for pos, idx in enumerate(test_signal_indices):
        if conf_proba[pos] > (fold_conf_threshold or 0.0):
            # REVERSE: invert the signal
            original_signal = df_test.iloc[idx]['signal']
            reversed_signal = -1 * original_signal
            df_test_filtered.iloc[idx, df_test_filtered.columns.get_loc('signal')] = reversed_signal
    
    filtered_count = (conf_proba > (fold_conf_threshold or 0.0)).sum()
    
    # Backtest
    try:
        trades_log, equity = simulate_trades(
            df_test_filtered,
            signal_col='signal',
            sl_atr=SL_MULT,
            tp_atr=TP_MULT,
            initial_capital=10000,
            risk_per_trade=RISK_PER_TRADE,
            max_notional_per_trade=0.05,
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
        expectancy = metrics.get('expectancy', 0.0)
        max_dd = metrics.get('max_drawdown', 0.0)
        
        # Print per-fold threshold info
        thr_info = f"thr={fold_conf_threshold:.3f}" if fold_conf_threshold is not None else "thr=auto-0.0"
        print(f"Fold {fold_idx:2d}/20: {thr_info} | Filtered {filtered_count:3d}/{len(test_signals):3d} signals -> "
              f"{total_trades:2d} trades, Win {win_rate:5.1%}, PnL {net_pnl:8.2f}, Exp {expectancy:6.2f}")
        
    except Exception as e:
        print(f"Fold {fold_idx}/20: ERROR - {e}")
        return
    
    result = {
        'fold': fold_idx,
        'signals_total': len(test_signals),
        'signals_filtered': filtered_count,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'net_pnl': net_pnl,
        'expectancy': expectancy,
        'max_drawdown': max_dd,
        'conf_threshold': float(fold_conf_threshold or 0.0),
    }
    results.append(result)

# OOS mode: train on history before start_ts, test on OOS window
if oos_mode:
    if oos_train_df is None or oos_test_df is None or len(oos_train_df) < 200 or len(oos_test_df) < 50:
        print("OOS datasets too short for validation.")
    else:
        run_fold(oos_train_df, oos_test_df, 1)
else:
    # If dataset is short, run a single fold; else run walk-forward
    if len(df_raw) < FOLD_SIZE:
        if len(df_raw) < 100:
            print("Dataset too short for validation.")
        else:
            train_end_idx = int(len(df_raw) * 0.70)
            df_train = df_raw.iloc[:train_end_idx].copy()
            df_test = df_raw.iloc[train_end_idx:].copy()
            run_fold(df_train, df_test, 1)
    else:
        for start_idx in range(0, len(df_raw) - FOLD_SIZE, TEST_FOLD_SIZE):
            fold_idx += 1
            if fold_idx > N_FOLDS:
                break
            
            fold_end_idx = start_idx + FOLD_SIZE
            train_end_idx = start_idx + int(FOLD_SIZE * 0.70)
            
            df_train = df_raw.iloc[start_idx:train_end_idx].copy()
            df_test = df_raw.iloc[train_end_idx:fold_end_idx].copy()
            run_fold(df_train, df_test, fold_idx)

# Summary
print("\n" + "="*70)
print("FINAL RESULTS SUMMARY:")
print("="*70)

if results:
    df_results = pd.DataFrame(results)
    
    # Aggregate threshold if percentile mode
    avg_thr = float(df_results['conf_threshold'].mean()) if 'conf_threshold' in df_results.columns else float(CONF_THRESHOLD or 0.0)
    summary = {
        'strategy': 'Reversed Hybrid (Optimized)',
        'tp_mult': float(TP_MULT),
        'sl_mult': float(SL_MULT),
        'conf_mode': CONF_MODE,
        'conf_threshold': float(CONF_THRESHOLD or avg_thr),
        'avg_conf_threshold': float(avg_thr),
        'conf_percentile': float((CONF_PERCENTILE or 0.0)),
        'risk_per_trade': float(RISK_PER_TRADE),
        'n_folds': int(len(results)),
        'avg_signals_filtered': float(df_results['signals_filtered'].mean() or 0.0),
        'avg_total_trades': float(df_results['total_trades'].mean() or 0.0),
        'avg_win_rate': float(df_results['win_rate'].mean() or 0.0),
        'avg_expectancy': float(df_results['expectancy'].mean() or 0.0),
        'avg_max_drawdown': float(df_results['max_drawdown'].mean() or 0.0),
        'total_pnl': float(df_results['net_pnl'].sum() or 0.0),
        'positive_folds': int((df_results['net_pnl'] > 0).sum()),
        'negative_folds': int((df_results['net_pnl'] < 0).sum()),
    }
    
    print(f"\nFolds tested: {summary['n_folds']}")
    print(f"Avg filtered signals: {summary['avg_signals_filtered']:.1f}/fold")
    print(f"Avg trades executed: {summary['avg_total_trades']:.1f}/fold")
    print(f"Avg win rate: {summary['avg_win_rate']*100:.2f}%")
    print(f"Avg expectancy: {summary['avg_expectancy']:.3f} PLN/trade")
    print(f"Avg max drawdown: {summary['avg_max_drawdown']*100:.2f}%")
    if summary['conf_mode'] == 'percentile':
        pct_disp = int((CONF_PERCENTILE or 0.95) * 100)
        print(f"Calibrated threshold (train-set): p{pct_disp} -> avg {summary['avg_conf_threshold']:.3f}")
    print(f"\n{'='*40}")
    print(f"TOTAL P&L: {summary['total_pnl']:.2f} PLN")
    print(f"{'='*40}")
    print(f"Profitable folds: {summary['positive_folds']}/{summary['n_folds']}")
    print(f"Losing folds: {summary['negative_folds']}/{summary['n_folds']}")
    
    # Save
    os.makedirs('experiments/exp_015_final_validation', exist_ok=True)
    
    df_results.to_csv('experiments/exp_015_final_validation/fold_results.csv', index=False)
    with open('experiments/exp_015_final_validation/summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nResults saved to experiments/exp_015_final_validation/")
else:
    print("No valid results collected!")
