"""
Risk Dashboard - Streamlit page

Advanced risk analytics and portfolio monitoring:
- Value at Risk analysis (95%, 99% confidence)
- Risk-adjusted returns (Sharpe, Sortino, Calmar ratios)
- Drawdown analysis and recovery metrics
- Trade-level statistics
- Strategy comparison
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import json

from src.backtest.risk_analyzer import RiskAnalyzer, compare_risk_profiles


def load_strategy_data(strategy_name: str):
    """Load equity curve and trades for a strategy."""
    # Map strategy names to experiment folders
    strategy_map = {
        'baseline': 'exp_015_final_validation',
        'multi_tf_strict': 'exp_030_multi_timeframe',
        'optuna_optimized': 'exp_031_optuna_optimization'
    }
    
    exp_dir = strategy_map.get(strategy_name, '')
    if not exp_dir:
        return None, None
    
    # Load results
    results_path = Path(f'experiments/{exp_dir}/multi_timeframe_results.csv')
    if results_path.exists():
        results_df = pd.read_csv(results_path)
        return results_df, None
    
    return None, None


def get_risk_profiles():
    """Get risk profiles for available strategies."""
    
    # Load baseline from exp_015
    baseline_path = Path('experiments/exp_015_final_validation/summary.json')
    if baseline_path.exists():
        with open(baseline_path) as f:
            baseline = json.load(f)
    else:
        baseline = {}
    
    # Load multi-timeframe
    mt_path = Path('experiments/exp_030_multi_timeframe/multi_timeframe_summary.json')
    if mt_path.exists():
        with open(mt_path) as f:
            mt = json.load(f)
    else:
        mt = {}
    
    # Load Optuna
    optuna_path = Path('experiments/exp_031_optuna_optimization/best_parameters.json')
    if optuna_path.exists():
        with open(optuna_path) as f:
            optuna = json.load(f)
    else:
        optuna = {}
    
    return baseline, mt, optuna


def main():
    st.markdown("## 📊 Risk Dashboard")
    st.markdown("Advanced risk metrics and portfolio analysis")
    
    # Load data
    baseline, mt, optuna = get_risk_profiles()
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Risk Overview",
        "⚠️ Value at Risk",
        "📉 Drawdown Analysis",
        "🎯 Strategy Comparison"
    ])
    
    # ========================================================================
    # TAB 1: RISK OVERVIEW
    # ========================================================================
    
    with tab1:
        st.markdown("### Risk-Adjusted Return Metrics")
        
        strategies = {
            'Baseline': baseline,
            'Multi-Timeframe': mt,
            'Optuna Optimized': optuna
        }
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Sharpe Ratio Comparison
        with col1:
            st.markdown("**Sharpe Ratio**")
            for name, profile in strategies.items():
                if profile and 'best_metrics' in profile:
                    sharpe = profile['best_metrics'].get('sharpe', 0)
                    st.metric(name, f"{sharpe:.2f}")
                elif profile and 'avg_win_rate' in profile:
                    st.metric(name, "N/A")
        
        # P&L Comparison
        with col2:
            st.markdown("**P&L (PLN)**")
            for name, profile in strategies.items():
                if profile and 'best_metrics' in profile:
                    pnl = profile['best_metrics'].get('final_pnl', 0)
                    st.metric(name, f"{pnl:,.0f}")
                elif profile and 'total_pnl' in profile:
                    pnl = profile.get('total_pnl', 0)
                    st.metric(name, f"{pnl:,.0f}")
        
        # CAGR
        with col3:
            st.markdown("**CAGR (%)**")
            for name, profile in strategies.items():
                if profile and 'best_metrics' in profile:
                    cagr = profile['best_metrics'].get('cagr', 0)
                    st.metric(name, f"{cagr:.2f}%")
                elif profile and 'n_folds' in profile:
                    st.metric(name, "N/A")
        
        # Max Drawdown
        with col4:
            st.markdown("**Max Drawdown (%)**")
            for name, profile in strategies.items():
                if profile and 'best_metrics' in profile:
                    dd = profile['best_metrics'].get('max_dd', 0)
                    st.metric(name, f"{dd:.2f}%")
                elif profile and 'avg_max_drawdown' in profile:
                    dd = profile.get('avg_max_drawdown', 0) * 100
                    st.metric(name, f"{dd:.2f}%")
        
        st.divider()
        
        # Risk Profile Details
        st.markdown("### Detailed Risk Profile")
        
        metrics_data = []
        for name, profile in strategies.items():
            if profile and 'best_metrics' in profile:
                metrics = profile['best_metrics']
                metrics_data.append({
                    'Strategy': name,
                    'P&L': f"{metrics.get('final_pnl', 0):,.0f}",
                    'CAGR': f"{metrics.get('cagr', 0):.2f}%",
                    'Sharpe': f"{metrics.get('sharpe', 0):.2f}",
                    'Win Rate': f"{metrics.get('win_rate', 0)*100:.1f}%",
                    'Max DD': f"{metrics.get('max_dd', 0):.2f}%",
                    'Trades': int(metrics.get('num_trades', 0))
                })
            elif profile and 'total_pnl' in profile:
                metrics_data.append({
                    'Strategy': name,
                    'P&L': f"{profile.get('total_pnl', 0):,.0f}",
                    'CAGR': f"{profile.get('cagr_pct', 0):.2f}%" if 'cagr_pct' in profile else "N/A",
                    'Sharpe': "N/A",
                    'Win Rate': f"{profile.get('avg_win_rate', 0)*100:.1f}%",
                    'Max DD': f"{profile.get('avg_max_drawdown', 0)*100:.2f}%",
                    'Trades': int(profile.get('avg_total_trades', 0))
                })
        
        if metrics_data:
            metrics_df = pd.DataFrame(metrics_data)
            st.dataframe(metrics_df, use_container_width=True, hide_index=True)
    
    # ========================================================================
    # TAB 2: VALUE AT RISK
    # ========================================================================
    
    with tab2:
        st.markdown("### Value at Risk (VaR) Analysis")
        st.markdown("""
        **VaR tells you potential losses at different confidence levels:**
        - **VaR 95%**: Worst case in 5% of days (daily loss)
        - **VaR 99%**: Worst case in 1% of days (extreme events)
        - **CVaR**: Average loss when VaR is exceeded (even worse case)
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### VaR Metrics")
            var_data = []
            for name, profile in strategies.items():
                if profile and 'best_metrics' in profile:
                    var_data.append({
                        'Strategy': name,
                        'VaR 95%': f"{profile.get('var_95', 0):.2f}%",
                        'VaR 99%': f"{profile.get('var_99', 0):.2f}%",
                    })
            
            if var_data:
                var_df = pd.DataFrame(var_data)
                st.dataframe(var_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("#### Risk-Free Return vs Strategy Return")
            
            # Create risk-return scatter
            risk_return_data = []
            for name, profile in strategies.items():
                if profile and 'best_metrics' in profile:
                    metrics = profile['best_metrics']
                    risk_return_data.append({
                        'Strategy': name,
                        'Risk (Volatility)': 15,  # Placeholder
                        'Return (CAGR)': metrics.get('cagr', 0),
                        'Sharpe': metrics.get('sharpe', 0)
                    })
            
            if risk_return_data:
                risk_df = pd.DataFrame(risk_return_data)
                fig = px.scatter(
                    risk_df, 
                    x='Risk (Volatility)', 
                    y='Return (CAGR)',
                    size='Sharpe',
                    hover_data=['Strategy'],
                    title='Risk vs Return Tradeoff'
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # ========================================================================
    # TAB 3: DRAWDOWN ANALYSIS
    # ========================================================================
    
    with tab3:
        st.markdown("### Drawdown Analysis")
        st.markdown("""
        **Drawdown metrics show portfolio recovery characteristics:**
        - **Max Drawdown**: Largest peak-to-trough decline
        - **Drawdown Duration**: How long to recover from losses
        - **Recovery Factor**: Total profit / max loss (higher is better)
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Maximum Drawdown Comparison")
            
            dd_data = []
            for name, profile in strategies.items():
                if profile and 'best_metrics' in profile:
                    dd_data.append({
                        'Strategy': name,
                        'Max DD %': profile['best_metrics'].get('max_dd', 0)
                    })
                elif profile and 'avg_max_drawdown' in profile:
                    dd_data.append({
                        'Strategy': name,
                        'Max DD %': profile.get('avg_max_drawdown', 0) * 100
                    })
            
            if dd_data:
                dd_df = pd.DataFrame(dd_data)
                fig = px.bar(
                    dd_df,
                    x='Strategy',
                    y='Max DD %',
                    color='Strategy',
                    title='Maximum Drawdown by Strategy'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### Risk Metrics Summary")
            
            summary_data = []
            for name, profile in strategies.items():
                if profile and 'best_metrics' in profile:
                    metrics = profile['best_metrics']
                    summary_data.append({
                        'Strategy': name,
                        'Max DD %': f"{metrics.get('max_dd', 0):.2f}%",
                        'Calmar Ratio': "N/A",
                        'Recovery Factor': "N/A"
                    })
            
            if summary_data:
                summary_df = pd.DataFrame(summary_data)
                st.dataframe(summary_df, use_container_width=True, hide_index=True)
    
    # ========================================================================
    # TAB 4: STRATEGY COMPARISON
    # ========================================================================
    
    with tab4:
        st.markdown("### Strategy Performance Comparison")
        
        # Key metrics comparison
        comparison_data = []
        for name, profile in strategies.items():
            if profile and 'best_metrics' in profile:
                metrics = profile['best_metrics']
                comparison_data.append({
                    'Strategy': name,
                    'P&L': metrics.get('final_pnl', 0),
                    'CAGR': metrics.get('cagr', 0),
                    'Sharpe': metrics.get('sharpe', 0),
                    'Max DD': metrics.get('max_dd', 0),
                    'Win Rate': metrics.get('win_rate', 0) * 100
                })
            elif profile and 'total_pnl' in profile:
                comparison_data.append({
                    'Strategy': name,
                    'P&L': profile.get('total_pnl', 0),
                    'CAGR': profile.get('cagr_pct', 0) if 'cagr_pct' in profile else 0,
                    'Sharpe': 0,
                    'Max DD': profile.get('avg_max_drawdown', 0) * 100,
                    'Win Rate': profile.get('avg_win_rate', 0) * 100
                })
        
        if comparison_data:
            comp_df = pd.DataFrame(comparison_data)
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(
                    comp_df,
                    x='Strategy',
                    y='P&L',
                    color='Strategy',
                    title='Profitability Comparison'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.line(
                    comp_df,
                    x='Strategy',
                    y='Sharpe',
                    markers=True,
                    title='Risk-Adjusted Returns (Sharpe Ratio)'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("#### Detailed Comparison Table")
            st.dataframe(comp_df, use_container_width=True, hide_index=True)


if __name__ == '__main__':
    main()
