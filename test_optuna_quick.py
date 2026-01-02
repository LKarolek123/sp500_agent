"""
Quick test of Optuna optimizer with 20 trials
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.models.optuna_optimizer import StrategyOptimizer

# Quick test with 20 trials
optimizer = StrategyOptimizer(
    data_path='data/processed/sp500_features_H4.csv',
    optimize_metric='sharpe',
    n_trials=20,  # Quick test
    study_name='quick_test'
)

print("\nRunning quick optimization test (20 trials)...")
study = optimizer.optimize(output_dir='experiments/exp_031_optuna_optimization')

print("\nComparing with baseline...")
comparison = optimizer.compare_with_baseline(study)

print("\nQuick test completed!")
