"""
Multi-Timeframe Strategy Validation

Tests all 4 combination methods on S&P 500 data and compares with baseline.

Methods:
1. Majority Vote   - ≥2/3 timeframes agree
2. Consensus       - All 3 timeframes aligned
3. Weighted        - Confidence-based (30/50/20%)
4. Strict Align    - All aligned + volume confirmation
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.models.multi_timeframe_engine import MultiTimeframeEngine
from src.models.hybrid_ma_ml_filter import generate_ma_signals
from src.backtest.simulator_core import simulate_trades
from src.backtest.metrics import compute_basic_stats
from src.features.feature_engine import build_features


def run_multi_timeframe_validation(data_path='data/processed/sp500_features_H4.csv',
                                   output_dir='experiments/exp_030_multi_timeframe',
                                   tp_mult=3.5,
                                   sl_mult=1.0,
                                   risk_per_trade=0.005):
    """
    Validate all multi-timeframe methods against baseline.
    
    Args:
        data_path: Path to processed data CSV
        output_dir: Directory to save results
        tp_mult: Take profit multiple of ATR
        sl_mult: Stop loss multiple of ATR
        risk_per_trade: Risk per trade (fraction of capital)
    
    Returns:
        Dictionary with results for all methods
    """
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 70)
    print("MULTI-TIMEFRAME STRATEGY VALIDATION")
    print("=" * 70)
    
    # Load and prepare data
    print(f"\n[1/5] Loading data from {data_path}...")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Data file not found: {data_path}")
    
    df_raw = pd.read_csv(data_path, index_col=0, parse_dates=True)
    df_raw = df_raw.sort_index()
    print(f"  OK Loaded {len(df_raw)} rows, {len(df_raw.columns)} columns")
    print(f"  Date range: {df_raw.index[0].date()} to {df_raw.index[-1].date()}")
    
    # Build features
    print(f"\n[2/5] Building features...")
    df = build_features(df_raw)
    print(f"  OK Added technical indicators")
    print(f"  Features: {', '.join(df.columns[-5:])}")
    
    # Generate baseline signal (MA20/MA50)
    print(f"\n[3/5] Generating baseline signal (MA20/MA50)...")
    baseline_signal = generate_ma_signals(df)
    df['signal_baseline'] = baseline_signal
    baseline_count = (baseline_signal != 0).sum()
    print(f"  OK Baseline signals: {baseline_count}")
    
    # Generate multi-timeframe signals
    print(f"\n[4/5] Generating multi-timeframe signals...")
    engine = MultiTimeframeEngine(use_volume_filter=True)
    mt_signals = engine.run_all_methods(df)
    
    # Add to dataframe
    for method, signal in mt_signals.items():
        df[f'signal_mt_{method}'] = signal
    
    stats = engine.get_signal_statistics(mt_signals)
    print("  Signal Statistics:")
    for method, stat in stats.items():
        print(f"    {method:10s}: {stat['total_signals']:4d} signals "
              f"({stat['bullish_pct']:5.1f}% up, {stat['bearish_pct']:5.1f}% down)")
    
    # Run backtests
    print(f"\n[5/5] Running backtests...")
    results = {}
    
    # Baseline
    print(f"  Testing baseline (MA20/MA50)...")
    trades_baseline, equity_baseline = simulate_trades(
        df, signal_col='signal_baseline',
        tp_atr=tp_mult, sl_atr=sl_mult,
        risk_per_trade=risk_per_trade,
        initial_capital=10000.0
    )
    stats_baseline = compute_basic_stats(trades_baseline, equity_baseline)
    
    # Calculate returns
    pnl_baseline = equity_baseline.iloc[-1] - 10000
    total_return_baseline = (pnl_baseline / 10000) * 100
    years = len(df) / 252  # Approximate years
    cagr_baseline = ((equity_baseline.iloc[-1] / 10000) ** (1/years) - 1) * 100 if years > 0 else 0
    
    # Calculate Sharpe ratio
    daily_returns = equity_baseline.pct_change().dropna()
    sharpe_baseline = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() > 0 else 0
    
    results['baseline'] = {
        'final_pnl': float(pnl_baseline),
        'final_equity': float(equity_baseline.iloc[-1]),
        'num_trades': stats_baseline.get('total_trades', baseline_count),
        'total_return': float(total_return_baseline),
        'cagr': float(cagr_baseline),
        'sharpe': float(sharpe_baseline),
        'max_dd': float(stats_baseline.get('max_drawdown', 0) * 100)
    }
    print(f"    PnL: {results['baseline']['final_pnl']:8.2f} PLN | "
          f"CAGR: {results['baseline']['cagr']:6.2f}% | "
          f"Sharpe: {results['baseline']['sharpe']:5.2f}")
    
    # Multi-timeframe methods
    for method in ['majority', 'consensus', 'weighted', 'strict']:
        print(f"  Testing {method}...")
        trades, equity = simulate_trades(
            df, signal_col=f'signal_mt_{method}',
            tp_atr=tp_mult, sl_atr=sl_mult,
            risk_per_trade=risk_per_trade,
            initial_capital=10000.0
        )
        stats_result = compute_basic_stats(trades, equity)
        
        pnl = equity.iloc[-1] - 10000
        total_return = (pnl / 10000) * 100
        cagr = ((equity.iloc[-1] / 10000) ** (1/years) - 1) * 100 if years > 0 else 0
        
        daily_returns = equity.pct_change().dropna()
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() > 0 else 0
        
        results[method] = {
            'final_pnl': float(pnl),
            'final_equity': float(equity.iloc[-1]),
            'num_trades': stats_result.get('total_trades', (mt_signals[method] != 0).sum()),
            'total_return': float(total_return),
            'cagr': float(cagr),
            'sharpe': float(sharpe),
            'max_dd': float(stats_result.get('max_drawdown', 0) * 100)
        }
        
        pnl_diff = results[method]['final_pnl'] - results['baseline']['final_pnl']
        pnl_pct = (pnl_diff / abs(results['baseline']['final_pnl'])) * 100 if results['baseline']['final_pnl'] != 0 else 0
        
        print(f"    PnL: {results[method]['final_pnl']:8.2f} PLN "
              f"({pnl_diff:+7.2f} vs baseline, {pnl_pct:+6.1f}%) | "
              f"CAGR: {results[method]['cagr']:6.2f}% | "
              f"Sharpe: {results[method]['sharpe']:5.2f}")
    
    # Create results summary
    results_df = pd.DataFrame(results).T
    results_df = results_df[[
        'num_trades', 'final_pnl', 'final_equity',
        'total_return', 'cagr', 'sharpe', 'max_dd'
    ]]
    
    # Save results
    results_path = os.path.join(output_dir, 'multi_timeframe_results.csv')
    results_df.to_csv(results_path)
    print(f"\nOK Results saved to {results_path}")
    
    # Save detailed results JSON
    results_json = os.path.join(output_dir, 'multi_timeframe_summary.json')
    with open(results_json, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'parameters': {
                'tp_mult': tp_mult,
                'sl_mult': sl_mult,
                'risk_per_trade': risk_per_trade,
                'initial_capital': 10000
            },
            'signal_stats': stats,
            'results': results
        }, f, indent=2)
    print(f"OK Summary saved to {results_json}")
    
    # Print summary table
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(results_df.to_string())
    
    # Ranking
    print("\n" + "=" * 70)
    print("RANKING BY P&L")
    print("=" * 70)
    ranking = results_df.sort_values('final_pnl', ascending=False)
    for i, (method, row) in enumerate(ranking.iterrows(), 1):
        print(f"{i}. {method:12s}: {row['final_pnl']:8.2f} PLN "
              f"({row['num_trades']:3.0f} trades, "
              f"CAGR {row['cagr']:6.2f}%, "
              f"Sharpe {row['sharpe']:5.2f})")
    
    # Save signal comparison for inspection
    signal_comparison = df[[
        'Close',
        'signal_baseline',
        'signal_mt_majority',
        'signal_mt_consensus',
        'signal_mt_weighted',
        'signal_mt_strict'
    ]].copy()
    signal_comparison.to_csv(os.path.join(output_dir, 'signal_comparison.csv'))
    print(f"\nOK Signal comparison saved to {os.path.join(output_dir, 'signal_comparison.csv')}")
    
    return results


def main():
    """Main entry point."""
    try:
        results = run_multi_timeframe_validation(
            data_path='data/processed/sp500_features_H4.csv',
            output_dir='experiments/exp_030_multi_timeframe',
            tp_mult=3.5,
            sl_mult=1.0,
            risk_per_trade=0.005
        )
        print("\nOK Multi-timeframe validation completed successfully!")
        return results
    except Exception as e:
        print(f"\nERROR during validation: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == '__main__':
    main()
