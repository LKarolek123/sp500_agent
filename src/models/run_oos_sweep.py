"""
OOS Sweep: Test baseline strategy across multiple OOS windows and percentile thresholds.
Aggregates results and provides recommendations.
"""
import os
import json
import subprocess
import pandas as pd
from pathlib import Path

# Configuration
OOS_WINDOWS = [
    ('2010-01-01', '2015-12-31', '2010-2015'),
    ('2016-01-01', '2018-12-31', '2016-2018'),
    ('2019-01-01', '2021-12-31', '2019-2021'),
    ('2022-01-01', '2025-12-31', '2022-2025'),
]

PERCENTILES = [90, 95, 98]

PYTHON_EXE = r'C:/Users/karol/OneDrive/Desktop/habits/sp500_agent/.venv/Scripts/python.exe'
VALIDATION_SCRIPT = 'src/models/final_validation.py'
OUTPUT_DIR = Path('experiments/exp_025_oos_sweep')
WORKING_DIR = r'C:\Users\karol\OneDrive\Desktop\habits\sp500_agent'

def run_validation(oos_start, oos_end, percentile):
    """Run validation for given OOS window and percentile."""
    env = os.environ.copy()
    env['OOS_START'] = oos_start
    env['OOS_END'] = oos_end
    env['CONF_PERCENTILE'] = str(percentile)
    env['PYTHONPATH'] = WORKING_DIR
    
    try:
        result = subprocess.run(
            [PYTHON_EXE, VALIDATION_SCRIPT],
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=WORKING_DIR
        )
        
        if result.returncode == 0:
            return result.stdout, None
        else:
            return None, result.stderr
    except subprocess.TimeoutExpired:
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

def parse_summary(window_label, percentile):
    """Parse summary.json from exp_015_final_validation."""
    summary_path = Path('experiments/exp_015_final_validation/summary.json')
    if summary_path.exists():
        try:
            with open(summary_path, 'r') as f:
                data = json.load(f)
                data['window'] = window_label
                data['percentile'] = percentile
                return data
        except Exception:
            pass
    return None

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    print("="*80)
    print("OOS SWEEP: Testing baseline across multiple windows and percentiles")
    print("="*80)
    print(f"\nWindows: {len(OOS_WINDOWS)}")
    print(f"Percentiles: {PERCENTILES}")
    print(f"Total runs: {len(OOS_WINDOWS) * len(PERCENTILES)}\n")
    
    run_idx = 0
    for oos_start, oos_end, window_label in OOS_WINDOWS:
        for percentile in PERCENTILES:
            run_idx += 1
            print(f"\n[{run_idx}/{len(OOS_WINDOWS) * len(PERCENTILES)}] Running {window_label} @ p{percentile}...")
            
            stdout, stderr = run_validation(oos_start, oos_end, percentile)
            
            if stdout:
                print(f"  SUCCESS")
                summary = parse_summary(window_label, percentile)
                if summary:
                    results.append(summary)
                    print(f"  Trades: {summary.get('avg_total_trades', 0):.1f}, "
                          f"Win: {summary.get('avg_win_rate', 0)*100:.1f}%, "
                          f"Total P&L: {summary.get('total_pnl', 0):.2f} PLN")
            else:
                print(f"  FAILED")
                if stderr:
                    print(f"  Error output:\n{stderr}")
    
    if not results:
        print("\nNo results collected!")
        return
    
    # Save results
    df_results = pd.DataFrame(results)
    df_results.to_csv(OUTPUT_DIR / 'sweep_results.csv', index=False)
    
    # Summary statistics
    print("\n" + "="*80)
    print("SWEEP RESULTS SUMMARY")
    print("="*80)
    
    # Group by percentile
    for pct in PERCENTILES:
        subset = df_results[df_results['percentile'] == pct]
        if len(subset) > 0:
            print(f"\nPercentile p{pct}:")
            print(f"  Windows tested: {len(subset)}")
            print(f"  Avg trades/window: {subset['avg_total_trades'].mean():.1f}")
            print(f"  Avg win rate: {subset['avg_win_rate'].mean()*100:.2f}%")
            print(f"  Avg expectancy: {subset['avg_expectancy'].mean():.3f} PLN/trade")
            print(f"  Total P&L (all windows): {subset['total_pnl'].sum():.2f} PLN")
            print(f"  Profitable windows: {(subset['total_pnl'] > 0).sum()}/{len(subset)}")
    
    # Best configuration
    print("\n" + "="*80)
    print("BEST CONFIGURATIONS")
    print("="*80)
    
    best_total_pnl = df_results.loc[df_results['total_pnl'].idxmax()]
    print(f"\nHighest Total P&L:")
    print(f"  {best_total_pnl['window']} @ p{best_total_pnl['percentile']}")
    print(f"  Total P&L: {best_total_pnl['total_pnl']:.2f} PLN")
    print(f"  Win Rate: {best_total_pnl['avg_win_rate']*100:.2f}%")
    print(f"  Expectancy: {best_total_pnl['avg_expectancy']:.3f} PLN/trade")
    
    best_expectancy = df_results.loc[df_results['avg_expectancy'].idxmax()]
    print(f"\nHighest Expectancy:")
    print(f"  {best_expectancy['window']} @ p{best_expectancy['percentile']}")
    print(f"  Expectancy: {best_expectancy['avg_expectancy']:.3f} PLN/trade")
    print(f"  Total P&L: {best_expectancy['total_pnl']:.2f} PLN")
    print(f"  Win Rate: {best_expectancy['avg_win_rate']*100:.2f}%")
    
    # Recommendation
    print("\n" + "="*80)
    print("RECOMMENDATION")
    print("="*80)
    
    # Find most consistent percentile (highest median P&L across windows)
    pct_medians = {}
    for pct in PERCENTILES:
        subset = df_results[df_results['percentile'] == pct]
        if len(subset) > 0:
            pct_medians[pct] = subset['total_pnl'].median()
    
    if pct_medians:
        best_pct = max(pct_medians, key=lambda x: pct_medians[x])
        best_subset = df_results[df_results['percentile'] == best_pct]
        
        print(f"\nRecommended threshold: p{best_pct} (train-set percentile)")
        print(f"  Rationale: Most consistent across OOS windows")
        print(f"  Median P&L: {pct_medians[best_pct]:.2f} PLN")
        print(f"  Total P&L (all windows): {best_subset['total_pnl'].sum():.2f} PLN")
        print(f"  Profitable windows: {(best_subset['total_pnl'] > 0).sum()}/{len(best_subset)}")
        print(f"  Avg calibrated threshold: {best_subset['avg_conf_threshold'].mean():.3f}")
    
    print(f"\nResults saved to: {OUTPUT_DIR}")
    print("="*80)

if __name__ == '__main__':
    main()
