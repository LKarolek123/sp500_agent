"""Test risk_analyzer module with sample data"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.backtest.risk_analyzer import RiskAnalyzer


def test_risk_analyzer():
    """Test RiskAnalyzer with sample data"""
    
    # Create sample equity curve
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=252, freq='D')
    
    # Simulated daily returns
    returns = np.random.normal(0.0005, 0.012, 252)
    equity = (1 + returns).cumprod() * 100000  # Start with 100k
    
    # Create DataFrame
    equity_curve = pd.DataFrame({
        'date': dates,
        'equity': equity,
        'returns': returns
    })
    
    print("=" * 70)
    print("RISK ANALYZER TEST")
    print("=" * 70)
    print(f"\nEquity curve shape: {equity_curve.shape}")
    print(f"Date range: {equity_curve['date'].min()} to {equity_curve['date'].max()}")
    print(f"Initial equity: ${equity_curve['equity'].iloc[0]:,.2f}")
    print(f"Final equity: ${equity_curve['equity'].iloc[-1]:,.2f}")
    
    # Initialize analyzer
    analyzer = RiskAnalyzer(equity_series=pd.Series(equity_curve['equity'].values))
    
    # Test VaR calculations
    print("\n" + "=" * 70)
    print("VALUE AT RISK")
    print("=" * 70)
    
    var_95 = analyzer.calculate_var(confidence=0.95)
    var_99 = analyzer.calculate_var(confidence=0.99)
    cvar_95 = analyzer.calculate_cvar(confidence=0.95)
    
    print(f"VaR (95% confidence): {var_95:.4f}")
    print(f"VaR (99% confidence): {var_99:.4f}")
    print(f"CVaR (95% confidence): {cvar_95:.4f}")
    
    # Test return metrics
    print("\n" + "=" * 70)
    print("RETURN METRICS")
    print("=" * 70)
    
    sharpe = analyzer.calculate_sharpe_ratio()
    sortino = analyzer.calculate_sortino_ratio()
    calmar = analyzer.calculate_calmar_ratio()
    
    print(f"Sharpe Ratio: {sharpe:.4f}")
    print(f"Sortino Ratio: {sortino:.4f}")
    print(f"Calmar Ratio: {calmar:.4f}")
    
    # Test drawdown metrics
    print("\n" + "=" * 70)
    print("DRAWDOWN ANALYSIS")
    print("=" * 70)
    
    max_dd = analyzer.calculate_max_drawdown()
    dd_duration = analyzer.calculate_drawdown_duration()
    
    print(f"Max Drawdown: {max_dd:.4f}")
    print(f"Drawdown Duration (days): {dd_duration}")
    
    # Test trade metrics (with trades passed in init)
    print("\n" + "=" * 70)
    print("TRADE METRICS")
    print("=" * 70)
    
    # Simulate some trades
    trades = pd.DataFrame({
        'entry_price': [100, 102, 101],
        'exit_price': [103, 101, 105],
        'pl': [3, -1, 4]  # profit/loss in dollars
    })
    
    # Reinitialize analyzer with trades
    analyzer_with_trades = RiskAnalyzer(
        equity_series=pd.Series(equity_curve['equity'].values),
        trades_df=trades
    )
    
    trade_metrics = analyzer_with_trades.calculate_trade_metrics()
    print(f"Win Rate: {trade_metrics.get('win_rate', 0):.2%}")
    print(f"Profit Factor: {trade_metrics.get('profit_factor', 0):.2f}")
    print(f"Avg Win: ${trade_metrics.get('avg_win', 0):.2f}")
    print(f"Avg Loss: ${trade_metrics.get('avg_loss', 0):.2f}")
    print(f"Max Consecutive Wins: {trade_metrics.get('max_consecutive_wins', 0)}")
    
    # Get full risk profile
    print("\n" + "=" * 70)
    print("FULL RISK PROFILE")
    print("=" * 70)
    
    risk_profile = analyzer_with_trades.get_risk_profile()
    for key, value in risk_profile.items():
        if isinstance(value, float):
            print(f"{key}: {value:.4f}")
        elif isinstance(value, int):
            print(f"{key}: {value}")
        elif isinstance(value, dict):
            print(f"{key}: {value}")
        else:
            print(f"{key}: {value}")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 70)


if __name__ == '__main__':
    test_risk_analyzer()
