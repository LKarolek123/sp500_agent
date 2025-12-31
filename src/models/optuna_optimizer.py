"""
Optuna Hyperparameter Optimizer for Trading Strategy

Automatically finds optimal parameters using Bayesian optimization:
- Take Profit multiple (TP)
- Stop Loss multiple (SL)  
- Risk per trade
- MA periods (fast/slow)
- Confidence threshold percentile

Uses Optuna's Tree-structured Parzen Estimator (TPE) for efficient search.
"""

import os
import sys
import json
import pandas as pd
import numpy as np
import optuna
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.features.feature_engine import build_features
from src.backtest.simulator_core import simulate_trades
from src.backtest.metrics import compute_basic_stats


class StrategyOptimizer:
    """Optuna-based hyperparameter optimizer for trading strategies."""
    
    def __init__(self, 
                 data_path: str,
                 optimize_metric: str = 'sharpe',
                 n_trials: int = 100,
                 study_name: str = 'strategy_optimization'):
        """
        Initialize optimizer.
        
        Args:
            data_path: Path to processed data CSV
            optimize_metric: Metric to optimize ('sharpe', 'pnl', 'cagr', 'win_rate')
            n_trials: Number of optimization trials
            study_name: Name for the Optuna study
        """
        self.data_path = data_path
        self.optimize_metric = optimize_metric
        self.n_trials = n_trials
        self.study_name = study_name
        
        # Load and prepare data
        print(f"Loading data from {data_path}...")
        df_raw = pd.read_csv(data_path, index_col=0, parse_dates=True)
        df_raw = df_raw.sort_index()
        print(f"  Loaded {len(df_raw)} rows")
        
        # Build features
        print("Building features...")
        self.df = build_features(df_raw)
        print(f"  Features ready: {len(self.df)} rows")
        
    def generate_ma_signal(self, fast_ma: int, slow_ma: int) -> pd.Series:
        """Generate MA crossover signal for given periods."""
        ema_fast = self.df['Close'].ewm(span=fast_ma, adjust=False).mean()
        ema_slow = self.df['Close'].ewm(span=slow_ma, adjust=False).mean()
        
        signal = np.where(ema_fast > ema_slow, 1,
                         np.where(ema_fast < ema_slow, -1, 0))
        return pd.Series(signal, index=self.df.index, dtype=int)
    
    def objective(self, trial: optuna.Trial) -> float:
        """
        Objective function for Optuna to optimize.
        
        Args:
            trial: Optuna trial object
            
        Returns:
            Metric value to optimize (higher is better)
        """
        # Suggest hyperparameters
        tp_mult = trial.suggest_float('tp_mult', 1.5, 5.0, step=0.25)
        sl_mult = trial.suggest_float('sl_mult', 0.5, 2.0, step=0.25)
        risk_per_trade = trial.suggest_float('risk_per_trade', 0.001, 0.02, step=0.001)
        fast_ma = trial.suggest_int('fast_ma', 10, 30, step=5)
        slow_ma = trial.suggest_int('slow_ma', 40, 100, step=10)
        
        # Ensure fast < slow
        if fast_ma >= slow_ma:
            return -1e6  # Invalid configuration
        
        try:
            # Generate signals
            df_test = self.df.copy()
            signal = self.generate_ma_signal(fast_ma, slow_ma)
            df_test['signal'] = signal
            
            # Run backtest
            trades, equity = simulate_trades(
                df_test,
                signal_col='signal',
                tp_atr=tp_mult,
                sl_atr=sl_mult,
                risk_per_trade=risk_per_trade,
                initial_capital=10000.0
            )
            
            # Calculate metrics
            stats = compute_basic_stats(trades, equity)
            
            # Calculate additional metrics
            final_pnl = equity.iloc[-1] - 10000
            years = len(self.df) / 252
            cagr = ((equity.iloc[-1] / 10000) ** (1/years) - 1) * 100 if years > 0 else 0
            
            daily_returns = equity.pct_change().dropna()
            sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() > 0 else 0
            
            win_rate = stats.get('win_rate', 0)
            num_trades = stats.get('total_trades', 0)
            
            # Store metrics for reporting
            trial.set_user_attr('final_pnl', float(final_pnl))
            trial.set_user_attr('cagr', float(cagr))
            trial.set_user_attr('sharpe', float(sharpe))
            trial.set_user_attr('win_rate', float(win_rate))
            trial.set_user_attr('num_trades', int(num_trades))
            trial.set_user_attr('max_dd', float(stats.get('max_drawdown', 0) * 100))
            
            # Penalize if too few trades
            if num_trades < 20:
                return -1e6
            
            # Return metric to optimize
            if self.optimize_metric == 'sharpe':
                return sharpe
            elif self.optimize_metric == 'pnl':
                return final_pnl
            elif self.optimize_metric == 'cagr':
                return cagr
            elif self.optimize_metric == 'win_rate':
                return win_rate
            else:
                return sharpe
                
        except Exception as e:
            print(f"Trial {trial.number} failed: {e}")
            return -1e6
    
    def optimize(self, output_dir: str = 'experiments/exp_031_optuna_optimization'):
        """
        Run Optuna optimization.
        
        Args:
            output_dir: Directory to save results
            
        Returns:
            Optuna study object
        """
        os.makedirs(output_dir, exist_ok=True)
        
        print("\n" + "=" * 70)
        print("OPTUNA HYPERPARAMETER OPTIMIZATION")
        print("=" * 70)
        print(f"Metric to optimize: {self.optimize_metric}")
        print(f"Number of trials: {self.n_trials}")
        print(f"Data points: {len(self.df)}")
        
        # Create study
        study = optuna.create_study(
            study_name=self.study_name,
            direction='maximize',
            sampler=optuna.samplers.TPESampler(seed=42)
        )
        
        # Run optimization
        print("\nStarting optimization...")
        study.optimize(self.objective, n_trials=self.n_trials, show_progress_bar=True)
        
        # Print results
        print("\n" + "=" * 70)
        print("OPTIMIZATION COMPLETED")
        print("=" * 70)
        
        best_trial = study.best_trial
        print(f"\nBest Trial: #{best_trial.number}")
        print(f"  {self.optimize_metric.upper()}: {best_trial.value:.4f}")
        
        print("\nBest Parameters:")
        for key, value in best_trial.params.items():
            print(f"  {key}: {value}")
        
        print("\nBest Metrics:")
        for key, value in best_trial.user_attrs.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
        
        # Save results
        self._save_results(study, output_dir)
        
        return study
    
    def _save_results(self, study: optuna.Study, output_dir: str):
        """Save optimization results to files."""
        
        # Save best parameters
        best_params_path = os.path.join(output_dir, 'best_parameters.json')
        with open(best_params_path, 'w') as f:
            json.dump({
                'best_trial_number': study.best_trial.number,
                'best_value': study.best_value,
                'best_params': study.best_trial.params,
                'best_metrics': study.best_trial.user_attrs,
                'optimization_metric': self.optimize_metric,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
        print(f"\nBest parameters saved to {best_params_path}")
        
        # Save all trials
        trials_df = study.trials_dataframe()
        trials_path = os.path.join(output_dir, 'all_trials.csv')
        trials_df.to_csv(trials_path, index=False)
        print(f"All trials saved to {trials_path}")
        
        # Save top 10 trials
        top_trials = trials_df.nlargest(10, 'value')
        top_trials_path = os.path.join(output_dir, 'top_10_trials.csv')
        top_trials.to_csv(top_trials_path, index=False)
        print(f"Top 10 trials saved to {top_trials_path}")
        
        # Create summary
        summary = {
            'study_name': study.study_name,
            'n_trials': len(study.trials),
            'best_value': float(study.best_value),
            'optimization_metric': self.optimize_metric,
            'best_params': study.best_trial.params,
            'timestamp': datetime.now().isoformat()
        }
        
        summary_path = os.path.join(output_dir, 'optimization_summary.json')
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"Summary saved to {summary_path}")
    
    def compare_with_baseline(self, study: optuna.Study, 
                              baseline_params: Dict = None) -> Dict:
        """
        Compare optimized parameters with baseline.
        
        Args:
            study: Completed Optuna study
            baseline_params: Dictionary with baseline parameters
                            If None, uses default MA20/50, TP=3.5, SL=1.0
        
        Returns:
            Comparison dictionary
        """
        if baseline_params is None:
            baseline_params = {
                'tp_mult': 3.5,
                'sl_mult': 1.0,
                'risk_per_trade': 0.005,
                'fast_ma': 20,
                'slow_ma': 50
            }
        
        print("\n" + "=" * 70)
        print("BASELINE VS OPTIMIZED COMPARISON")
        print("=" * 70)
        
        # Test baseline
        print("\nTesting baseline parameters...")
        df_test = self.df.copy()
        signal_baseline = self.generate_ma_signal(
            baseline_params['fast_ma'],
            baseline_params['slow_ma']
        )
        df_test['signal'] = signal_baseline
        
        trades_baseline, equity_baseline = simulate_trades(
            df_test,
            signal_col='signal',
            tp_atr=baseline_params['tp_mult'],
            sl_atr=baseline_params['sl_mult'],
            risk_per_trade=baseline_params['risk_per_trade'],
            initial_capital=10000.0
        )
        
        stats_baseline = compute_basic_stats(trades_baseline, equity_baseline)
        pnl_baseline = equity_baseline.iloc[-1] - 10000
        
        years = len(self.df) / 252
        cagr_baseline = ((equity_baseline.iloc[-1] / 10000) ** (1/years) - 1) * 100
        
        daily_returns_baseline = equity_baseline.pct_change().dropna()
        sharpe_baseline = (daily_returns_baseline.mean() / daily_returns_baseline.std()) * np.sqrt(252)
        
        # Test optimized
        print("Testing optimized parameters...")
        best_params = study.best_trial.params
        signal_optimized = self.generate_ma_signal(
            best_params['fast_ma'],
            best_params['slow_ma']
        )
        df_test['signal'] = signal_optimized
        
        trades_optimized, equity_optimized = simulate_trades(
            df_test,
            signal_col='signal',
            tp_atr=best_params['tp_mult'],
            sl_atr=best_params['sl_mult'],
            risk_per_trade=best_params['risk_per_trade'],
            initial_capital=10000.0
        )
        
        stats_optimized = compute_basic_stats(trades_optimized, equity_optimized)
        pnl_optimized = equity_optimized.iloc[-1] - 10000
        
        cagr_optimized = ((equity_optimized.iloc[-1] / 10000) ** (1/years) - 1) * 100
        
        daily_returns_optimized = equity_optimized.pct_change().dropna()
        sharpe_optimized = (daily_returns_optimized.mean() / daily_returns_optimized.std()) * np.sqrt(252)
        
        # Print comparison
        print("\nBASELINE Results:")
        print(f"  P&L: {pnl_baseline:.2f} PLN")
        print(f"  CAGR: {cagr_baseline:.2f}%")
        print(f"  Sharpe: {sharpe_baseline:.2f}")
        print(f"  Win Rate: {stats_baseline.get('win_rate', 0)*100:.1f}%")
        print(f"  Trades: {stats_baseline.get('total_trades', 0)}")
        print(f"  Max DD: {stats_baseline.get('max_drawdown', 0)*100:.2f}%")
        
        print("\nOPTIMIZED Results:")
        print(f"  P&L: {pnl_optimized:.2f} PLN (+{pnl_optimized - pnl_baseline:+.2f})")
        print(f"  CAGR: {cagr_optimized:.2f}% ({cagr_optimized - cagr_baseline:+.2f}%)")
        print(f"  Sharpe: {sharpe_optimized:.2f} ({sharpe_optimized - sharpe_baseline:+.2f})")
        print(f"  Win Rate: {stats_optimized.get('win_rate', 0)*100:.1f}% "
              f"({(stats_optimized.get('win_rate', 0) - stats_baseline.get('win_rate', 0))*100:+.1f}%)")
        print(f"  Trades: {stats_optimized.get('total_trades', 0)} "
              f"({stats_optimized.get('total_trades', 0) - stats_baseline.get('total_trades', 0):+d})")
        print(f"  Max DD: {stats_optimized.get('max_drawdown', 0)*100:.2f}% "
              f"({(stats_optimized.get('max_drawdown', 0) - stats_baseline.get('max_drawdown', 0))*100:+.2f}%)")
        
        # Calculate improvement
        improvement_pct = ((pnl_optimized - pnl_baseline) / abs(pnl_baseline)) * 100 if pnl_baseline != 0 else 0
        
        print(f"\nIMPROVEMENT: {improvement_pct:+.1f}%")
        
        comparison = {
            'baseline': {
                'pnl': float(pnl_baseline),
                'cagr': float(cagr_baseline),
                'sharpe': float(sharpe_baseline),
                'win_rate': float(stats_baseline.get('win_rate', 0)),
                'trades': int(stats_baseline.get('total_trades', 0)),
                'max_dd': float(stats_baseline.get('max_drawdown', 0) * 100)
            },
            'optimized': {
                'pnl': float(pnl_optimized),
                'cagr': float(cagr_optimized),
                'sharpe': float(sharpe_optimized),
                'win_rate': float(stats_optimized.get('win_rate', 0)),
                'trades': int(stats_optimized.get('total_trades', 0)),
                'max_dd': float(stats_optimized.get('max_drawdown', 0) * 100)
            },
            'improvement_pct': float(improvement_pct)
        }
        
        return comparison


def main():
    """Main entry point."""
    
    # Configuration
    DATA_PATH = 'data/processed/sp500_features_H4.csv'
    OUTPUT_DIR = 'experiments/exp_031_optuna_optimization'
    OPTIMIZE_METRIC = 'sharpe'  # 'sharpe', 'pnl', 'cagr', 'win_rate'
    N_TRIALS = 100
    
    try:
        # Create optimizer
        optimizer = StrategyOptimizer(
            data_path=DATA_PATH,
            optimize_metric=OPTIMIZE_METRIC,
            n_trials=N_TRIALS,
            study_name='sp500_strategy_opt'
        )
        
        # Run optimization
        study = optimizer.optimize(output_dir=OUTPUT_DIR)
        
        # Compare with baseline
        comparison = optimizer.compare_with_baseline(study)
        
        # Save comparison
        comparison_path = os.path.join(OUTPUT_DIR, 'baseline_vs_optimized.json')
        with open(comparison_path, 'w') as f:
            json.dump(comparison, f, indent=2)
        print(f"\nComparison saved to {comparison_path}")
        
        print("\n" + "=" * 70)
        print("OPTIMIZATION COMPLETE!")
        print("=" * 70)
        
        return study, comparison
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == '__main__':
    main()
