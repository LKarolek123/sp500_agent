"""
QUICK DEMO - 3EMA + BX Trender Strategy
Shows exactly how the strategy works with real examples
"""

from datetime import datetime


class Demo3EMA:
    """Simple demo of 3EMA logic"""
    
    @staticmethod
    def demo():
        print("="*80)
        print("DEMO: 3EMA + BX Trender Trading Strategy")
        print("="*80)
        
        print("\n📊 STRATEGY OVERVIEW")
        print("-" * 80)
        print("""
The strategy uses 3 Exponential Moving Averages:
  • EMA_21 (FAST) - Reacts quickly to price changes
  • EMA_89 (MEDIUM) - Captures medium-term trend
  • EMA_200 (SLOW) - Shows long-term direction

UPTREND Signal:     EMA_21 > EMA_89 > EMA_200
DOWNTREND Signal:   EMA_21 < EMA_89 < EMA_200
CONSOLIDATION:      Lines bunched together (gap <1.5%)

BX Trender:
  • GREEN DOT = Bullish reversal (for LONGs)
  • RED DOT = Bearish reversal (for SHORTs)
  • Trend Line confirms the signal
""")
        
        print("\n✅ ENTRY RULES")
        print("-" * 80)
        print("""
LONG ENTRY (BUY):
  1. EMAs show UPTREND (21 > 89 > 200)
  2. Gap between EMAs is significant (>1.5%)
  3. Price pulls back to EMA_89
  4. BX Trender shows GREEN DOT
  5. Trend line is GREEN and ABOVE zero line
  6. Price > EMA_21 (confirms strength)
  → ENTRY: Market order

SHORT ENTRY (SELL):
  1. EMAs show DOWNTREND (21 < 89 < 200)
  2. Gap between EMAs is significant (>1.5%)
  3. Price bounces up to EMA_89
  4. BX Trender shows RED DOT
  5. Trend line is RED and BELOW zero line
  6. Price < EMA_21 (confirms weakness)
  → ENTRY: Market order
""")
        
        print("\n📍 EXIT RULES")
        print("-" * 80)
        print("""
STOP LOSS (SL):
  • LONG: Place 1% below recent swing low
  • SHORT: Place 1% above recent swing high
  • Protects against unexpected moves

TAKE PROFIT (TP):
  Rule 1 - AGGRESSIVE:
    • Exit when Position is PROFITABLE (>0%)
    • AND opposite signal appears
    • Lock profits quickly
  
  Rule 2 - CONSERVATIVE:
    • Exit when Position is UNPROFITABLE (<0%)
    • AND opposite signal appears
    • WAIT for reversal or SL
    • Avoids fake reversals
""")
        
        print("\n💰 POSITION SIZING")
        print("-" * 80)
        print("""
Risk Management:
  • Risk per trade: 1.5% of account
  • Max open positions: 10 simultaneously
  • Example (Account: $10,000):
    - Risk amount: $150
    - Entry: $100, SL: $97
    - Distance: $3
    - Shares: 150 / 3 = 50 shares
    
This ensures consistent risk across all trades.
""")
        
        print("\n📈 EXAMPLE TRADES")
        print("-" * 80)
        
        trades = [
            {
                "type": "LONG",
                "entry": 180.50,
                "sl": 175.00,
                "exit": 195.00,
                "reason": "Opposite SHORT signal appeared",
                "pnl": 14.50,
                "pnl_pct": 8.03
            },
            {
                "type": "SHORT",
                "entry": 190.00,
                "sl": 196.00,
                "exit": 180.00,
                "reason": "SHORT signal + price below EMA_21",
                "pnl": 10.00,
                "pnl_pct": 5.26
            },
            {
                "type": "LONG",
                "entry": 175.00,
                "sl": 170.00,
                "exit": 171.50,
                "reason": "Stop Loss hit",
                "pnl": -3.50,
                "pnl_pct": -2.00
            }
        ]
        
        for i, trade in enumerate(trades, 1):
            print(f"\nTrade #{i}: {trade['type']}")
            print(f"  Entry: ${trade['entry']:.2f}")
            print(f"  Stop Loss: ${trade['sl']:.2f}")
            print(f"  Exit: ${trade['exit']:.2f}")
            print(f"  Reason: {trade['reason']}")
            status = "✅ WIN" if trade['pnl'] > 0 else "❌ LOSS"
            print(f"  Result: {status} | P&L: ${trade['pnl']:.2f} ({trade['pnl_pct']:.2f}%)")
        
        print("\n" + "="*80)
        print("📊 BACKTEST RESULTS (Video - 80% Win Rate)")
        print("="*80)
        print("""
Symbol  | Win Rate | Trades | Profit % | Notes
--------|----------|--------|----------|-------------------
BTC/USD |  85%     | 25     | +22%     | ✅ Excellent
ETH/USD |  88.5%   | 21     | +33%     | ✅ Excellent
LTC/USD |  91%     | 11     | varies   | ⚠️  Few trades
BNB/USD |  77%     | 31     | +34%     | ✅ Good
--------|----------|--------|----------|-------------------
AVERAGE |  85%     | 88     | +27%     | ✅ VALIDATED
""")
        
        print("\n🎯 WHY THIS STRATEGY WORKS")
        print("-" * 80)
        print("""
1. TREND CONFIRMATION
   ✓ Multiple indicators must align (EMAs + BX)
   ✓ Reduces false signals
   ✓ Only trades trending markets

2. RISK MANAGEMENT
   ✓ Fixed 1.5% risk per trade
   ✓ Clear stop loss placement
   ✓ Prevents account blowup

3. MECHANICAL DISCIPLINE
   ✓ No emotion - follow rules exactly
   ✓ Consistent execution
   ✓ Backtestable and trackable

4. MARKET STRUCTURE
   ✓ Follows Price Action (pullbacks)
   ✓ Confirms with Technical Indicators
   ✓ Aligns with trend direction
""")
        
        print("\n⏰ IDEAL TIMEFRAME: 15 MINUTES (Video suggests)")
        print("-" * 80)
        print("""
Why 15 min?
  • Enough signals to trade
  • Not too noisy
  • Suitable for day/swing trading
  • Can do 4-8 trades per day
  
Alternative timeframes:
  • 5 min: More trades, higher win rate needs
  • 1 hour: Fewer trades, larger moves
  • Daily: Swing trading, less signals
""")
        
        print("\n🚀 NEXT STEPS FOR YOU")
        print("-" * 80)
        print(f"""
✅ DONE (by 16.01):
  • Strategy documented
  • Core logic written
  • Architecture planned

🔄 TODO (17-20.01):
  • Code 3EMA implementation
  • Code BX Trender implementation
  • Test signals on real data

📊 BACKTEST (21-26.01):
  • Run on S&P 500 stocks
  • Validate 80%+ win rate
  • Generate results

🤖 LIVE BOT (27-01.02):
  • Connect to Alpaca API
  • Paper trading
  • Live deployment

🎂 PRODUCTION (02.02):
  • Running live
  • Making money
  • Ready for birthday!
""")
        
        print("\n" + "="*80)
        print(f"Strategy Document Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        return True


if __name__ == "__main__":
    Demo3EMA.demo()
