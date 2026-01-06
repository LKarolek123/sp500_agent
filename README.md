# S&P 500 Multi-Symbol Trading Bot

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Alpaca](https://img.shields.io/badge/Broker-Alpaca-green.svg)](https://alpaca.markets)
[![Docker](https://img.shields.io/badge/Docker-Enabled-blue.svg)](https://www.docker.com/)
[![Status](https://img.shields.io/badge/Status-Live%20Trading-success.svg)]()

A **production-grade algorithmic trading bot** monitoring 8 S&P 500 stocks 24/7 on Hetzner VPS using EMA crossover strategy with proven profitability.

**Current Status**: ✅ **LIVE** on Hetzner (46.224.197.25) | 🎯 Trading Top 8 Symbols | 📈 +11.53% Avg P&L (backtest)

---

## 🎯 Strategy at a Glance

### Symbols (Top 8 Profitable)

```
TSLA (+30.87%)  DIS (+14.95%)  GOOGL (+14.10%)  JNJ (+11.37%)
JPM (+7.97%)    LLY (+6.88%)   META (+4.92%)    AMZN (+1.20%)
```

### Signal Generation

- **Fast EMA**: 10-period exponential moving average
- **Slow EMA**: 100-period exponential moving average
- **Entry Signal**: When Fast EMA crosses above/below Slow EMA
- **Exit Strategy**: Take profit at +6% or Stop Loss at -3%

### Risk Management

- **Max Concurrent Positions**: 5 trades
- **Risk Per Trade**: 0.8% of equity (~$800 on $100k account)
- **Position Sizing**: Dynamic based on ATR volatility
- **Check Interval**: Every 2 minutes (120 seconds)
- **Market Hours Only**: Skips analysis during market closure

---

## 📊 Backtest Results

### 2-Year Historical Performance (Jan 2024 - Dec 2025)

| Metric                 | Value                    |
| ---------------------- | ------------------------ |
| **Average P&L**        | +11.53%                  |
| **Symbols Profitable** | 8/8 (100%)               |
| **Total Portfolio**    | +92.27%                  |
| **Avg Trades/Symbol**  | 7.5                      |
| **Best Symbol**        | TSLA: +30.87% (83.3% WR) |
| **Worst Symbol**       | AMZN: +1.20% (37.5% WR)  |

### Individual Symbol Performance

```
TSLA   [83.3% WR]  +30.87%  STAR
DIS    [50.0% WR]  +14.95%
GOOGL  [50.0% WR]  +14.10%
JNJ    [40.0% WR]  +11.37%
JPM    [50.0% WR]   +7.97%
LLY    [40.0% WR]   +6.88%
META   [33.3% WR]   +4.92%
AMZN   [37.5% WR]   +1.20%
```

---

## 🚀 Quick Start

### Local Testing (Backtest)

```bash
# Install dependencies
pip install -r requirements.txt

# Run backtest on top 8 symbols
python test_top_8.py

# Run backtest on all 18 S&P 500 stocks
python test_all_18.py
```

### Live Trading Setup

#### 1. Get Alpaca API Keys

```bash
# Sign up for paper trading: https://app.alpaca.markets/signup
# Get API keys from dashboard
```

#### 2. Configure Environment

```bash
# Create .env file
echo "ALPACA_API_KEY=your_api_key" > .env
echo "ALPACA_SECRET_KEY=your_secret_key" >> .env
echo "ALPACA_BASE_URL=https://paper-api.alpaca.markets" >> .env
```

#### 3. Run Locally

```bash
# Test locally (interactive mode)
python src/live/live_trader_multi.py

# Auto-start without confirmation
python src/live/live_trader_multi.py --auto-start

# Trade specific symbols only
python src/live/live_trader_multi.py --symbols TSLA GOOGL AMZN
```

#### 4. Deploy to Docker

```bash
# Build image
docker build -t sp500-bot:v2 .

# Run container
docker run -d --name sp500-bot --restart unless-stopped \
  -e ALPACA_API_KEY="your_api_key" \
  -e ALPACA_SECRET_KEY="your_secret_key" \
  -e ALPACA_BASE_URL="https://paper-api.alpaca.markets" \
  sp500-bot:v2

# Monitor logs
docker logs -f sp500-bot
```

---

## 📁 Project Structure

```
sp500_agent/
├── README.md                         # This file
├── Dockerfile                        # Docker configuration
├── requirements.txt                  # Python dependencies
├── .env                             # API credentials (git ignored)
├── .gitignore                       # Git ignore rules
│
├── config/
│   └── alpaca_config.json           # (Optional) config template
│
├── src/
│   ├── live/
│   │   ├── alpaca_connector.py      # REST API wrapper (batch quotes, bracket orders)
│   │   ├── live_trader_multi.py     # Main trading loop (EMA signals, position management)
│   │   └── sp500_screener.py        # Symbol lists (top 8 profitable + all 18)
│   │
│   └── backtest/
│       └── ema_backtest.py          # Backtest engine (yfinance data, EMA crossover simulation)
│
└── test_*.py
    ├── test_top_8.py                # Validate strategy on 8 symbols
    ├── test_all_18.py               # Validate strategy on 18 symbols
    └── test_ema_comparison.py       # Compare EMA 10/100 vs 20/100
```

---

## 🔧 Configuration

### Trading Parameters

Edit `src/live/live_trader_multi.py`:

```python
MultiSymbolTrader(
    fast_ma=10,              # Fast EMA period
    slow_ma=100,             # Slow EMA period
    tp_atr_mult=5.0,         # TP = 5.0 × ATR (≈6% for S&P 500)
    sl_atr_mult=1.75,        # SL = 1.75 × ATR (≈3% for S&P 500)
    risk_per_trade=0.008,    # 0.8% risk per trade
    max_positions=5,         # Max 5 concurrent trades
    check_interval=120,      # Check every 120 seconds
)
```

### Backtest Parameters

Edit `src/backtest/ema_backtest.py`:

```python
backtest_ema_crossover(
    fast=10,        # Fast EMA
    slow=100,       # Slow EMA
    tp_pct=0.06,    # 6% take profit
    sl_pct=0.03,    # 3% stop loss
)
```

---

## 📡 Live Deployment (Hetzner)

### SSH Setup

```bash
# Connect to VPS
ssh root@46.224.197.25

# Navigate to project
cd /opt/sp500_agent

# Pull latest code
git pull origin main

# Rebuild Docker image
docker build -t sp500-bot:v2 .

# Stop old container
docker stop sp500-bot && docker rm sp500-bot

# Start new container
docker run -d --name sp500-bot --restart unless-stopped \
  -e ALPACA_API_KEY="your_key" \
  -e ALPACA_SECRET_KEY="your_secret" \
  -e ALPACA_BASE_URL="https://paper-api.alpaca.markets" \
  sp500-bot:v2

# Monitor logs
docker logs -f sp500-bot
```

### Health Check

```bash
# Check container status
docker ps | grep sp500-bot

# View recent logs (last 50 lines)
docker logs --tail=50 sp500-bot

# Full logs with timestamps
docker logs --timestamps sp500-bot
```

---

## 📊 How It Works

### Trading Cycle (Every 120 seconds)

```
1. Check if market is open (NYSE hours)
   |
2. Fetch latest prices for 8 symbols (batch API call)
   |
3. Calculate EMA 10 & EMA 100 for each symbol
   |
4. Check for crossover signals (EMA10 > EMA100 or EMA10 < EMA100)
   |
5. For each signal, check if < max_positions limit
   |
6. Open bracket order: Entry + TP/SL limits
   |
7. Monitor open positions for TP/SL hits
   |
8. Log trades to stdout (JSON format)
   |
9. Wait 120 seconds, repeat
```

---

## 🧪 Testing

### Run Backtest on Top 8

```bash
python test_top_8.py
```

**Expected**: Average P&L +11.53%, 8/8 symbols profitable, TSLA as star performer

### Run Backtest on All 18

```bash
python test_all_18.py
```

**Expected**: Average P&L -0.74%, 8/18 symbols profitable (shows why we focus on top 8)

### Run EMA Strategy Comparison

```bash
python test_ema_comparison.py
```

**Expected**: EMA 10/100 outperforms EMA 20/100 on 4/5 test symbols

---

## 🔬 Version Comparison

- Files: [src/backtest/compare_versions.py](src/backtest/compare_versions.py), [src/backtest/ema_backtest.py](src/backtest/ema_backtest.py)
- Compares baseline v1 (no reversal exit, no time-stop) vs v2 (reversal exit + time-stop 3d).

### Quick Run (top8+SPY, ~900 days)

```bash
python src/backtest/compare_versions.py --symbols TSLA DIS GOOGL JNJ JPM LLY META AMZN SPY --lookback 900
```

### Single Version Runs

```bash
# v1
python src/backtest/ema_backtest.py --symbols TSLA DIS GOOGL JNJ JPM LLY META AMZN SPY --lookback 900 --no-reversal-exit

# v2
python src/backtest/ema_backtest.py --symbols TSLA DIS GOOGL JNJ JPM LLY META AMZN SPY --lookback 900 --time-stop-days 3
```

### Notes

- In our latest run, v1 showed higher average P&L% on the last ~900 days for top8+SPY.
- Results vary with period/symbols; tune parameters to preference.

---

## 📝 API Integration

### Alpaca REST API v2

- **Broker**: Alpaca Securities
- **Account Type**: Paper Trading (simulated, no real money)
- **Features Used**:
  - Batch quotes (get prices for multiple symbols)
  - Bracket orders (entry + TP/SL in single call)
  - Position management (current open trades)
  - Account info (equity, buying power)

### Data Source

- **Historical Data**: yfinance (Yahoo Finance)
- **Live Data**: Alpaca REST API
- **Timeframe**: Daily (1D) bars

---

## ⚠️ Risk Disclaimer

**This is a paper trading bot using simulated equity. NO REAL MONEY IS INVOLVED.**

- Backtest results are not guaranteed for live trading
- Past performance does not indicate future results
- Market conditions can change rapidly
- Always use proper risk management (stop losses, position sizing)
- Start with paper trading before using real capital
- Consult a financial advisor before trading with real money

---

## 🔍 Troubleshooting

### Bot Not Trading

- Check if market is open (9:30 AM - 4:00 PM EST weekdays)
- Verify API credentials in environment variables
- Check Docker logs: `docker logs sp500-bot`

### High API Rate Limits

- Increase `check_interval` (default 120 sec is safe)
- Alpaca allows 200 requests per minute for paper accounts

### Data Fetch Errors

- yfinance sometimes blocks large batch downloads
- Try reducing number of symbols or adding delays
- Use `python test_top_8.py` to test data fetching

---

## 📚 Files Reference

| File                   | Purpose                                     |
| ---------------------- | ------------------------------------------- |
| `alpaca_connector.py`  | REST API wrapper (quotes, orders, account)  |
| `live_trader_multi.py` | Main bot (EMA signals, position management) |
| `sp500_screener.py`    | Symbol lists (profitable 8 + all 18)        |
| `ema_backtest.py`      | Backtest engine (historical simulation)     |
| `Dockerfile`           | Docker container definition                 |
| `requirements.txt`     | Python package dependencies                 |

---

## 🚀 Next Steps

- [ ] Add Slack notifications for trades
- [ ] Implement performance dashboard (Streamlit)
- [ ] Add email alerts for P&L changes
- [ ] Test with different time intervals (30min, 1hr bars)
- [ ] Try other indicators (RSI, MACD) as filters
- [ ] Optimize position sizing using Kelly Criterion
- [ ] Add trailing stop losses

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

---

## 👤 Author

Karol - S&P 500 Trading Bot (2026)

**Repository**: https://github.com/LKarolek123/sp500_agent

---

## 📞 Support

For issues, questions, or improvements:

1. Check the troubleshooting section above
2. Review backtest results in `test_top_8.py` output
3. Check Docker logs for runtime errors
4. Review Alpaca API documentation: https://alpaca.markets/docs/

---

**Last Updated**: January 5, 2026 | **Bot Status**: LIVE ✅
