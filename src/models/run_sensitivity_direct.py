"""
Fast Subperiod + Parameter Grid Sensitivity Test
Direct simulation without subprocess overhead
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)).split('src')[0])

import pandas as pd
import numpy as np
from pathlib import Path
from src.backtest.simulator_core import simulate_trades
from src.backtest.metrics import compute_basic_stats

# Configuration
SUBPERIODS = [
    ('2010-01-01', '2012-12-31', '2010-2012'),
    ('2013-01-01', '2015-12-31', '2013-2015'),
    ('2016-01-01', '2017-12-31', '2016-2017'),
    ('2018-01-01', '2019-12-31', '2018-2019'),
    ('2020-01-01', '2021-12-31', '2020-2021'),
    ('2022-01-01', '2023-12-31', '2022-2023'),
    ('2024-01-01', '2025-12-31', '2024-2025'),
]

TP_VALUES = [2.5, 2.75, 3.0, 3.25, 3.5]
SL_VALUES = [0.75, 0.875, 1.0, 1.125, 1.25]

OUTPUT_DIR = Path('experiments/exp_026_subperiod_sensitivity')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load data
print("Loading data...")
df_raw = pd.read_csv('data/processed/sp500_features_H4.csv', index_col=0, parse_dates=True)
df_raw = df_raw.sort_index()

# Generate MA signals
df_raw['EMA20'] = df_raw['Close'].ewm(span=20, adjust=False).mean()
df_raw['EMA50'] = df_raw['Close'].ewm(span=50, adjust=False).mean()
df_raw['signal'] = np.where(df_raw['EMA20'] > df_raw['EMA50'], 1, 
                            np.where(df_raw['EMA20'] < df_raw['EMA50'], -1, 0))

print(f"Data loaded: {len(df_raw)} rows, {df_raw.index[0]} to {df_raw.index[-1]}\n")

results = []
run_idx = 0
total_runs = len(SUBPERIODS) * len(TP_VALUES) * len(SL_VALUES)

print("="*80)
print("SUBPERIOD SENSITIVITY ANALYSIS (Direct Simulation)")
print("="*80)
print(f"Subperiods: {len(SUBPERIODS)}")
print(f"TP values: {TP_VALUES}")
print(f"SL values: {SL_VALUES}")
print(f"Total runs: {total_runs}\n")

for oos_start, oos_end, period_label in SUBPERIODS:
    # Train on all data before period, test on period
    start_ts = pd.to_datetime(oos_start)
    end_ts = pd.to_datetime(oos_end)
    
    df_train = df_raw[df_raw.index < start_ts].copy()
    df_test = df_raw[(df_raw.index >= start_ts) & (df_raw.index <= end_ts)].copy()
    
    if len(df_test) < 50:
        print(f"SKIP {period_label}: insufficient test data")
        continue
    
    # Train ML model
    train_signals = df_train[df_train['signal'] != 0].copy()
    if len(train_signals) < 10:
        print(f"SKIP {period_label}: insufficient train signals")
        continue
    
    # Create labels for training
    y_train = []
    for idx in train_signals.index:
        pos = df_train.index.get_loc(idx)
        if pos + 6 >= len(df_train):
            continue
        
        entry = df_train.loc[idx, 'Close']
        signal = df_train.loc[idx, 'signal']
        atr = df_train.loc[idx, 'ATR']
        
        future_high = df_train.iloc[pos+1:pos+7]['High'].max()
        future_low = df_train.iloc[pos+1:pos+7]['Low'].min()
        
        # Check win at default TP=3.0, SL=1.0
        if signal == 1:
            wins = (future_high >= entry + 3.0*atr) and (future_low >= entry - 1.0*atr)
        else:
            wins = (future_low <= entry - 3.0*atr) and (future_high <= entry + 1.0*atr)
        
        y_train.append(1 if wins else 0)
    
    if len(y_train) < 5:
        print(f"SKIP {period_label}: insufficient valid labels")
        continue
    
    X_train = train_signals.iloc[:len(y_train)][['RSI', 'ATR', 'volatility_regime']].fillna(0).values
    y_train = np.array(y_train)
    
    # Train ML filter
    import xgboost as xgb
    filter_model = xgb.XGBClassifier(
        n_estimators=30,
        max_depth=2,
        learning_rate=0.1,
        random_state=42,
        tree_method='hist',
        eval_metric='logloss'
    )
    filter_model.fit(X_train, y_train, verbose=False)
    
    # Get test signal confidences
    test_signals = df_test[df_test['signal'] != 0].copy()
    if len(test_signals) == 0:
        print(f"SKIP {period_label}: no test signals")
        continue
    
    X_test = test_signals[['RSI', 'ATR', 'volatility_regime']].fillna(0).values
    conf_proba = filter_model.predict_proba(X_test)[:, 1]
    
    # Calculate p98 threshold
    fold_conf_threshold = float(np.quantile(conf_proba, 0.98))
    
    # Test each TP/SL combination
    for tp_mult in TP_VALUES:
        for sl_mult in SL_VALUES:
            run_idx += 1
            
            # Filter signals by confidence
            df_test_filtered = df_test.copy()
            df_test_filtered['signal'] = 0
            
            test_signal_indices = np.where(df_test['signal'].values != 0)[0]
            for pos, idx in enumerate(test_signal_indices):
                if conf_proba[pos] > fold_conf_threshold:
                    # REVERSE signal
                    original_signal = df_test.iloc[idx]['signal']
                    reversed_signal = -1 * original_signal
                    df_test_filtered.iloc[idx, df_test_filtered.columns.get_loc('signal')] = reversed_signal
            
            try:
                trades_log, equity = simulate_trades(
                    df_test_filtered,
                    signal_col='signal',
                    sl_atr=sl_mult,
                    tp_atr=tp_mult,
                    initial_capital=10000,
                    risk_per_trade=0.005,
                    max_notional_per_trade=0.05,
                    slippage_pct=0.0001,
                    commission_per_trade=1.0,
                    max_qty=100,
                    min_stop_distance_pct=0.005,
                    max_notional_absolute=50000,
                    dynamic_notional=False
                )
                
                metrics = compute_basic_stats(trades_log, equity)
                
                results.append({
                    'period': period_label,
                    'tp_mult': tp_mult,
                    'sl_mult': sl_mult,
                    'total_trades': metrics.get('total_trades', 0),
                    'win_rate': metrics.get('win_rate', 0.0),
                    'total_pnl': metrics.get('net_pnl', 0.0),
                    'expectancy': metrics.get('expectancy', 0.0),
                    'max_drawdown': metrics.get('max_drawdown', 0.0),
                    'conf_threshold': fold_conf_threshold,
                })
                
                print(f"[{run_idx:3d}/{total_runs}] {period_label} TP={tp_mult:.2f} SL={sl_mult:.3f}: {metrics.get('net_pnl', 0):.0f} PLN", flush=True)
                
            except Exception as e:
                print(f"[{run_idx:3d}/{total_runs}] {period_label} TP={tp_mult:.2f} SL={sl_mult:.3f}: ERROR - {str(e)[:50]}")

if not results:
    print("\nNo results!")
else:
    df_results = pd.DataFrame(results)
    df_results.to_csv(OUTPUT_DIR / 'sensitivity_results.csv', index=False)
    
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    
    # By period
    print("\nBy Period:")
    for period in [p[2] for p in SUBPERIODS]:
        subset = df_results[df_results['period'] == period]
        if len(subset) == 0:
            continue
        
        best_pnl = subset.loc[subset['total_pnl'].idxmax()]
        print(f"  {period}: Best TP={best_pnl['tp_mult']:.2f} SL={best_pnl['sl_mult']:.3f} → {best_pnl['total_pnl']:+.0f} PLN (Win {best_pnl['win_rate']*100:.1f}%)")
    
    # By parameter
    print("\nBy TP Multiplier:")
    for tp in TP_VALUES:
        subset = df_results[df_results['tp_mult'] == tp]
        if len(subset) > 0:
            print(f"  TP={tp:.2f}: Total {subset['total_pnl'].sum():+.0f} PLN, Profitable {(subset['total_pnl'] > 0).sum()}/{len(subset)}")
    
    print("\nBy SL Multiplier:")
    for sl in SL_VALUES:
        subset = df_results[df_results['sl_mult'] == sl]
        if len(subset) > 0:
            print(f"  SL={sl:.3f}: Total {subset['total_pnl'].sum():+.0f} PLN, Profitable {(subset['total_pnl'] > 0).sum()}/{len(subset)}")
    
    # Best combo
    param_consistency = []
    for tp in TP_VALUES:
        for sl in SL_VALUES:
            subset = df_results[(df_results['tp_mult'] == tp) & (df_results['sl_mult'] == sl)]
            if len(subset) > 0:
                param_consistency.append({
                    'tp': tp, 'sl': sl, 'total_pnl': subset['total_pnl'].sum(),
                    'mean_pnl': subset['total_pnl'].mean(), 'std_pnl': subset['total_pnl'].std(),
                    'profitable': (subset['total_pnl'] > 0).sum(), 'count': len(subset)
                })
    
    consistency_df = pd.DataFrame(param_consistency).sort_values('total_pnl', ascending=False)
    consistency_df.to_csv(OUTPUT_DIR / 'parameter_consistency.csv', index=False)
    
    print("\nTop 5 Parameter Combos:")
    for idx, row in consistency_df.head(5).iterrows():
        print(f"  TP={row['tp']:.2f} SL={row['sl']:.3f}: {row['total_pnl']:+.0f} PLN, profitable {row['profitable']}/{row['count']}")
    
    print(f"\nResults saved to: {OUTPUT_DIR}")
