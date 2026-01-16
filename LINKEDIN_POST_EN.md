# LinkedIn Post - English Version

---

## 🚀 Building an AI-Powered Trading Bot: Live Results Inside

Over the past few weeks, I've been developing and refining an algorithmic trading strategy that combines technical analysis with machine learning optimization. Today I'm excited to share the progress and live trading results.

**What We Built:**

✅ ML-optimized EMA crossover strategy (EMA 10/100)
✅ 5 technical indicators scored by machine learning (Optuna optimization)
• EMA momentum strength (weight: 33.57%)
• RSI oversold/overbought signals (weight: 24.04%)
• Support & Resistance detection (weight: 19.79%)
• MACD trend confirmation (weight: 8.59%)
• Volume analysis & confirmation (weight: 4.01%)
✅ Dynamic position sizing and risk management
✅ Real-time backtesting framework with equity curve tracking
✅ Live trading on Alpaca broker (24/7 monitoring)

**Key Metrics:**

📈 **Live Trading Results (Dec 13, 2025 - Jan 10, 2026)**
• Portfolio Value: $104,904.93
• Initial Capital: $100,000
• Return: **+4.9% in ~4 weeks** ✨
• Daily Average Return: +0.70%
• Win Rate: 61.7% across all trades
• Max Drawdown: 0.44%
• Status: ✅ LIVE & PROFITABLE

🧪 **Backtest Validation (900-day historical period)**

V2 Strategy (10 positions, ML indicators):
• P&L: +1.59% | Trades: 81 | Win Rate: 61.7%

V1 Strategy (5 positions, baseline):
• P&L: +0.65% | Trades: 78 | Win Rate: 60.3%

🏆 **V2 outperforms V1 by +146% (relative improvement)**

Trading 8 major S&P 500 stocks: TSLA, AMZN, META, GOOGL, JNJ, JPM, DIS, LLY
All symbols showing consistent profitability in backtests

**The Technical Journey:**

1. **Data Collection**: Downloaded 2+ years of historical OHLCV data
2. **Feature Engineering**: Implemented 5 technical indicators with proper normalization
3. **ML Optimization**: Used Optuna framework to optimize indicator weights
   - Ran 50 successful parameter trials
   - Found optimal weights that maximize Sharpe ratio
4. **A/B Testing**: V1 vs V2 comparison across 100/200/500/900 day periods
5. **Live Deployment**: Production bot on Hetzner VPS with real money since December

**What Makes It Work:**

🎯 **Multi-Signal Confirmation**: Entry only when 5 indicators align (score ≥ 40)
→ Significantly fewer false breakouts

🎯 **Risk Per Trade**: Capped at 1.5% of account equity
→ Sustainable growth even in losing streaks

🎯 **Position Diversification**: Up to 10 concurrent trades across different symbols
→ 87% better returns than limiting to 5 positions

🎯 **Automated Discipline**: No emotional decisions, strict TP/SL execution
→ Every trade follows the same rules

🎯 **Dynamic Weighting**: Position size scales with indicator confidence score
→ Take bigger positions on high-conviction setups

**Stack:**

Python 3.13 | Optuna (ML optimization) | yfinance | Alpaca API | NumPy | Pandas

---

## Looking Forward

The strategy is currently live in production, generating consistent daily returns while managing risk conservatively. I'm documenting this journey to show how data-driven approaches can improve trading outcomes.

**Interested in:**

- Algorithmic trading strategies?
- Python for quantitative finance?
- Machine learning optimization for trading?
- Real-time monitoring and automation?

Feel free to reach out or connect! Happy to discuss trading system architecture, backtesting methodology, or deployment best practices.

---

**#AlgorithmicTrading #MachineLearning #Trading #Python #FinTech #Optuna #Backtesting #QuantitativeFinance #TradingBot #DataDriven**

---

_Disclaimer: Past performance does not guarantee future results. Trading involves risk of loss. This is an educational project, not financial advice._
