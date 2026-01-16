"""
Simplified Backtest Runner - Optimized for Speed
Uses minimal data and cached approach
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
from pathlib import Path


class SimplifiedStrategy:
    """Simplified 3EMA + BX Trender - optimized version"""
    
    def __init__(self):
        pass
    
    @staticmethod
    def calculate_ema(prices, period):
        """Fast EMA calculation"""
        ema = np.full_like(prices, np.nan, dtype=float)
        multiplier = 2 / (period + 1)
        
        # Start from period-1
        ema[period - 1] = np.mean(prices[:period])
        
        for i in range(period, len(prices)):
            ema[i] = prices[i] * multiplier + ema[i - 1] * (1 - multiplier)
        
        return ema
    
    @staticmethod
    def generate_signals(df):
        """Generate trading signals"""
        n = len(df)
        prices = df['close'].values
        
        # Calculate EMAs
        ema21 = SimplifiedStrategy.calculate_ema(prices, 21)
        ema89 = SimplifiedStrategy.calculate_ema(prices, 89)
        ema200 = SimplifiedStrategy.calculate_ema(prices, 200)
        
        signals = []
        
        for i in range(200, n):
            price = prices[i]
            e21, e89, e200 = ema21[i], ema89[i], ema200[i]
            
            if np.isnan(e21) or np.isnan(e89) or np.isnan(e200):
                continue
            
            # Gap check for consolidation
            gap = abs(e21 - e200) / e200
            if gap < 0.015:  # 1.5% threshold
                continue
            
            # LONG signal
            if e21 > e89 > e200 and price > e21:
                signals.append({
                    'idx': i,
                    'type': 'LONG',
                    'price': price,
                    'date': df.index[i]
                })
            
            # SHORT signal  
            elif e21 < e89 < e200 and price < e21:
                signals.append({
                    'idx': i,
                    'type': 'SHORT',
                    'price': price,
                    'date': df.index[i]
                })
        
        return signals


class SimpleBacktester:
    """Simple backtest engine"""
    
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        self.trades = []
    
    def backtest(self, df, symbol):
        """Run backtest"""
        
        strategy = SimplifiedStrategy()
        signals = strategy.generate_signals(df)
        
        if not signals:
            return {
                'symbol': symbol,
                'total_trades': 0,
                'win_rate': 0,
                'profit': 0,
                'profit_percent': 0
            }
        
        # Simulate trades
        wins = 0
        losses = 0
        total_profit = 0
        
        for i in range(0, len(signals) - 1):
            signal = signals[i]
            next_signal = signals[i + 1]
            
            # Entry
            entry_price = signal['price']
            
            # Exit at next signal (simplified)
            exit_price = next_signal['price']
            
            # Calculate P&L
            if signal['type'] == 'LONG':
                pnl = (exit_price - entry_price) * 100  # 100 shares
            else:
                pnl = (entry_price - exit_price) * 100
            
            total_profit += pnl
            
            if pnl > 0:
                wins += 1
            else:
                losses += 1
            
            self.trades.append({
                'symbol': symbol,
                'entry_time': signal['date'],
                'entry_price': entry_price,
                'exit_price': exit_price,
                'type': signal['type'],
                'pnl': round(pnl, 2)
            })
        
        total_trades = wins + losses
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        final_equity = self.initial_capital + total_profit
        profit_percent = (total_profit / self.initial_capital) * 100
        
        return {
            'symbol': symbol,
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'win_rate': round(win_rate, 2),
            'profit': round(total_profit, 2),
            'profit_percent': round(profit_percent, 2),
            'final_equity': round(final_equity, 2)
        }


def create_sample_data():
    """Create sample OHLCV data for testing"""
    
    print("Creating sample data for testing...")
    
    dates = pd.date_range(start='2024-01-01', end='2025-12-31', freq='1h')
    
    # Generate realistic OHLCV data
    np.random.seed(42)
    
    # Start price
    price = 100
    returns = []
    
    for _ in range(len(dates)):
        # Random walk
        r = np.random.normal(0.0001, 0.01)  # drift + volatility
        price = price * (1 + r)
        returns.append(price)
    
    df = pd.DataFrame({
        'open': returns,
        'high': [p * 1.01 for p in returns],
        'low': [p * 0.99 for p in returns],
        'close': returns,
        'volume': np.random.randint(1000000, 5000000, len(dates))
    }, index=dates)
    
    return df


def main():
    """Main test"""
    
    print("="*70)
    print("SIMPLIFIED BACKTEST - 3EMA + BX Trender")
    print("="*70 + "\n")
    
    # Create sample data
    df = create_sample_data()
    print(f"Generated sample data: {len(df)} candles from {df.index[0]} to {df.index[-1]}\n")
    
    # Run backtest
    backtester = SimpleBacktester()
    
    # Test on different symbols (we'll reuse same data with different names for demo)
    symbols = ["TSLA", "AMZN", "META", "GOOGL"]
    results = []
    
    for symbol in symbols:
        print(f"Testing {symbol}...")
        result = backtester.backtest(df, symbol)
        results.append(result)
        
        print(f"  ✅ {symbol}: {result['total_trades']} trades | "
              f"{result['win_rate']}% win rate | "
              f"${result['profit']:.2f} profit ({result['profit_percent']:.2f}%)\n")
    
    # Summary
    print("="*70)
    print("SUMMARY")
    print("="*70)
    
    avg_win_rate = np.mean([r['win_rate'] for r in results])
    total_profit = sum([r['profit'] for r in results])
    avg_profit_pct = np.mean([r['profit_percent'] for r in results])
    total_trades = sum([r['total_trades'] for r in results])
    
    print(f"Total Trades: {total_trades}")
    print(f"Average Win Rate: {avg_win_rate:.2f}%")
    print(f"Total Profit: ${total_profit:.2f}")
    print(f"Average Profit %: {avg_profit_pct:.2f}%")
    print(f"\nPer-Stock Results:")
    
    for r in results:
        print(f"  {r['symbol']}: {r['win_rate']}% | ${r['profit']:.2f} | {r['profit_percent']:.2f}%")
    
    # Save results
    output_file = Path('results/backtest_3ema_demo.json')
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_trades': total_trades,
                'avg_win_rate': round(avg_win_rate, 2),
                'total_profit': round(total_profit, 2),
                'avg_profit_pct': round(avg_profit_pct, 2)
            },
            'per_stock': results,
            'trades_sample': backtester.trades[:10]
        }, f, indent=2, default=str)
    
    print(f"\n✅ Results saved to {output_file}")
    
    return True


if __name__ == "__main__":
    main()
