# 📊 PROJECT PLAN: 3EMA + BX Trender Strategy

**Deadline:** 02.02.2026 (17 dni)  
**Status:** ACTIVE 🔴

---

## 🎯 STRATEGY OVERVIEW

**Nazwa:** Triple EMA + BX Trender Hybrid  
**Timeframe:** H1, H4 (backtest), H1 para live  
**Instruments:** S&P 500 stocks (TSLA, AMZN, META, GOOGL, JNJ, JPM, DIS, LLY)  
**Expected Win Rate:** 80% (based on video backtest)

---

## 📐 TECHNICAL SPECIFICATIONS

### **INDICATORS**

#### 1. **Triple EMA (3M n1)**

```
EMA_21  = 21 period exponential moving average (FAST)
EMA_89  = 89 period exponential moving average (MEDIUM)
EMA_200 = 200 period exponential moving average (SLOW)

Trend Direction:
  UPTREND:   EMA_21 > EMA_89 > EMA_200
  DOWNTREND: EMA_21 < EMA_89 < EMA_200

Consolidation Filter:
  IF gap(EMA_21, EMA_200) < threshold → CONSOLIDATION (no trade)
  IF gap(EMA_21, EMA_200) > threshold → TRENDING (trade allowed)
```

#### 2. **BX Trender Signal Generator**

```
- Generates GREEN DOT = LONG signal
- Generates RED DOT = SHORT signal
- Trend Line: confirms signal (above/below zero line)
  - Green trend line + above zero = valid LONG
  - Red trend line + below zero = valid SHORT
```

---

## ✅ ENTRY RULES

### **LONG ENTRY**

```
Condition 1: EMA Alignment
  ✓ EMA_21 > EMA_89 > EMA_200 (uptrend)
  ✓ Gap between EMAs is significant (>2%)

Condition 2: Price Action
  ✓ Price pullback to EMA_89 (or very close)
  ✓ No entry at tops

Condition 3: BX Trender
  ✓ Green dot appears on BX signal line
  ✓ Trend line is GREEN and ABOVE zero line

Condition 4: Price Position
  ✓ Price > EMA_21 (confirms strength)

ENTRY: Market/Limit order when all conditions met
```

### **SHORT ENTRY**

```
Condition 1: EMA Alignment
  ✓ EMA_21 < EMA_89 < EMA_200 (downtrend)
  ✓ Gap between EMAs is significant

Condition 2: Price Action
  ✓ Price pullback to EMA_89 (or very close)
  ✓ No entry at bottoms

Condition 3: BX Trender
  ✓ Red dot appears on BX signal line
  ✓ Trend line is RED and BELOW zero line

Condition 4: Price Position
  ✓ Price < EMA_21 (confirms weakness)

ENTRY: Market/Limit order when all conditions met
```

---

## 📍 EXIT RULES

### **STOP LOSS**

```
LONG:  Place at last local swing low (or 1-2% below)
SHORT: Place at last local swing high (or 1-2% above)

Reason: Prevents excessive losses, avoids liquidity pools
```

### **TAKE PROFIT - Rule 1 (AGGRESSIVE)**

```
Exit LONG if:
  - Position is PROFITABLE (>0% P&L)
  - AND new SHORT signal appears on BX Trender

Exit SHORT if:
  - Position is PROFITABLE (>0% P&L)
  - AND new LONG signal appears on BX Trender

Advantage: Lock profits quickly when trend reverses
```

### **TAKE PROFIT - Rule 2 (CONSERVATIVE)**

```
Exit LONG if:
  - Position is UNPROFITABLE (<0% P&L)
  - AND new SHORT signal appears on BX Trender
  - DO NOT EXIT → Wait for SL or reversal

Exit SHORT if:
  - Position is UNPROFITABLE (<0% P&L)
  - AND new LONG signal appears on BX Trender
  - DO NOT EXIT → Wait for SL or reversal

Advantage: Avoids fakeouts, captures full moves
```

---

## 💰 POSITION SIZING & RISK MANAGEMENT

```
Risk per Trade: 1.5% of account equity
Account Size: $10,000 (test)
Risk Amount: $150 per trade

Position Size = Risk Amount / (Entry - SL distance)

Example:
  Entry: $100
  SL: $97
  Distance: $3
  Qty = $150 / $3 = 50 shares

Max Open Positions: 10 simultaneous
Max Daily Loss: 5% account equity (stop trading for day)
```

---

## 📋 IMPLEMENTATION PHASES

### **PHASE 1: CORE STRATEGY ENGINE (17-20.01)**

- [x] Strategy specification (this doc)
- [ ] EMA calculation engine
- [ ] BX Trender signal generator
- [ ] Entry/Exit logic parser
- [ ] Risk management calculator
- **Deliverable:** `strategy_engine.py` (complete)

### **PHASE 2: BACKTEST FRAMEWORK (21-26.01)**

- [ ] Historical data loader (yfinance)
- [ ] Candle-by-candle backtester
- [ ] Trade simulator with commissions
- [ ] Metrics calculator (Win%, Sharpe, DD, CAGR)
- [ ] 8 stocks validation (target 80% win rate)
- **Deliverable:** `backtest_results.json` + charts

### **PHASE 3: LIVE BOT (27-01.02)**

- [ ] Alpaca API integration
- [ ] Real-time quote fetching
- [ ] Order placement (market/limit)
- [ ] Position tracking & monitoring
- [ ] Telegram alerts
- **Deliverable:** `live_bot.py` (tested on paper)

### **PHASE 4: POLISH & CRYPTO COMPARISON (02.02)**

- [ ] Error handling & edge cases
- [ ] Crypto backtest (BTC, ETH, BNB)
- [ ] Returns comparison analysis
- [ ] Deployment on VPS
- [ ] Documentation
- **Deliverable:** `STRATEGY_RESULTS.md` + deployment

---

## 📊 BACKTEST PARAMETERS

```
Symbols: [TSLA, AMZN, META, GOOGL, JNJ, JPM, DIS, LLY]
Timeframe: H1 (hourly candles)
Start Date: 2024-01-01
End Date: 2025-12-31 (2 years)
Commission: 0.001 (0.1% per trade - realistic)
Slippage: 0.0005 (0.05%)
Initial Capital: $10,000
```

---

## 🎯 SUCCESS CRITERIA

| Metric           | Target | Status |
| ---------------- | ------ | ------ |
| Win Rate         | ≥75%   | ❌ TBD |
| Sharpe Ratio     | ≥1.5   | ❌ TBD |
| Max Drawdown     | <10%   | ❌ TBD |
| CAGR             | >20%   | ❌ TBD |
| Trades per Stock | 50+    | ❌ TBD |

---

## 📂 PROJECT STRUCTURE

```
sp500_agent/
├── src/
│   ├── strategy/
│   │   ├── __init__.py
│   │   ├── indicators.py          # EMA, BX calculations
│   │   ├── signal_generator.py    # Entry/exit logic
│   │   └── position_manager.py    # Risk management
│   ├── backtest/
│   │   ├── __init__.py
│   │   ├── backtest_engine.py     # Main backtester
│   │   ├── data_loader.py         # yfinance integration
│   │   └── metrics.py             # Performance calculations
│   ├── live/
│   │   ├── __init__.py
│   │   ├── bot.py                 # Live trading bot
│   │   ├── alpaca_client.py       # API wrapper
│   │   └── notifier.py            # Telegram alerts
│   └── utils/
│       ├── config.py
│       └── logger.py
├── config/
│   ├── strategy_config.yaml       # EMA periods, thresholds
│   ├── backtest_config.yaml       # Test parameters
│   └── live_config.yaml           # Bot settings
├── notebooks/
│   └── analysis_3ema_btrender.ipynb
├── tests/
│   ├── test_indicators.py
│   ├── test_signals.py
│   └── test_backtest.py
├── logs/
├── results/
│   ├── backtest_results.json
│   └── trades.csv
├── PROJECT_PLAN_3EMA_BTRENDER.md (this file)
└── requirements.txt
```

---

## 🔧 TECH STACK

```
Python 3.13
Pandas       - Data manipulation
NumPy        - Numerical computing
yfinance     - Stock data
Alpaca API   - Live trading
TradingView  - Signal visualization (optional)
Telegram Bot - Notifications
```

---

## 📈 EXPECTED OUTCOMES (by 02.02)

✅ Full strategy engine implemented  
✅ 80% win rate validated on backtest  
✅ Live bot tested on paper trading  
✅ 8 S&P 500 stocks profitable  
✅ Crypto comparison analysis done  
✅ Ready for live deployment

**Goal:** Profitable, automated trading system live by birthday! 🎂

---

**Last Updated:** 16.01.2026  
**Author:** GitHub Copilot + Karol
