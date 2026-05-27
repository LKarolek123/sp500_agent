#!/usr/bin/env python3
"""
Quick working backtest for 3EMA + BX Trender - minimal viable version
Saves detailed per-trade CSV for post-analysis.
"""

import argparse
import pandas as pd
import numpy as np
import json
from datetime import datetime
from pathlib import Path

from src.backtest.backtest_engine import DataLoader
from src.strategy.strategy_engine import StrategyEngine, SignalType

def run_quick_backtest(
    symbols=None,
    start_date: str = "2018-01-01",
    end_date: str = "2026-05-26",
    initial_capital: float = 10000,
    risk_pct: float = 0.015
):
    """Run a quick backtest"""
    
    SYMBOLS = symbols or ["TSLA", "AMZN", "META", "GOOGL", "JNJ", "JPM", "DIS", "LLY"]
    START_DATE = start_date
    END_DATE = end_date
    INITIAL_CAPITAL = initial_capital
    RISK_PERCENT = risk_pct
    
    print(f"\nQUICK BACKTEST")
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Symbols: {', '.join(SYMBOLS)}")
    print(f"Initial Capital: ${INITIAL_CAPITAL:.2f}")
    print(f"Risk per trade: {RISK_PERCENT*100:.2f}%\n")
    
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
                print(f"Not enough data ({len(df)} candles)\n")
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
                            "symbol": symbol,
                            "entry": entry_price,
                            "exit": exit_price,
                            "shares": open_trade['shares'],
                            "entry_date": open_trade['entry_date'],
                            "exit_date": str(df['timestamp'].iloc[idx]),
                            "entry_value": round(entry_price * open_trade['shares'], 2),
                            "percent_of_equity_at_entry": round((entry_price * open_trade['shares']) / INITIAL_CAPITAL * 100, 4),
                            "risk_amount_usd": round(open_trade['shares'] * (open_trade['entry'] - open_trade['stop_loss']), 2),
                            "risk_pct_of_equity": round((open_trade['shares'] * (open_trade['entry'] - open_trade['stop_loss'])) / INITIAL_CAPITAL * 100, 6),
                            "pnl": pnl,
                            "pnl_percent": (pnl / INITIAL_CAPITAL) * 100,
                            "exit_reason": "STOP_LOSS",
                            "entry_time_idx": int(open_trade['entry_idx']),
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
                            "symbol": symbol,
                            "entry": entry_price,
                            "exit": exit_price,
                            "shares": open_trade['shares'],
                            "entry_date": open_trade['entry_date'],
                            "exit_date": str(df['timestamp'].iloc[idx]),
                            "entry_value": round(entry_price * open_trade['shares'], 2),
                            "percent_of_equity_at_entry": round((entry_price * open_trade['shares']) / INITIAL_CAPITAL * 100, 4),
                            "risk_amount_usd": round(open_trade['shares'] * (open_trade['entry'] - open_trade['stop_loss']), 2),
                            "risk_pct_of_equity": round((open_trade['shares'] * (open_trade['entry'] - open_trade['stop_loss'])) / INITIAL_CAPITAL * 100, 6),
                            "pnl": pnl,
                            "pnl_percent": (pnl / INITIAL_CAPITAL) * 100,
                            "exit_reason": "TAKE_PROFIT_OR_OPPOSITE_SIGNAL",
                            "entry_time_idx": int(open_trade['entry_idx']),
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
                        # Enter trade with REAL position sizing using the configured risk percent
                        entry_price = current_price
                        stop_loss = entry_price * 0.99  # 1% below entry
                        
                        # Calculate position size using the active equity and chosen risk percent
                        risk_per_share = entry_price - stop_loss
                        if risk_per_share > 0:
                            shares = int((equity * RISK_PERCENT) / risk_per_share)
                            shares = max(1, min(shares, int(equity / entry_price)))  # At least 1, max affordable
                        else:
                            shares = 1
                        
                        open_trade = {
                            'entry': entry_price,
                            'stop_loss': stop_loss,
                            'direction': signal.signal_type,
                            'shares': shares,
                            'entry_idx': idx,
                            'entry_date': str(df['timestamp'].iloc[idx])
                        }
                        print(f"  [{idx}] ENTRY: {entry_price:.2f} | SL: {stop_loss:.2f} | Shares: {shares}")
            
            # Close any remaining open trade at last price
            if open_trade:
                exit_price = df['close'].iloc[-1]
                pnl = (exit_price - open_trade['entry']) * open_trade['shares']  # Real position size
                
                trades.append({
                    "symbol": symbol,
                    "entry": open_trade['entry'],
                    "exit": exit_price,
                    "shares": open_trade['shares'],
                    "entry_date": open_trade['entry_date'],
                    "exit_date": str(df['timestamp'].iloc[-1]),
                    "entry_value": round(open_trade['entry'] * open_trade['shares'], 2),
                    "percent_of_equity_at_entry": round((open_trade['entry'] * open_trade['shares']) / INITIAL_CAPITAL * 100, 4),
                    "risk_amount_usd": round(open_trade['shares'] * (open_trade['entry'] - open_trade['stop_loss']), 2),
                    "risk_pct_of_equity": round((open_trade['shares'] * (open_trade['entry'] - open_trade['stop_loss'])) / INITIAL_CAPITAL * 100, 6),
                    "pnl": pnl,
                    "pnl_percent": (pnl / INITIAL_CAPITAL) * 100,
                    "exit_reason": "BACKTEST_END",
                    "entry_time_idx": int(open_trade['entry_idx']),
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
            print("Error:", repr(e))
    
    # Save results
    output_file = Path("results") / f"backtest_quick_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Save detailed trades CSV
    trades_df = None
    try:
        import pandas as _pd
        trades_df = _pd.DataFrame(all_trades)
    except Exception:
        trades_df = None

    if trades_df is not None and len(trades_df) > 0:
        csv_out = Path("results") / f"backtest_quick_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        trades_df.to_csv(csv_out, index=False)
        print(f"Detailed trades saved to {csv_out}")
    
    print(f"\nResults saved to {output_file}")
    
    # Print summary
    if results:
        total_profit = sum(r["profit"] for r in results.values())
        avg_win_rate = np.mean([r["win_rate"] for r in results.values()])
        print(f"\nSummary:")
        print(f"Total Profit: ${total_profit:.2f}")
        print(f"Avg Win Rate: {avg_win_rate:.1f}%")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quick backtest runner")
    parser.add_argument("--symbols", nargs="+", default=None, help="Symbols to test")
    parser.add_argument("--start", default="2018-01-01", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default="2026-05-26", help="End date YYYY-MM-DD")
    parser.add_argument("--capital", type=float, default=10000, help="Initial capital")
    parser.add_argument("--risk", type=float, default=0.015, help="Risk percent per trade")
    args = parser.parse_args()

    run_quick_backtest(
        symbols=args.symbols,
        start_date=args.start,
        end_date=args.end,
        initial_capital=args.capital,
        risk_pct=args.risk,
    )
