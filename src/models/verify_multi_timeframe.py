"""
Verify Multi-Timeframe Results and Calculate Time-Horizon Returns

Double-checks the multi-timeframe validation and calculates returns for:
1 month, 2 months, 6 months, 1 year, 2 years, 5 years, 10 years
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.models.multi_timeframe_engine import MultiTimeframeEngine
from src.models.hybrid_ma_ml_filter import generate_ma_signals
from src.backtest.simulator_core import simulate_trades
from src.backtest.metrics import compute_basic_stats
from src.features.feature_engine import build_features


def calculate_time_horizon_returns(equity_series, periods):
    """
    Calculate returns for different time horizons.
    
    Args:
        equity_series: Equity curve (pandas Series)
        periods: List of (name, days) tuples
    
    Returns:
        Dictionary with return statistics for each period
    """
    results = {}
    
    for period_name, days in periods:
        if len(equity_series) < days:
            results[period_name] = {
                'total_return': 0.0,
                'cagr': 0.0,
                'days': 0,
                'note': 'Insufficient data'
            }
            continue
        
        # Get last N days
        subset = equity_series.iloc[-days:]
        start_equity = subset.iloc[0]
        end_equity = subset.iloc[-1]
        
        total_return = ((end_equity - start_equity) / start_equity) * 100
        
        # CAGR calculation
        years = days / 252  # Trading days per year
        if years > 0 and start_equity > 0:
            cagr = ((end_equity / start_equity) ** (1/years) - 1) * 100
        else:
            cagr = 0.0
        
        results[period_name] = {
            'total_return': float(total_return),
            'cagr': float(cagr),
            'days': int(days),
            'start_equity': float(start_equity),
            'end_equity': float(end_equity)
        }
    
    return results


def verify_and_analyze(data_path='data/processed/sp500_features_H4.csv',
                       tp_mult=3.5,
                       sl_mult=1.0,
                       risk_per_trade=0.005):
    """
    Verify multi-timeframe results and calculate detailed time-horizon returns.
    """
    
    print("=" * 70)
    print("MULTI-TIMEFRAME VERIFICATION & TIME-HORIZON ANALYSIS")
    print("=" * 70)
    
    # Load and prepare data
    print(f"\n[1/4] Loading data...")
    df_raw = pd.read_csv(data_path, index_col=0, parse_dates=True)
    df_raw = df_raw.sort_index()
    print(f"  Data: {len(df_raw)} rows from {df_raw.index[0].date()} to {df_raw.index[-1].date()}")
    
    # Build features
    print(f"\n[2/4] Building features and generating signals...")
    df = build_features(df_raw)
    
    # Generate baseline
    baseline_signal = generate_ma_signals(df)
    df['signal_baseline'] = baseline_signal
    
    # Generate multi-timeframe
    engine = MultiTimeframeEngine(use_volume_filter=True)
    mt_signals = engine.run_all_methods(df)
    
    for method, signal in mt_signals.items():
        df[f'signal_mt_{method}'] = signal
    
    # Print signal counts
    print("\nSignal Counts:")
    print(f"  Baseline (MA20/MA50): {(baseline_signal != 0).sum()}")
    for method, signal in mt_signals.items():
        count = (signal != 0).sum()
        print(f"  {method:12s}: {count}")
    
    # Run backtests
    print(f"\n[3/4] Running backtests...")
    methods_to_test = {
        'baseline': 'signal_baseline',
        'consensus': 'signal_mt_consensus',
        'weighted': 'signal_mt_weighted',
        'strict': 'signal_mt_strict'
    }
    
    equity_curves = {}
    
    for method_name, signal_col in methods_to_test.items():
        print(f"  Backtesting {method_name}...")
        trades, equity = simulate_trades(
            df, signal_col=signal_col,
            tp_atr=tp_mult, sl_atr=sl_mult,
            risk_per_trade=risk_per_trade,
            initial_capital=10000.0
        )
        equity_curves[method_name] = equity
        
        stats = compute_basic_stats(trades, equity)
        final_pnl = equity.iloc[-1] - 10000
        
        print(f"    Trades: {stats.get('total_trades', 0):5d} | "
              f"Final P&L: {final_pnl:8.2f} PLN | "
              f"Win Rate: {stats.get('win_rate', 0)*100:5.1f}%")
    
    # Calculate time-horizon returns
    print(f"\n[4/4] Calculating time-horizon returns...")
    
    # Define periods (name, trading days)
    periods = [
        ('1_month', 21),      # ~1 month
        ('2_months', 42),     # ~2 months
        ('6_months', 126),    # ~6 months
        ('1_year', 252),      # ~1 year
        ('2_years', 504),     # ~2 years
        ('5_years', 1260),    # ~5 years
        ('10_years', 2520),   # ~10 years
    ]
    
    all_results = {}
    
    for method_name, equity in equity_curves.items():
        print(f"\n  {method_name.upper()}:")
        horizon_returns = calculate_time_horizon_returns(equity, periods)
        all_results[method_name] = horizon_returns
        
        for period_name, stats in horizon_returns.items():
            if 'note' in stats:
                print(f"    {period_name:10s}: {stats['note']}")
            else:
                print(f"    {period_name:10s}: Total Return: {stats['total_return']:7.2f}% | "
                      f"CAGR: {stats['cagr']:6.2f}% | "
                      f"Days: {stats['days']:4d}")
    
    # Create comparison table
    print("\n" + "=" * 70)
    print("COMPARISON TABLE: TIME-HORIZON RETURNS")
    print("=" * 70)
    
    # Build DataFrame for comparison
    comparison_data = []
    for method_name in methods_to_test.keys():
        row = {'Method': method_name}
        for period_name, _ in periods:
            if period_name in all_results[method_name]:
                row[period_name] = all_results[method_name][period_name]['total_return']
            else:
                row[period_name] = 0.0
        comparison_data.append(row)
    
    comparison_df = pd.DataFrame(comparison_data)
    print(comparison_df.to_string(index=False))
    
    # CAGR comparison
    print("\n" + "=" * 70)
    print("COMPARISON TABLE: CAGR BY TIME HORIZON")
    print("=" * 70)
    
    cagr_data = []
    for method_name in methods_to_test.keys():
        row = {'Method': method_name}
        for period_name, _ in periods:
            if period_name in all_results[method_name]:
                row[period_name] = all_results[method_name][period_name]['cagr']
            else:
                row[period_name] = 0.0
        cagr_data.append(row)
    
    cagr_df = pd.DataFrame(cagr_data)
    print(cagr_df.to_string(index=False))
    
    # Save results
    output_dir = 'experiments/exp_030_multi_timeframe'
    os.makedirs(output_dir, exist_ok=True)
    
    comparison_df.to_csv(os.path.join(output_dir, 'time_horizon_returns.csv'), index=False)
    cagr_df.to_csv(os.path.join(output_dir, 'time_horizon_cagr.csv'), index=False)
    
    print(f"\nResults saved to {output_dir}/")
    
    # Show winner for each time horizon
    print("\n" + "=" * 70)
    print("BEST STRATEGY BY TIME HORIZON")
    print("=" * 70)
    
    for period_name, _ in periods:
        best_method = None
        best_return = -float('inf')
        
        for method_name in methods_to_test.keys():
            if period_name in all_results[method_name]:
                ret = all_results[method_name][period_name]['total_return']
                if ret > best_return:
                    best_return = ret
                    best_method = method_name
        
        if best_method:
            print(f"{period_name:10s}: {best_method:12s} ({best_return:+7.2f}%)")
    
    return all_results


def main():
    """Main entry point."""
    try:
        results = verify_and_analyze()
        print("\n" + "=" * 70)
        print("VERIFICATION COMPLETED")
        print("=" * 70)
        return results
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == '__main__':
    main()
