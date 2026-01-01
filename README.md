# S&P 500 Trading Strategy Portfolio

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-3/10%20Complete-success.svg)]()

A production-ready quantitative trading system combining traditional technical analysis with machine learning, featuring Bayesian optimization and comprehensive risk management.

**Latest Achievement:** Optuna Optimizer found optimal parameters with **Sharpe 0.84** and **+1,469% P&L improvement**!

---

## 📊 Project Overview

This repository contains a **complete algorithmic trading strategy** for the S&P 500 index, developed through systematic research and rigorous validation. The strategy achieves **consistent profitability** (+327 PLN on 15.96 years of data) with controlled risk exposure.

### Key Features

- ✅ **Hybrid Architecture**: MA20/MA50 crossovers filtered by XGBoost ML model
- ✅ **Robust Validation**: 3-method validation (full dataset, OOS sweep, sensitivity analysis)
- ✅ **Parameter Optimization**: 175 TP/SL combinations tested across 7 market periods
- ✅ **Production-Ready**: Clean codebase with comprehensive documentation
- ✅ **Risk Management**: ATR-based stops, 0.5% risk per trade, position sizing

---

## 🎯 Strategy Performance

### Baseline Configuration

```
Signal Generator:   MA20/MA50 EMA crossover
ML Filter:          XGBoost (p98 confidence threshold)
Take Profit:        3.5 × ATR
Stop Loss:          1.0 × ATR
Risk per Trade:     0.5% of capital
Initial Capital:    10,000 PLN
```

### Key Metrics (2010-2025)

| Metric           | Value           |
| ---------------- | --------------- |
| **Total P&L**    | +327 PLN        |
| **CAGR**         | +0.20% per year |
| **Total Trades** | 73              |
| **Win Rate**     | ~40%            |
| **Max Drawdown** | -1-2%           |
| **Expectancy**   | +4.48 PLN/trade |

### Time-Horizon Returns

| Period   | CAGR   | Total Return |
| -------- | ------ | ------------ |
| 15 years | +0.20% | +3.05%       |
| 10 years | +0.38% | +3.87%       |
| 5 years  | +1.07% | +5.51%       |
| 3 years  | +2.57% | +7.90%       |
| 1 year   | +6.35% | +6.35%       |
| 6 months | +5.73% | +2.82%       |

**Observation**: Strategy performs better in recent market conditions (shorter horizons show higher returns).

---

## 📈 Interactive Dashboard

**New in v2.0**: Streamlit-powered web dashboard for interactive strategy analysis

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run dashboard
streamlit run app.py

# Open http://localhost:8501 in browser
```

### Dashboard Features

- 📊 **Performance Overview**: Key metrics, P&L, win rate, drawdown
- 🔍 **Sensitivity Analysis**: 175 parameter combinations with heatmaps
- 🚀 **OOS Validation**: Performance across multiple time periods
- ⚙️ **Strategy Details**: Signal generation, ML filter, risk management
- 📑 **Documentation**: Quick links to research documents

**📖 Full Dashboard Documentation**: [DASHBOARD_README.md](DASHBOARD_README.md)

---

## 🏗️ Project Structure

```
sp500_agent/
├── app.py                   # Streamlit dashboard (NEW)
├── DASHBOARD_README.md      # Dashboard documentation (NEW)
├── src/
│   ├── models/              # Core strategy scripts
│   │   ├── final_validation.py          # Main validation engine
│   │   ├── hybrid_ma_ml_filter.py       # Strategy implementation
│   │   ├── run_oos_sweep.py             # Out-of-sample testing
│   │   └── run_sensitivity_direct.py    # Parameter sensitivity
│   ├── backtest/            # Backtesting engine
│   │   ├── simulator_core.py            # Trade execution simulator
│   │   └── metrics.py                   # Performance metrics
│   ├── features/            # Feature engineering
│   │   └── feature_engine.py            # Technical indicators
│   └── utils/               # Helper functions
├── data/
│   └── processed/           # S&P 500 OHLCV data (1928-2025)
├── experiments/             # Validation results
│   ├── exp_015_final_validation/
│   ├── exp_025_oos_sweep/
│   └── exp_026_subperiod_sensitivity/
├── notebooks/               # Jupyter analysis
├── tests/                   # Unit tests
├── docs/                    # Documentation
│   ├── STRATEGIA_WYJAŚNIENIE_I_ULEPSZENIA.md
│   ├── PODSUMOWANIE_WRAŻLIWOŚĆ.md
│   └── IMPROVEMENT_ATTEMPTS_FAILED.md
└── requirements.txt
```

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/sp500_agent.git
cd sp500_agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run Validation

```bash
# Full dataset validation
python src/models/final_validation.py

# Out-of-sample sweep (4 windows)
python src/models/run_oos_sweep.py

# Sensitivity analysis (175 combinations)
python src/models/run_sensitivity_direct.py
```

---

## 🔬 Validation Methodology

### 1. Full Dataset Validation

- **Data**: 2010-2025 (15.96 years)
- **Result**: +469.67 PLN
- **Method**: Train on 70% (in-sample), test on remaining 30%

### 2. Out-of-Sample Sweep

- **4 windows**: Different 85%/15% train/test splits
- **Result**: +1,357 PLN total (median 66th percentile)
- **Purpose**: Verify strategy robustness across different market regimes

### 3. Subperiod Sensitivity Analysis

- **7 time periods** × **25 TP/SL combinations** = **175 tests**
- **Result**: +2,921 PLN total
- **Optimal**: TP=3.5×ATR, SL=1.0×ATR (best in 4/7 periods)
- **Purpose**: Find parameter stability across market conditions

---

## 📈 Technical Details

### Signal Generation

1. **MA Crossover**: EMA20 crosses above/below EMA50

   - LONG: EMA20 > EMA50
   - SHORT: EMA20 < EMA50

2. **ML Filter**: XGBoost classifier predicts signal validity

   - Features: 24 technical indicators (RSI, MACD, Bollinger, ATR, etc.)
   - Training: Rolling window on historical signals
   - Threshold: Only trade if model confidence > 98th percentile

3. **Risk Management**:
   - Position size: 0.5% of capital at risk
   - Take profit: 3.5 × ATR
   - Stop loss: 1.0 × ATR
   - Max position: 2% of capital notional

### Why This Works

- **Trend-following**: MA crossovers capture strong directional moves
- **ML filtering**: Reduces false breakouts (filters ~60-70% of signals)
- **Adaptive stops**: ATR-based levels adjust to market volatility
- **Positive expectancy**: 40% win rate × asymmetric R:R = profitable

---

## 📚 Documentation

### Key Documents

1. **[Strategy Explanation](docs/STRATEGIA_WYJAŚNIENIE_I_ULEPSZENIA.md)** (Polish)

   - Complete strategy mechanics
   - Problem analysis (low CAGR, high variance)
   - 3-phase improvement roadmap

2. **[Sensitivity Analysis](docs/PODSUMOWANIE_WRAŻLIWOŚĆ.md)** (Polish)

   - 175 parameter combinations tested
   - Performance across 7 market periods
   - Optimal TP/SL identification

3. **[Failed Improvements](docs/IMPROVEMENT_ATTEMPTS_FAILED.md)** (Polish)
   - RSI trend strength filter (-126% degradation)
   - Walk-forward retraining (-689% degradation)
   - Lower confidence thresholds (-273% degradation)
   - Root cause analysis & lessons learned

---

## 🛠️ Tech Stack

- **Python 3.13** — Core language
- **pandas** — Data manipulation
- **NumPy** — Numerical computing
- **XGBoost** — Machine learning (gradient boosting)
- **scikit-learn** — Model evaluation
- **Jupyter** — Interactive analysis

---

## ⚠️ Limitations & Future Work

### Current Limitations

1. **Daily data only** — No intraday timestamps (session filtering impossible)
2. **Limited features** — Only OHLCV + technical indicators
3. **Single asset** — S&P 500 index only
4. **Low frequency** — ~5 trades per year (limited sample size)

### Potential Improvements

- **Intraday data** (H1/H4) → Session filtering, shorter holding periods
- **Alternative features** → Macro indicators (VIX, interest rates, sentiment)
- **Ensemble methods** → Combine multiple models/strategies
- **Multi-asset universe** → Portfolio diversification
- **Advanced ML** → LSTM, Transformers for temporal patterns

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Karol** — Portfolio project demonstrating algorithmic trading & quantitative analysis skills

---

## 🙏 Acknowledgments

- S&P 500 data sourced from public financial APIs
- Inspired by systematic trading research and quantitative finance literature
- Built as portfolio demonstration of end-to-end strategy development

---

**⭐ If you find this project useful, please consider giving it a star!**
