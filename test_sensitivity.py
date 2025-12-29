#!/usr/bin/env python3
"""Test sensitivity script step by step"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Step 1: Imports...")
try:
    import pandas as pd
    import numpy as np
    from pathlib import Path
    print("  + Basic imports OK")
except Exception as e:
    print(f"  - Basic imports failed: {e}")
    sys.exit(1)

print("Step 2: Load data...")
try:
    df_raw = pd.read_csv('data/processed/sp500_features_H4.csv', index_col=0, parse_dates=True)
    df_raw = df_raw.sort_index()
    print(f"  + Data loaded: {len(df_raw)} rows")
except Exception as e:
    print(f"  - Data load failed: {e}")
    sys.exit(1)

print("Step 3: Generate signals...")
try:
    df_raw['EMA20'] = df_raw['Close'].ewm(span=20, adjust=False).mean()
    df_raw['EMA50'] = df_raw['Close'].ewm(span=50, adjust=False).mean()
    df_raw['signal'] = np.where(df_raw['EMA20'] > df_raw['EMA50'], 1, 
                                np.where(df_raw['EMA20'] < df_raw['EMA50'], -1, 0))
    print(f"  + Signals generated")
except Exception as e:
    print(f"  - Signal generation failed: {e}")
    sys.exit(1)

print("Step 4: Import backtest modules...")
try:
    from src.backtest.simulator_core import simulate_trades
    from src.backtest.metrics import compute_basic_stats
    print(f"  + Backtest modules imported")
except Exception as e:
    print(f"  - Backtest modules import failed: {e}")
    sys.exit(1)

print("Step 5: Import XGBoost...")
try:
    import xgboost as xgb
    print(f"  + XGBoost imported")
except Exception as e:
    print(f"  - XGBoost import failed: {e}")
    sys.exit(1)

print("\nAll imports successful! Running actual sensitivity script...")
print("="*80)

# Now run the actual script
exec(open('src/models/run_sensitivity_direct.py').read())
