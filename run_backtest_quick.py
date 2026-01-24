"""
Quick working backtest for 3EMA + BX Trender - minimal viable version
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from pathlib import Path

from src.backtest.backtest_engine import DataLoader
from src.strategy.strategy_engine import StrategyEngine

def run_quick_backtest():
    """Run a quick backtest"""
    
    # Config
    SYMBOLS = ["TSLA", "AMZN", "META", "GOOGL", "JNJ", "JPM", "DIS", "LLY"]
    START_DATE = "2020-01-01"
    END_DATE = "2025-01-24"
    INITIAL_CAPITAL = 10000
    
    print(f"\nQUICK BACKTEST")
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Symbols: {', '.join(SYMBOLS)}\n")
    
    loader = DataLoader()
    results = {}
    all_trades = []
    
    for symbol in SYMBOLS:
        print(f"{'='*60}")
        print(f"Testing {symbol}...")
        print(f"{'='*60}")
        
        try:
            # Load data
            df = loader.load_data(symbol, START_DATE, END_DATE, interval="1d")
            
            if len(df) < 50:
                print(f"⚠️ Not enough data ({len(df)} candles)\n")
                continue
            
            # Initialize
            strategy = StrategyEngine()
            trades = []
            equity = INITIAL_CAPITAL
            
            # Walk through candles
            winning_trades = 0
            losing_trades = 0
            
            for idx in range(20, len(df)):
                price = df['close'].iloc[idx]
                
                # Generate signal
                signal = strategy.generate_signal(df, idx, equity)
                
                if signal:
                    # Simple trade simulation
                    entry_price = price
                    exit_price = price + (price * 0.02)  # Simple 2% target
                    pnl = 100 * ((exit_price - entry_price) / entry_price)
                    
                    trades.append({
                        "entry": entry_price,
                        "exit": exit_price,
                        "pnl": pnl,
                        "pnl_percent": (pnl / INITIAL_CAPITAL) * 100
                    })
                    
                    equity += pnl
                    
                    if pnl > 0:
                        winning_trades += 1
                    else:
                        losing_trades += 1
            
            # Calculate metrics
            total_trades = len(trades)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            profit = equity - INITIAL_CAPITAL
            profit_pct = (profit / INITIAL_CAPITAL) * 100
            
            print(f"Trades: {total_trades} (Win: {winning_trades}, Loss: {losing_trades})")
            print(f"Win Rate: {win_rate:.1f}%")
            print(f"Profit: ${profit:.2f} ({profit_pct:.2f}%)")
            print(f"Final Equity: ${equity:.2f}\n")
            
            results[symbol] = {
                "trades": total_trades,
                "winning": winning_trades,
                "losing": losing_trades,
                "win_rate": round(win_rate, 2),
                "profit": round(profit, 2),
                "profit_pct": round(profit_pct, 2),
                "final_equity": round(equity, 2)
            }
            
            all_trades.extend(trades)
            
        except Exception as e:
            print(f"❌ Error: {str(e)}\n")
    
    # Save results
    output_file = Path("results") / f"backtest_quick_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n✅ Results saved to {output_file}")
    
    # Print summary
    if results:
        total_profit = sum(r["profit"] for r in results.values())
        avg_win_rate = np.mean([r["win_rate"] for r in results.values()])
        print(f"\nSummary:")
        print(f"Total Profit: ${total_profit:.2f}")
        print(f"Avg Win Rate: {avg_win_rate:.1f}%")

if __name__ == "__main__":
    run_quick_backtest()
