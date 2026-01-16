"""
Multi-Stock Backtest Runner for 3EMA + BX Trender
Tests strategy on 8 S&P 500 stocks
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import numpy as np
from typing import Dict

from src.strategy.strategy_engine import StrategyEngine
from src.backtest.backtest_engine import BacktestEngine, DataLoader


class MultiStockBacktester:
    """Run backtest across multiple stocks and aggregate results"""
    
    def __init__(self):
        self.results = {}
        self.all_trades = []
        self.aggregate_metrics = {}
    
    def run_all_stocks(
        self,
        symbols: list,
        start_date: str,
        end_date: str,
        interval: str = "1h",
        save_results: bool = True
    ) -> Dict:
        """
        Run backtest on multiple stocks
        
        Args:
            symbols: list of stock symbols
            start_date: backtest start date
            end_date: backtest end date
            interval: timeframe (1h, 1d, etc)
            save_results: save to JSON file
        
        Returns:
            Dictionary with aggregated results
        """
        
        print(f"\n{'='*80}")
        print(f"MULTI-STOCK BACKTEST")
        print(f"Symbols: {', '.join(symbols)}")
        print(f"Period: {start_date} to {end_date}")
        print(f"Timeframe: {interval}")
        print(f"{'='*80}\n")
        
        loader = DataLoader()
        
        for symbol in symbols:
            try:
                # Load data
                df = loader.load_data(symbol, start_date, end_date, interval=interval)
                
                if len(df) < 500:
                    print(f"⚠️  {symbol}: Not enough data ({len(df)} candles)")
                    continue
                
                # Run backtest
                strategy = StrategyEngine()
                backtester = BacktestEngine()
                result = backtester.run_backtest(df, symbol)
                
                self.results[symbol] = result
                self.all_trades.extend(result["trades"])
                
                # Print summary
                m = result["metrics"]
                print(f"\n✅ {symbol} Summary:")
                print(f"   Trades: {m['total_trades']} (W: {m['winning_trades']} | L: {m['losing_trades']})")
                print(f"   Win Rate: {m['win_rate']}%")
                print(f"   Profit: ${m['total_profit']:.2f} ({m['profit_percent']:.2f}%)")
                print(f"   CAGR: {m['cagr']:.2f}%")
                print(f"   Sharpe: {m['sharpe_ratio']:.2f}")
                print(f"   Max DD: {m['max_drawdown']:.2f}%")
                
            except Exception as e:
                print(f"❌ {symbol}: Error - {str(e)}")
                continue
        
        # Aggregate metrics
        self.aggregate_metrics = self._aggregate_results()
        
        if save_results:
            self._save_results()
        
        return self.aggregate_metrics
    
    def _aggregate_results(self) -> Dict:
        """Calculate aggregate metrics across all stocks"""
        
        if not self.results:
            return {}
        
        all_win_rates = [r["metrics"]["win_rate"] for r in self.results.values()]
        all_profits = [r["metrics"]["profit_percent"] for r in self.results.values()]
        all_cagrs = [r["metrics"]["cagr"] for r in self.results.values()]
        all_sharpes = [r["metrics"]["sharpe_ratio"] for r in self.results.values()]
        all_dd = [r["metrics"]["max_drawdown"] for r in self.results.values()]
        
        return {
            "backtest_date": datetime.now().isoformat(),
            "num_stocks": len(self.results),
            "total_trades": len(self.all_trades),
            "avg_win_rate": round(np.mean(all_win_rates), 2),
            "avg_profit_percent": round(np.mean(all_profits), 2),
            "avg_cagr": round(np.mean(all_cagrs), 2),
            "avg_sharpe": round(np.mean(all_sharpes), 2),
            "avg_max_drawdown": round(np.mean(all_dd), 2),
            "all_profitable": all(p > 0 for p in all_profits),
            "profitable_stocks": sum(1 for p in all_profits if p > 0),
            "individual_results": {
                symbol: result["metrics"] 
                for symbol, result in self.results.items()
            }
        }
    
    def _save_results(self):
        """Save results to JSON file"""
        
        output_dir = Path("results")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = output_dir / f"backtest_3ema_btrender_{timestamp}.json"
        
        # Prepare data for JSON serialization
        data = {
            "metadata": {
                "strategy": "3EMA + BX Trender",
                "timestamp": datetime.now().isoformat(),
                "num_stocks": len(self.results)
            },
            "aggregate": self.aggregate_metrics,
            "individual_stocks": {
                symbol: {
                    "metrics": result["metrics"],
                    "num_trades": len(result["trades"]),
                    "sample_trades": result["trades"][:5]  # Save first 5 trades as sample
                }
                for symbol, result in self.results.items()
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"\n✅ Results saved to {filename}")
        
        # Also save CSV with trades
        trades_df = pd.DataFrame(self.all_trades)
        trades_file = output_dir / f"backtest_trades_3ema_btrender_{timestamp}.csv"
        trades_df.to_csv(trades_file, index=False)
        
        print(f"✅ Trades saved to {trades_file}")
    
    def print_summary(self):
        """Print summary of backtest results"""
        
        if not self.aggregate_metrics:
            print("No results to display")
            return
        
        print(f"\n{'='*80}")
        print(f"BACKTEST SUMMARY - 3EMA + BX Trender Strategy")
        print(f"{'='*80}")
        
        agg = self.aggregate_metrics
        
        print(f"\nAggregate Metrics ({agg['num_stocks']} stocks):")
        print(f"  Total Trades: {agg['total_trades']}")
        print(f"  Average Win Rate: {agg['avg_win_rate']}%")
        print(f"  Average Profit: {agg['avg_profit_percent']:.2f}%")
        print(f"  Average CAGR: {agg['avg_cagr']:.2f}%")
        print(f"  Average Sharpe Ratio: {agg['avg_sharpe']:.2f}")
        print(f"  Average Max Drawdown: {agg['avg_max_drawdown']:.2f}%")
        print(f"  Profitable Stocks: {agg['profitable_stocks']}/{agg['num_stocks']}")
        
        print(f"\nPer-Stock Results:")
        for symbol, metrics in agg['individual_results'].items():
            status = "✅" if metrics['profit_percent'] > 0 else "❌"
            print(f"  {status} {symbol}: {metrics['win_rate']:.1f}% | ${metrics['total_profit']:.2f} | {metrics['profit_percent']:.2f}%")
        
        print(f"\n{'='*80}")


def main():
    """Main entry point"""
    
    # Configuration
    SYMBOLS = ["TSLA", "AMZN", "META", "GOOGL", "JNJ", "JPM", "DIS", "LLY"]
    START_DATE = "2024-01-01"
    END_DATE = "2025-12-31"
    TIMEFRAME = "1h"  # hourly
    
    # Run backtest
    backtester = MultiStockBacktester()
    results = backtester.run_all_stocks(
        symbols=SYMBOLS,
        start_date=START_DATE,
        end_date=END_DATE,
        interval=TIMEFRAME,
        save_results=True
    )
    
    # Print summary
    backtester.print_summary()


if __name__ == "__main__":
    main()
