# Streamlit Dashboard Documentation

## Overview

The Streamlit dashboard provides an interactive, web-based interface for exploring the S&P 500 trading strategy performance, parameter sensitivity, and validation results.

**What’s new (2026-01-02):** Added a left-nav multi-timeframe charts page (D1/H4/H1/M15) with trade markers and EMA/MACD/RSI toggles.

## Features

### 1. Performance Overview Tab

- **Key Metrics**: Total P&L, trade count, win rate, max drawdown
- **Detailed Metrics**: Expectancy, risk per trade, confidence threshold, strategy parameters
- **Risk & Returns Summary**: All essential performance indicators at a glance

### 2. Sensitivity Analysis Tab

- **175 Parameter Combinations**: Tested across 6 subperiods (2010-2025)
- **Interactive Filters**: Select period, TP multiple, SL multiple
- **Heatmaps**: Visualize P&L across parameter space
- **Period Summary**: Performance comparison across time windows

### 3. Out-of-Sample Validation Tab

- **Multiple Timeframes**: Test results on unseen market periods
- **Robustness Metrics**: Winning configuration rates, distribution analysis
- **P&L Distribution**: Histogram of configuration performance
- **Detailed Results**: Complete OOS sweep results table

### 4. Strategy Details Tab

- **Signal Generation**: MA20/MA50 EMA crossover rules
- **ML Filter**: XGBoost confidence-based signal selection
- **Risk Management**: Position sizing, take profit, stop loss logic
- **Data Quality**: Source, period, and data integrity notes

### 5. Documentation Tab

- **Quick Links**: Key documents and resources
- **GitHub Repository**: Link to full source code
- **Setup Instructions**: How to run the dashboard
- **Attribution**: Author, license, and contact info

### 6. Multi-Timeframe Charts (left nav page)

- **Timeframes**: D1 (default), H4, H1, M15 (M15 uses 6-month resample fallback)
- **Overlays**: EMA on/off with custom spans; optional MACD and RSI
- **Trade Markers**: Entries/exits rebuilt from latest Optuna best parameters
- **Controls**: Collapsible settings below chart (months back, overlays, periods)

## Installation

```bash
# Navigate to project directory
cd sp500_agent

# Install dependencies
pip install -r requirements.txt

# Or install just the dashboard dependencies
pip install streamlit plotly
```

## Running the Dashboard

```bash
# Method 1: Direct command
streamlit run app.py

# Method 2: From project root
python -m streamlit run app.py

# Dashboard will open at: http://localhost:8501
```

## Dashboard Layout

The dashboard uses a tabbed interface for organization:

```
📈 S&P 500 Trading Strategy Dashboard
├── 📊 Performance Overview    → Key metrics and summary statistics
├── 🔍 Sensitivity Analysis    → Parameter combinations and heatmaps
├── 🚀 Out-of-Sample Validation → Robustness testing across periods
├── ⚙️ Strategy Details         → Rules, filters, risk management
├── 📑 Documentation           → Resources and setup guide
└── 📈 Multi-Timeframe Charts  → D1/H4/H1/M15 price + trades + overlays
```

## Data Sources

The dashboard reads results from three key experiments:

1. **exp_015_final_validation/**

   - Files: `summary.json`, `fold_results.csv`
   - Contains: Strategy performance on full 2010-2025 dataset

2. **exp_025_oos_sweep/**

   - Files: `sweep_results.csv`
   - Contains: Out-of-sample validation across multiple time periods

3. **exp_026_subperiod_sensitivity/**
   - Files: `sensitivity_results.csv`, `parameter_consistency.csv`
   - Contains: 175 parameter combinations tested on 6 subperiods

## Key Visualizations

### Heatmap: P&L by Parameters

- X-axis: Take Profit Multiple (ATR)
- Y-axis: Stop Loss Multiple (ATR)
- Color intensity: Profit/Loss in PLN
- Filter by time period for detailed analysis

### Distribution: OOS Configuration P&L

- Histogram of P&L values across all tested configurations
- Median line for quick reference
- Identifies skew and tail risk

### Period Summary: Performance Tracking

- Tracks total P&L, average P&L, and trade count by subperiod
- Shows strategy robustness across different market conditions
- Max drawdown metrics for risk assessment

## Performance Interpretation

### Baseline Metrics

- **Total P&L**: +741.55 PLN (2010-2025)
- **Total Trades**: 73 over 15.96 years
- **Win Rate**: 66.7% (from final validation)
- **Max Drawdown**: -1.01%
- **Expectancy**: +61.80 PLN per trade

### What These Mean

- **Positive P&L**: Strategy is profitable in absolute terms
- **Low CAGR (0.2%)**: Strategy works but slowly; useful for risk diversification
- **High Win Rate**: Fewer losses than wins; good risk/reward ratio
- **Small Drawdown**: Limited downside risk; steady growth

### Sensitivity Insights

- Parameter variations show consistency across subperiods
- Best configurations improve P&L by 2-3x baseline
- Performance degrades gracefully with parameter changes
- No "cliff-edge" parameter dependencies

## Troubleshooting

### Dashboard won't start

```bash
# Check Python version (3.8+ required)
python --version

# Verify Streamlit installation
pip install --upgrade streamlit

# Run with verbose output
streamlit run app.py --logger.level=debug
```

### Data loading errors

```bash
# Check experiment files exist
ls experiments/exp_015_final_validation/
ls experiments/exp_025_oos_sweep/
ls experiments/exp_026_subperiod_sensitivity/

# Verify file permissions
chmod 644 experiments/*/*.csv
chmod 644 experiments/*/*.json
```

### Port already in use

```bash
# Run on different port
streamlit run app.py --server.port 8502
```

## Performance Tips

- **First load**: Caches data automatically with `@st.cache_data`
- **File size**: All CSVs are <10MB, loads in <1 second
- **Heatmap interactivity**: Smooth even with 175 parameter combinations
- **Responsive**: Dashboard works on desktop and tablet displays

## Extending the Dashboard

To add new features:

1. **New metric**: Add to `Performance Overview` tab

   ```python
   st.metric("Your Metric", value)
   ```

2. **New visualization**: Use `plotly` for interactive charts

   ```python
   fig = px.scatter(data, x="col1", y="col2")
   st.plotly_chart(fig, use_container_width=True)
   ```

3. **New tab**: Add to main tab definition
   ```python
   tab6 = st.tabs(["Tab 1", "Tab 2", "Tab 3", "Tab 4", "Tab 5", "Tab 6"])
   with tab6:
       # Your content here
   ```

## Configuration Files

Streamlit can be configured via `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"

[client]
showErrorDetails = true

[logger]
level = "info"
```

## Support & Documentation

- **Streamlit Docs**: https://docs.streamlit.io
- **GitHub Issues**: https://github.com/LKarolek123/sp500_agent/issues
- **Strategy Details**: See `/docs/STRATEGIA_WYJAŚNIENIE_I_ULEPSZENIA.md`

---

**Last Updated**: 2025  
**Version**: 1.1  
**Author**: Karol  
**License**: MIT
