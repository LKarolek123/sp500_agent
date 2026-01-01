"""
Risk Analysis Module

Comprehensive risk metrics calculation:
- Value at Risk (VaR) - 95% and 99% confidence levels
- Conditional Value at Risk (CVaR/Expected Shortfall)
- Sharpe Ratio - risk-adjusted returns
- Sortino Ratio - downside risk focus
- Max Drawdown and Drawdown Duration
- Calmar Ratio - return/max drawdown
- Recovery Factor - total profit / max loss
- Win/Loss Ratio and Profit Factor
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, List
from scipy import stats


class RiskAnalyzer:
    """Comprehensive risk analysis for trading strategies."""
    
    def __init__(self, equity_series: pd.Series, trades_df: pd.DataFrame = None,
                 risk_free_rate: float = 0.02, annual_trading_days: int = 252):
        """
        Initialize risk analyzer.
        
        Args:
            equity_series: Daily equity curve
            trades_df: DataFrame with trade results (optional)
            risk_free_rate: Annual risk-free rate (default 2%)
            annual_trading_days: Trading days per year (default 252)
        """
        self.equity = equity_series.copy()
        self.trades = trades_df
        self.rfr = risk_free_rate
        self.annual_days = annual_trading_days
        
        # Calculate daily returns
        self.returns = self.equity.pct_change().dropna()
        
    # ========================================================================
    # VALUE AT RISK METRICS
    # ========================================================================
    
    def calculate_var(self, confidence: float = 0.95) -> float:
        """
        Calculate Value at Risk (VaR) at given confidence level.
        
        VaR tells you the maximum loss at given confidence level.
        E.g., 95% VaR = worst 5% of days.
        
        Args:
            confidence: Confidence level (0.95 = 95%, 0.99 = 99%)
            
        Returns:
            VaR as percentage
        """
        return np.percentile(self.returns, (1 - confidence) * 100)
    
    def calculate_cvar(self, confidence: float = 0.95) -> float:
        """
        Calculate Conditional Value at Risk (CVaR / Expected Shortfall).
        
        Average loss in worst (1-confidence)% of cases.
        More extreme than VaR.
        
        Args:
            confidence: Confidence level
            
        Returns:
            CVaR as percentage
        """
        var = self.calculate_var(confidence)
        return self.returns[self.returns <= var].mean()
    
    # ========================================================================
    # RETURN METRICS
    # ========================================================================
    
    def calculate_sharpe_ratio(self) -> float:
        """
        Calculate Sharpe Ratio.
        
        Higher is better. Measures return per unit of risk.
        Formula: (annual_return - risk_free_rate) / annual_std
        """
        annual_return = self.returns.mean() * self.annual_days
        annual_std = self.returns.std() * np.sqrt(self.annual_days)
        
        if annual_std == 0:
            return 0
        
        return (annual_return - self.rfr) / annual_std
    
    def calculate_sortino_ratio(self) -> float:
        """
        Calculate Sortino Ratio.
        
        Like Sharpe but only penalizes downside volatility.
        Better for non-normal distributions.
        """
        annual_return = self.returns.mean() * self.annual_days
        
        # Downside standard deviation
        downside_returns = self.returns[self.returns < 0]
        if len(downside_returns) == 0:
            return float('inf') if annual_return > 0 else 0
        
        downside_std = downside_returns.std() * np.sqrt(self.annual_days)
        
        if downside_std == 0:
            return 0
        
        return (annual_return - self.rfr) / downside_std
    
    def calculate_calmar_ratio(self) -> float:
        """
        Calculate Calmar Ratio.
        
        Annual return / max drawdown.
        Higher is better (good returns with small drawdown).
        """
        annual_return = self.returns.mean() * self.annual_days * 100
        max_dd = self.calculate_max_drawdown()
        
        if max_dd == 0:
            return 0
        
        return annual_return / abs(max_dd)
    
    # ========================================================================
    # DRAWDOWN METRICS
    # ========================================================================
    
    def calculate_max_drawdown(self) -> float:
        """
        Calculate maximum drawdown.
        
        Largest peak-to-trough decline.
        Returns as negative percentage.
        """
        cumulative = (1 + self.returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min() * 100
    
    def calculate_drawdown_duration(self) -> Dict[str, any]:
        """
        Analyze drawdown duration.
        
        Returns:
            Dictionary with max duration, avg duration, total days in DD
        """
        cumulative = (1 + self.returns).cumprod()
        running_max = cumulative.expanding().max()
        
        # Identify drawdown periods
        in_drawdown = cumulative < running_max
        
        # Find consecutive drawdown periods
        dd_groups = (in_drawdown != in_drawdown.shift()).cumsum()
        dd_durations = []
        
        for group_id in dd_groups.unique():
            group_mask = (dd_groups == group_id) & in_drawdown
            if group_mask.any():
                duration = group_mask.sum()
                dd_durations.append(duration)
        
        if len(dd_durations) == 0:
            return {
                'max_duration_days': 0,
                'avg_duration_days': 0,
                'total_days_in_dd': 0
            }
        
        return {
            'max_duration_days': int(max(dd_durations)),
            'avg_duration_days': int(np.mean(dd_durations)),
            'total_days_in_dd': int(sum(dd_durations))
        }
    
    def calculate_recovery_factor(self) -> float:
        """
        Calculate Recovery Factor.
        
        Total profit / maximum loss.
        Higher is better (e.g., 2.0 = $2 profit per $1 max loss).
        
        Returns 0 if no drawdown (perfect strategy).
        """
        if self.trades is None or self.trades.empty:
            return 0
        
        total_pnl = self.trades['pl'].sum()
        max_loss = self.trades['pl'].min()
        
        if max_loss >= 0:  # No losses
            return float('inf')
        
        return total_pnl / abs(max_loss)
    
    # ========================================================================
    # TRADE METRICS
    # ========================================================================
    
    def calculate_trade_metrics(self) -> Dict[str, float]:
        """
        Calculate metrics from individual trades.
        
        Returns:
            Dictionary with win rate, profit factor, etc.
        """
        if self.trades is None or self.trades.empty:
            return {
                'num_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'win_loss_ratio': 0
            }
        
        pnl = self.trades['pl']
        wins = pnl[pnl > 0]
        losses = pnl[pnl <= 0]
        
        num_trades = len(pnl)
        win_rate = len(wins) / max(num_trades, 1)
        
        sum_wins = wins.sum()
        sum_losses = abs(losses.sum())
        profit_factor = sum_wins / max(sum_losses, 1)
        
        avg_win = wins.mean() if len(wins) > 0 else 0
        avg_loss = losses.mean() if len(losses) > 0 else 0
        
        win_loss_ratio = avg_win / abs(max(avg_loss, -0.01))
        
        return {
            'num_trades': int(num_trades),
            'win_rate': float(win_rate),
            'profit_factor': float(profit_factor),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'win_loss_ratio': float(win_loss_ratio)
        }
    
    # ========================================================================
    # OVERALL RISK PROFILE
    # ========================================================================
    
    def get_risk_profile(self) -> Dict:
        """
        Calculate comprehensive risk profile.
        
        Returns:
            Dictionary with all major risk metrics
        """
        # Calculate all metrics
        annual_return = self.returns.mean() * self.annual_days * 100
        annual_volatility = self.returns.std() * np.sqrt(self.annual_days) * 100
        
        years = len(self.equity) / self.annual_days
        if years > 0:
            cagr = ((self.equity.iloc[-1] / self.equity.iloc[0]) ** (1/years) - 1) * 100
        else:
            cagr = 0
        
        profile = {
            # Return metrics
            'annual_return_pct': float(annual_return),
            'cagr_pct': float(cagr),
            'total_return_pct': float(((self.equity.iloc[-1] / self.equity.iloc[0]) - 1) * 100),
            
            # Volatility
            'annual_volatility_pct': float(annual_volatility),
            
            # Risk metrics
            'sharpe_ratio': float(self.calculate_sharpe_ratio()),
            'sortino_ratio': float(self.calculate_sortino_ratio()),
            'calmar_ratio': float(self.calculate_calmar_ratio()),
            
            # Drawdown
            'max_drawdown_pct': float(self.calculate_max_drawdown()),
            'var_95_pct': float(self.calculate_var(0.95) * 100),
            'var_99_pct': float(self.calculate_var(0.99) * 100),
            'cvar_95_pct': float(self.calculate_cvar(0.95) * 100),
            'cvar_99_pct': float(self.calculate_cvar(0.99) * 100),
            
            # Drawdown duration
            **self.calculate_drawdown_duration(),
            'recovery_factor': float(self.calculate_recovery_factor()),
            
            # Trade metrics
            **self.calculate_trade_metrics()
        }
        
        return profile
    
    def print_risk_report(self):
        """Print formatted risk report."""
        profile = self.get_risk_profile()
        
        print("\n" + "=" * 70)
        print("RISK ANALYSIS REPORT")
        print("=" * 70)
        
        print("\nRETURN METRICS:")
        print(f"  Annual Return:          {profile['annual_return_pct']:7.2f}%")
        print(f"  CAGR:                   {profile['cagr_pct']:7.2f}%")
        print(f"  Total Return:           {profile['total_return_pct']:7.2f}%")
        
        print("\nVOLATILITY & RISK-ADJUSTED:")
        print(f"  Annual Volatility:      {profile['annual_volatility_pct']:7.2f}%")
        print(f"  Sharpe Ratio:           {profile['sharpe_ratio']:7.2f}")
        print(f"  Sortino Ratio:          {profile['sortino_ratio']:7.2f}")
        print(f"  Calmar Ratio:           {profile['calmar_ratio']:7.2f}")
        
        print("\nDRAWDOWN ANALYSIS:")
        print(f"  Max Drawdown:           {profile['max_drawdown_pct']:7.2f}%")
        print(f"  Max DD Duration:        {profile['max_duration_days']:7d} days")
        print(f"  Avg DD Duration:        {profile['avg_duration_days']:7d} days")
        print(f"  Total Days in DD:       {profile['total_days_in_dd']:7d} days")
        print(f"  Recovery Factor:        {profile['recovery_factor']:7.2f}")
        
        print("\nVALUE AT RISK:")
        print(f"  VaR 95%:                {profile['var_95_pct']:7.2f}%")
        print(f"  VaR 99%:                {profile['var_99_pct']:7.2f}%")
        print(f"  CVaR 95%:               {profile['cvar_95_pct']:7.2f}%")
        print(f"  CVaR 99%:               {profile['cvar_99_pct']:7.2f}%")
        
        print("\nTRADE METRICS:")
        print(f"  Total Trades:           {profile['num_trades']:7d}")
        print(f"  Win Rate:               {profile['win_rate']*100:7.1f}%")
        print(f"  Profit Factor:          {profile['profit_factor']:7.2f}")
        print(f"  Avg Win:                {profile['avg_win']:7.2f} PLN")
        print(f"  Avg Loss:               {profile['avg_loss']:7.2f} PLN")
        print(f"  Win/Loss Ratio:         {profile['win_loss_ratio']:7.2f}")


def compare_risk_profiles(profiles: Dict[str, Dict]) -> pd.DataFrame:
    """
    Compare risk profiles across multiple strategies.
    
    Args:
        profiles: Dictionary with strategy names as keys, profile dicts as values
        
    Returns:
        DataFrame with comparison
    """
    comparison_df = pd.DataFrame(profiles).T
    return comparison_df
