"""
Streamlit Dashboard for S&P 500 Trading Strategy Analysis

Interactive visualization and analysis of the MA20/MA50 EMA crossover strategy
with XGBoost ML filter on S&P 500 daily data (2010-2025).

Run: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="S&P 500 Trading Strategy Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main {
        padding-top: 0rem;
    }
    h1 {
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .positive {
        color: #06a77d;
        font-weight: bold;
    }
    .negative {
        color: #d62728;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# LOAD DATA
# ============================================================================

@st.cache_data
def load_data():
    """Load all experiment results."""
    exp_path = Path("experiments")
    
    data = {}
    
    # Final validation results
    try:
        with open(exp_path / "exp_015_final_validation" / "summary.json") as f:
            data["final_validation"] = json.load(f)
        data["fold_results"] = pd.read_csv(
            exp_path / "exp_015_final_validation" / "fold_results.csv"
        )
    except Exception as e:
        st.warning(f"Could not load final validation: {e}")
    
    # OOS sweep results
    try:
        data["oos_sweep"] = pd.read_csv(
            exp_path / "exp_025_oos_sweep" / "sweep_results.csv"
        )
    except Exception as e:
        st.warning(f"Could not load OOS sweep: {e}")
    
    # Sensitivity analysis
    try:
        data["sensitivity"] = pd.read_csv(
            exp_path / "exp_026_subperiod_sensitivity" / "sensitivity_results.csv"
        )
        data["parameter_consistency"] = pd.read_csv(
            exp_path / "exp_026_subperiod_sensitivity" / "parameter_consistency.csv"
        )
    except Exception as e:
        st.warning(f"Could not load sensitivity analysis: {e}")
    
    return data

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_pnl(value):
    """Format PLN value with color."""
    if value >= 0:
        return f"<span class='positive'>+{value:.2f} PLN</span>"
    else:
        return f"<span class='negative'>{value:.2f} PLN</span>"

def format_percentage(value, decimals=2):
    """Format percentage with color."""
    fmt = f"{value:.{decimals}f}%"
    if value >= 0:
        return f"<span class='positive'>{fmt}</span>"
    else:
        return f"<span class='negative'>{fmt}</span>"

# ============================================================================
# MAIN CONTENT
# ============================================================================

data = load_data()

# Header
st.markdown("# 📈 S&P 500 Trading Strategy Dashboard")
st.markdown("""
Interactive analysis of the **MA20/MA50 EMA Crossover Strategy** with XGBoost ML Filter.
- **Data**: S&P 500 daily OHLCV (2010-2025)
- **Period**: 15.96 years | **Trades**: 73 | **Win Rate**: 40%
""")

st.divider()

# ============================================================================
# TAB LAYOUT
# ============================================================================

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Performance Overview",
    "🔍 Sensitivity Analysis",
    "🚀 Out-of-Sample Validation",
    "⚙️ Strategy Details",
    "📑 Documentation",
    "⚠️ Risk Analysis"
])

# ============================================================================
# TAB 1: PERFORMANCE OVERVIEW
# ============================================================================

with tab1:
    st.markdown("## Strategy Performance Summary")
    
    if "final_validation" in data:
        val = data["final_validation"]
        
        # Key metrics in columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total P&L",
                f"{val.get('total_pnl', 0):.2f} PLN",
                delta=None,
                delta_color="off"
            )
        
        with col2:
            st.metric(
                "Total Trades",
                int(val.get('avg_total_trades', 0)),
                delta=None,
                delta_color="off"
            )
        
        with col3:
            win_rate = val.get('avg_win_rate', 0) * 100
            st.metric(
                "Win Rate",
                f"{win_rate:.1f}%",
                delta=None,
                delta_color="off"
            )
        
        with col4:
            max_dd = val.get('avg_max_drawdown', 0) * 100
            st.metric(
                "Max Drawdown",
                f"{max_dd:.2f}%",
                delta=None,
                delta_color="off"
            )
        
        st.divider()
        
        # Detailed metrics
        st.markdown("### Detailed Metrics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Risk & Returns**")
            metrics_df = pd.DataFrame({
                "Metric": [
                    "Average Expectancy (per trade)",
                    "Risk per Trade",
                    "Confidence Threshold (p98)",
                    "Strategy Type"
                ],
                "Value": [
                    f"{val.get('avg_expectancy', 0):.2f} PLN",
                    f"{val.get('risk_per_trade', 0)*100:.1f}%",
                    f"{val.get('conf_threshold', 0):.4f}",
                    val.get('strategy', 'N/A')
                ]
            })
            st.dataframe(metrics_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("**Parameters**")
            params_df = pd.DataFrame({
                "Parameter": [
                    "Take Profit Multiple",
                    "Stop Loss Multiple",
                    "Confidence Mode",
                    "Percentile Level"
                ],
                "Value": [
                    f"{val.get('tp_mult', 0)}x ATR",
                    f"{val.get('sl_mult', 0)}x ATR",
                    val.get('conf_mode', 'N/A'),
                    f"{val.get('conf_percentile', 0)*100:.0f}th"
                ]
            })
            st.dataframe(params_df, use_container_width=True, hide_index=True)
    else:
        st.error("Final validation data not available")

# ============================================================================
# TAB 2: SENSITIVITY ANALYSIS
# ============================================================================

with tab2:
    st.markdown("## Parameter Sensitivity Analysis")
    st.markdown("*175 parameter combinations tested across 6 subperiods (2010-2025)*")
    
    if "sensitivity" in data:
        sens_df = data["sensitivity"].copy()
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            periods = sorted(sens_df["period"].unique())
            selected_period = st.selectbox("Select Period:", periods)
        
        with col2:
            filtered_df = sens_df[sens_df["period"] == selected_period]
            tp_vals = sorted(filtered_df["tp_mult"].unique())
            selected_tp = st.selectbox("TP Multiple:", tp_vals)
        
        with col3:
            filtered_df = sens_df[
                (sens_df["period"] == selected_period) & 
                (sens_df["tp_mult"] == selected_tp)
            ]
            sl_vals = sorted(filtered_df["sl_mult"].unique())
            selected_sl = st.selectbox("SL Multiple:", sl_vals)
        
        # Show selected combination
        result = sens_df[
            (sens_df["period"] == selected_period) &
            (sens_df["tp_mult"] == selected_tp) &
            (sens_df["sl_mult"] == selected_sl)
        ]
        
        if not result.empty:
            r = result.iloc[0]
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("P&L", f"{r['total_pnl']:.2f} PLN")
            with col2:
                st.metric("Trades", int(r['total_trades']))
            with col3:
                st.metric("Win Rate", f"{r['win_rate']*100:.1f}%")
            with col4:
                st.metric("Max DD", f"{r['max_drawdown']*100:.2f}%")
        
        st.divider()
        
        # Heatmap: PnL by TP and SL
        st.markdown("### P&L Heatmap (Current Period)")
        
        period_data = sens_df[sens_df["period"] == selected_period]
        pivot = period_data.pivot_table(
            values="total_pnl",
            index="sl_mult",
            columns="tp_mult",
            aggfunc="first"
        )
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale="RdYlGn",
            text=np.round(pivot.values, 0),
            texttemplate="%{text:.0f}",
            textfont={"size": 10},
            colorbar=dict(title="P&L (PLN)")
        ))
        
        fig.update_layout(
            title=f"P&L by Parameters - {selected_period}",
            xaxis_title="Take Profit Multiple (ATR)",
            yaxis_title="Stop Loss Multiple (ATR)",
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # All periods summary
        st.markdown("### Performance Across All Periods")
        
        period_summary = sens_df.groupby("period").agg({
            "total_pnl": ["sum", "mean", "count"],
            "win_rate": "mean",
            "max_drawdown": "min"
        }).round(2)
        
        period_summary.columns = ["Total P&L", "Avg P&L", "Combinations", "Avg Win Rate", "Max DD"]
        st.dataframe(period_summary, use_container_width=True)
    else:
        st.error("Sensitivity analysis data not available")

# ============================================================================
# TAB 3: OUT-OF-SAMPLE VALIDATION
# ============================================================================

with tab3:
    st.markdown("## Out-of-Sample (OOS) Validation")
    st.markdown("*Validation on unseen time periods with different market conditions*")
    
    if "oos_sweep" in data:
        oos_df = data["oos_sweep"].copy()
        
        # Summary statistics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            positive = (oos_df["total_pnl"] > 0).sum()
            st.metric("Winning Configurations", positive)
        
        with col2:
            total_pnl = oos_df["total_pnl"].sum()
            st.metric("Total P&L (All Configs)", f"{total_pnl:.2f} PLN")
        
        with col3:
            avg_wr = (oos_df["avg_win_rate"] * 100).mean()
            st.metric("Avg Win Rate", f"{avg_wr:.1f}%")
        
        st.divider()
        
        # Performance by period
        st.markdown("### Performance by Time Period")
        
        period_data = oos_df.groupby("window").agg({
            "total_pnl": "sum",
            "avg_total_trades": "sum",
            "avg_win_rate": "mean",
            "avg_max_drawdown": "min"
        }).round(2)
        
        period_data.columns = ["Total P&L", "Total Trades", "Avg Win Rate", "Max DD"]
        st.dataframe(period_data, use_container_width=True)
        
        st.divider()
        
        # P&L distribution
        st.markdown("### P&L Distribution Across Percentiles")
        
        fig = px.histogram(
            oos_df,
            x="total_pnl",
            nbins=20,
            title="Distribution of Configuration P&L Values",
            labels={"total_pnl": "P&L (PLN)", "count": "Frequency"}
        )
        fig.add_vline(
            x=oos_df["total_pnl"].median(),
            line_dash="dash",
            line_color="red",
            annotation_text="Median"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Detailed results table
        st.markdown("### Detailed OOS Results")
        st.dataframe(oos_df, use_container_width=True)
    else:
        st.error("OOS validation data not available")

# ============================================================================
# TAB 4: STRATEGY DETAILS
# ============================================================================

with tab4:
    st.markdown("## Strategy Configuration & Rules")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Signal Generation")
        st.markdown("""
        **MA20/MA50 EMA Crossover**
        
        1. **Buy Signal**: MA20 > MA50 (bullish crossover)
        2. **Sell Signal**: MA20 < MA50 (bearish crossover)
        3. **Base Entry**: Every crossover triggers a potential trade
        
        **Parameters**:
        - MA20: 20-period Exponential Moving Average
        - MA50: 50-period Exponential Moving Average
        - Data: Daily OHLCV bars
        """)
    
    with col2:
        st.markdown("### ML Filter (XGBoost)")
        st.markdown("""
        **Confidence-Based Selection**
        
        - **Model**: XGBoost classifier (trained on 2010-2020 data)
        - **Input Features**: Technical indicators + market regime
        - **Output**: Probability score (0-1)
        - **Threshold**: p98 = 0.0962 (98th percentile)
        - **Logic**: Only trade signals with P(success) > threshold
        
        **Effect**: Filters ~83% of signals, keeping highest conviction trades
        """)
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Risk Management")
        st.markdown("""
        **Position Sizing & Exits**
        
        - **Risk per Trade**: 0.5% of portfolio
        - **Take Profit**: 3.5 × ATR(14)
        - **Stop Loss**: 1.0 × ATR(14)
        - **Risk/Reward**: 3.5:1 (asymmetric)
        
        **Trade Lifetime**:
        - Closes on TP hit or SL hit
        - Typically 5-20 days per trade
        - No fixed time exits
        """)
    
    with col2:
        st.markdown("### Performance Drivers")
        st.markdown("""
        **Key Statistics**
        
        - **Trades (2010-2025)**: 73 total
        - **Win Rate**: 40% (29 winners)
        - **Avg Winner**: +27.5 PLN
        - **Avg Loser**: -14.2 PLN
        - **Profit Factor**: 1.10
        - **Expectancy**: +4.5 PLN/trade
        
        **CAGR**: +0.20% (low but positive)
        """)
    
    st.divider()
    
    st.markdown("### Data Quality Notes")
    st.markdown("""
    - **Source**: Yahoo Finance S&P 500 daily data
    - **Period**: 1928-2025 (testing on 2010-2025)
    - **Bars**: ~3,900 daily candles
    - **Missing Data**: None (NYSE trading days only)
    - **Data Label Mismatch**: Labels indicate "H4" but actual data is daily
    """)

# ============================================================================
# TAB 5: DOCUMENTATION
# ============================================================================

with tab5:
    st.markdown("## Documentation & Resources")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Key Documents")
        st.markdown("""
        📄 **[Strategy Explanation](../docs/STRATEGIA_WYJAŚNIENIE_I_ULEPSZENIA.md)**
        - Complete strategy mechanics
        - Feature engineering details
        - 3-phase improvement roadmap
        
        📄 **[Sensitivity Analysis](../docs/PODSUMOWANIE_WRAŻLIWOŚĆ.md)**
        - 175 parameter combinations
        - Robustness across subperiods
        - Parameter consistency analysis
        """)
    
    with col2:
        st.markdown("### Project Information")
        st.markdown("""
        🔗 **GitHub Repository**
        - [LKarolek123/sp500_agent](https://github.com/LKarolek123/sp500_agent)
        - Latest: Portfolio-ready clean structure
        
        📦 **Main Scripts**
        - `final_validation.py`: Run full strategy validation
        - `run_oos_sweep.py`: Out-of-sample testing
        - `run_sensitivity_direct.py`: Parameter sensitivity
        """)
    
    st.divider()
    
    st.markdown("### Running This Dashboard")
    st.code("""
# Install dependencies
pip install -r requirements.txt

# Run dashboard
streamlit run app.py

# Dashboard available at: http://localhost:8501
    """, language="bash")
    
    st.divider()
    
    st.markdown("### Contact & Attribution")
    st.markdown("""
    **Author**: Karol  
    **License**: MIT  
    **Created**: 2025  
    
    Strategy combines traditional technical analysis (EMA crossovers) with 
    modern machine learning (XGBoost) for robust S&P 500 trading on daily timeframe.
    """)

# ============================================================================
# TAB 6: RISK ANALYSIS
# ============================================================================

with tab6:
    st.markdown("## ⚠️ Risk Analysis")
    st.markdown("Advanced risk metrics and portfolio monitoring")
    
    # Load optimization results
    optuna_path = Path('experiments/exp_031_optuna_optimization/baseline_vs_optimized.json')
    if optuna_path.exists():
        with open(optuna_path) as f:
            optuna_results = json.load(f)
    else:
        optuna_results = {}
    
    # Tabs for different risk views
    risk_tab1, risk_tab2, risk_tab3 = st.tabs([
        "📈 Risk Overview",
        "⚠️ Value at Risk",
        "📉 Drawdown Analysis"
    ])
    
    # ====================================================================
    # RISK TAB 1: OVERVIEW
    # ====================================================================
    
    with risk_tab1:
        st.markdown("### Risk-Adjusted Return Metrics")
        
        # Create comparison data from Optuna results
        if optuna_results and 'baseline' in optuna_results and 'optimized' in optuna_results:
            baseline = optuna_results['baseline']
            optimized = optuna_results['optimized']
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown("#### Sharpe Ratio")
                baseline_sharpe = baseline.get('sharpe', 0)
                optimized_sharpe = optimized.get('sharpe', 0)
                st.metric("Baseline", f"{baseline_sharpe:.2f}")
                st.metric("Optimized", f"{optimized_sharpe:.2f}", 
                         delta=f"{optimized_sharpe - baseline_sharpe:.2f}")
            
            with col2:
                st.markdown("#### P&L (PLN)")
                baseline_pnl = baseline.get('final_pnl', 0)
                optimized_pnl = optimized.get('final_pnl', 0)
                st.metric("Baseline", f"{baseline_pnl:,.0f}")
                st.metric("Optimized", f"{optimized_pnl:,.0f}",
                         delta=f"{optimized_pnl - baseline_pnl:,.0f}")
            
            with col3:
                st.markdown("#### CAGR (%)")
                baseline_cagr = baseline.get('cagr', 0)
                optimized_cagr = optimized.get('cagr', 0)
                st.metric("Baseline", f"{baseline_cagr:.2f}%")
                st.metric("Optimized", f"{optimized_cagr:.2f}%",
                         delta=f"{optimized_cagr - baseline_cagr:.2f}%")
            
            with col4:
                st.markdown("#### Max Drawdown (%)")
                baseline_dd = baseline.get('max_dd', 0)
                optimized_dd = optimized.get('max_dd', 0)
                st.metric("Baseline", f"{baseline_dd:.2f}%")
                st.metric("Optimized", f"{optimized_dd:.2f}%",
                         delta=f"{optimized_dd - baseline_dd:.2f}%")
            
            st.divider()
            
            # Detailed comparison table
            st.markdown("### Detailed Risk Profile")
            
            comparison_data = []
            metrics_to_compare = [
                'final_pnl', 'cagr', 'sharpe', 'win_rate', 
                'max_dd', 'num_trades', 'profit_factor'
            ]
            
            for metric in metrics_to_compare:
                baseline_val = baseline.get(metric, 0)
                optimized_val = optimized.get(metric, 0)
                
                # Format display
                if metric == 'final_pnl':
                    baseline_display = f"{baseline_val:,.0f}"
                    optimized_display = f"{optimized_val:,.0f}"
                    label = "P&L (PLN)"
                elif metric in ['cagr', 'max_dd']:
                    baseline_display = f"{baseline_val:.2f}%"
                    optimized_display = f"{optimized_val:.2f}%"
                    label = metric.upper()
                elif metric == 'win_rate':
                    baseline_display = f"{baseline_val*100:.1f}%"
                    optimized_display = f"{optimized_val*100:.1f}%"
                    label = "Win Rate"
                elif metric == 'num_trades':
                    baseline_display = str(int(baseline_val))
                    optimized_display = str(int(optimized_val))
                    label = "Number of Trades"
                else:
                    baseline_display = f"{baseline_val:.2f}"
                    optimized_display = f"{optimized_val:.2f}"
                    label = metric.replace('_', ' ').title()
                
                comparison_data.append({
                    'Metric': label,
                    'Baseline': baseline_display,
                    'Optimized': optimized_display,
                    'Change': f"{((optimized_val - baseline_val) / abs(baseline_val) * 100 if baseline_val != 0 else 0):.1f}%"
                })
            
            comp_df = pd.DataFrame(comparison_data)
            st.dataframe(comp_df, use_container_width=True, hide_index=True)
        
        else:
            st.info("⏳ Optimization results not yet loaded. Run Optuna optimizer first.")
    
    # ====================================================================
    # RISK TAB 2: VALUE AT RISK
    # ====================================================================
    
    with risk_tab2:
        st.markdown("### Value at Risk (VaR) Analysis")
        st.markdown("""
        **VaR tells you potential losses at different confidence levels:**
        - **VaR 95%**: Maximum 5% probability of worse daily loss
        - **VaR 99%**: Maximum 1% probability of worse daily loss (tail risk)
        - **CVaR**: Average loss when VaR is exceeded (stress scenario)
        """)
        
        if optuna_results and 'baseline' in optuna_results:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### VaR Metrics (Baseline vs Optimized)")
                
                var_data = []
                for scenario, results in [("Baseline", optuna_results.get('baseline', {})),
                                         ("Optimized", optuna_results.get('optimized', {}))]:
                    var_data.append({
                        'Strategy': scenario,
                        'VaR 95%': f"{results.get('var_95', 0):.2f}%",
                        'VaR 99%': f"{results.get('var_99', 0):.2f}%",
                        'CVaR 95%': f"{results.get('cvar_95', 0):.2f}%"
                    })
                
                var_df = pd.DataFrame(var_data)
                st.dataframe(var_df, use_container_width=True, hide_index=True)
            
            with col2:
                st.markdown("#### Risk Interpretation")
                st.markdown("""
                **Baseline Performance:**
                - Higher VaR values = more extreme potential losses
                - Wider confidence intervals = greater tail risk
                
                **Optimized Performance:**
                - Lower VaR values = better downside protection
                - Tighter confidence intervals = more stable risk profile
                - Result: Achieved via tighter stop-loss (0.75x ATR) + wider take-profit
                """)
        else:
            st.info("Optimization results not available. Run Optuna optimizer first.")
    
    # ====================================================================
    # RISK TAB 3: DRAWDOWN ANALYSIS
    # ====================================================================
    
    with risk_tab3:
        st.markdown("### Drawdown Analysis")
        st.markdown("""
        **Drawdown metrics show portfolio recovery characteristics:**
        - **Max Drawdown**: Largest peak-to-trough decline
        - **Recovery Time**: How long to fully recover from losses
        - **Calmar Ratio**: Return per unit of maximum drawdown (higher = better)
        """)
        
        if optuna_results and 'baseline' in optuna_results:
            col1, col2 = st.columns(2)
            
            with col1:
                # Max Drawdown comparison chart
                dd_data = {
                    'Baseline': optuna_results['baseline'].get('max_dd', 0),
                    'Optimized': optuna_results['optimized'].get('max_dd', 0)
                }
                
                fig = go.Figure(data=[
                    go.Bar(x=list(dd_data.keys()), y=list(dd_data.values()),
                           marker=dict(color=['#d62728', '#06a77d']))
                ])
                fig.update_layout(
                    title="Maximum Drawdown Comparison",
                    yaxis_title="Drawdown (%)",
                    height=400,
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("#### Drawdown Metrics Summary")
                
                dd_summary = []
                for scenario, results in [("Baseline", optuna_results.get('baseline', {})),
                                         ("Optimized", optuna_results.get('optimized', {}))]:
                    dd_summary.append({
                        'Strategy': scenario,
                        'Max DD': f"{results.get('max_dd', 0):.2f}%",
                        'Calmar Ratio': f"{results.get('calmar', 0):.2f}",
                        'Recovery Time': "N/A (daily data)"
                    })
                
                dd_df = pd.DataFrame(dd_summary)
                st.dataframe(dd_df, use_container_width=True, hide_index=True)
        else:
            st.info("Optimization results not available.")


# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.markdown("""
<div style='text-align: center; color: #888; font-size: 0.9em; margin-top: 2rem;'>
Dashboard created with Streamlit | Data from Yahoo Finance | Last updated: 2025
</div>
""", unsafe_allow_html=True)
