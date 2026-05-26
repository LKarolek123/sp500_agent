"""
Quick working backtest for 3EMA + BX Trender - minimal viable version
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from pathlib import Path

from src.backtest.backtest_engine import DataLoader
from src.strategy.strategy_engine import StrategyEngine, SignalType

def run_quick_backtest():
    """Run a quick backtest"""
    
    # Config
    SYMBOLS = ["TSLA", "AMZN", "META", "GOOGL", "JNJ", "JPM", "DIS", "LLY"]
    START_DATE = "2022-01-01"
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
            
            # Walk through candles with REAL market simulation
            winning_trades = 0
            losing_trades = 0
            open_trade = None
            
            for idx in range(200, len(df) - 1):  # Start after EMAs stabilize, leave 1 candle for exit
                current_price = df['close'].iloc[idx]
                
                # Check if we have open trade
                if open_trade:
                    # Check REAL stop loss hit
                    if df['low'].iloc[idx] <= open_trade['stop_loss']:
                        # SL hit - use SL price as exit
                        exit_price = open_trade['stop_loss']
                        entry_price = open_trade['entry']
                        pnl = (exit_price - entry_price) * open_trade['shares']  # Real position size
                        
                        trades.append({
                            "entry": entry_price,
                            "exit": exit_price,
                            "pnl": pnl,
                            "pnl_percent": (pnl / INITIAL_CAPITAL) * 100,
                            "exit_reason": "STOP_LOSS"
                        })
                        
                        equity += pnl
                        if pnl > 0:
                            winning_trades += 1
                        else:
                            losing_trades += 1
                        
                        print(f"  [{idx}] SL HIT: Entry {entry_price:.2f} -> Exit {exit_price:.2f} | PnL: ${pnl:.2f}")
                        open_trade = None
                        continue
                    
                    # Check for opposite signal (TP)
                    signal = strategy.generate_signal(df, idx, equity)
                    if signal and signal.signal_type != open_trade['direction']:
                        # Opposite signal - take profit
                        exit_price = current_price
                        entry_price = open_trade['entry']
                        pnl = (exit_price - entry_price) * open_trade['shares']  # Real position size
                        
                        trades.append({
                            "entry": entry_price,
                            "exit": exit_price,
                            "pnl": pnl,
                            "pnl_percent": (pnl / INITIAL_CAPITAL) * 100,
                            "exit_reason": "TAKE_PROFIT"
                        })
                        
                        equity += pnl
                        if pnl > 0:
                            winning_trades += 1
                        else:
                            losing_trades += 1
                        
                        print(f"  [{idx}] TP HIT: Entry {entry_price:.2f} -> Exit {exit_price:.2f} | PnL: ${pnl:.2f}")
                        open_trade = None
                        continue
                
                # Look for new entry signal (only if no open trade)
                if not open_trade:
                    signal = strategy.generate_signal(df, idx, equity)
                    
                    if signal:
                        # Enter trade with REAL position sizing (1.5% risk)
                        entry_price = current_price
                        stop_loss = entry_price * 0.99  # 1% below entry
                        
                        # Calculate position size: risk $150 (1.5% of $10k)
                        risk_per_share = entry_price - stop_loss
                        if risk_per_share > 0:
                            shares = int((equity * 0.015) / risk_per_share)  # 1.5% risk
                            shares = max(1, min(shares, int(equity / entry_price)))  # At least 1, max affordable
                        else:
                            shares = 1
                        
                        open_trade = {
                            'entry': entry_price,
                            'stop_loss': stop_loss,
                            'direction': signal.signal_type,
                            'shares': shares
                        }
                        print(f"  [{idx}] ENTRY: {entry_price:.2f} | SL: {stop_loss:.2f}")
            
            # Close any remaining open trade at last price
            if open_trade:
                exit_price = df['close'].iloc[-1]
                pnl = (exit_price - open_trade['entry']) * open_trade['shares']  # Real position size
                
                trades.append({
                    "entry": open_trade['entry'],
                    "exit": exit_price,
                    "pnl": pnl,
                    "pnl_percent": (pnl / INITIAL_CAPITAL) * 100,
                    "exit_reason": "BACKTEST_END"
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
