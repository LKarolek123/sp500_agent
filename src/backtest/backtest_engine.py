"""
Backtest Engine for 3EMA + BX Trender Strategy
Tests strategy on historical S&P 500 data
"""

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json
from pathlib import Path

from src.strategy.strategy_engine import StrategyEngine, SignalType, Trade


class BacktestEngine:
    """Main backtester - simulates strategy on historical data"""
    
    def __init__(
        self,
        strategy_engine: StrategyEngine,
        initial_capital: float = 10000,
        commission: float = 0.001,  # 0.1% per trade
        slippage: float = 0.0005     # 0.05%
    ):
        self.strategy = strategy_engine
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        
        self.equity_curve = []
        self.trades_executed: List[Trade] = []
        self.signals_generated: List[Dict] = []
    
    def run_backtest(
        self,
        df: pd.DataFrame,
        symbol: str
    ) -> Dict:
        """
        Run complete backtest on historical data
        
        Args:
            df: DataFrame with OHLCV data, must have columns: open, high, low, close, volume
            symbol: stock symbol for logging
        
        Returns:
            Dictionary with backtest results
        """
        
        print(f"\n{'='*60}")
        print(f"BACKTEST: {symbol}")
        print(f"{'='*60}")
        print(f"Data points: {len(df)}")
        print(f"Date range: {df.index[0]} to {df.index[-1]}")
        
        # Initialize
        current_equity = self.initial_capital
        open_trades: Dict[str, Trade] = {}  # key: "LONG" or "SHORT"
        
        # Walk through each candle
        for idx in range(200, len(df)):  # Start after enough data for EMAs
            timestamp = df.index[idx]
            current_price = df['close'].iloc[idx]
            
            # Check if open trade should be closed
            if open_trades:
                for position_type, trade in list(open_trades.items()):
                    # Check for stop loss
                    if position_type == "LONG":
                        if current_price <= trade.stop_loss:
                            # SL hit
                            self._close_trade(
                                trade,
                                current_price,
                                timestamp,
                                "STOP_LOSS",
                                open_trades
                            )
                            current_equity += trade.pnl - (trade.pnl * self.commission)
                            print(f"  [{timestamp}] LONG SL: {trade.entry_price:.2f} -> {current_price:.2f} | "
                                  f"PnL: ${trade.pnl:.2f} | Equity: ${current_equity:.2f}")
                        else:
                            # Try to exit on opposite signal
                            signal = self.strategy.generate_signal(df, idx, current_equity)
                            should_exit, reason = self.strategy.check_exit_signal(trade, signal)
                            
                            if should_exit and trade.pnl > 0:  # Only exit if profitable
                                self._close_trade(
                                    trade,
                                    current_price,
                                    timestamp,
                                    reason,
                                    open_trades
                                )
                                current_equity += trade.pnl - (trade.pnl * self.commission)
                                print(f"  [{timestamp}] LONG TP: {trade.entry_price:.2f} -> {current_price:.2f} | "
                                      f"PnL: ${trade.pnl:.2f} | Equity: ${current_equity:.2f}")
                    
                    elif position_type == "SHORT":
                        if current_price >= trade.stop_loss:
                            # SL hit
                            self._close_trade(
                                trade,
                                current_price,
                                timestamp,
                                "STOP_LOSS",
                                open_trades
                            )
                            current_equity += trade.pnl - (abs(trade.pnl) * self.commission)
                            print(f"  [{timestamp}] SHORT SL: {trade.entry_price:.2f} -> {current_price:.2f} | "
                                  f"PnL: ${trade.pnl:.2f} | Equity: ${current_equity:.2f}")
                        else:
                            # Try to exit on opposite signal
                            signal = self.strategy.generate_signal(df, idx, current_equity)
                            should_exit, reason = self.strategy.check_exit_signal(trade, signal)
                            
                            if should_exit and trade.pnl > 0:  # Only exit if profitable
                                self._close_trade(
                                    trade,
                                    current_price,
                                    timestamp,
                                    reason,
                                    open_trades
                                )
                                current_equity += trade.pnl - (abs(trade.pnl) * self.commission)
                                print(f"  [{timestamp}] SHORT TP: {trade.entry_price:.2f} -> {current_price:.2f} | "
                                      f"PnL: ${trade.pnl:.2f} | Equity: ${current_equity:.2f}")
            
            # Check for new entry signal
            signal = self.strategy.generate_signal(df, idx, current_equity)
            
            if signal and not open_trades:  # Only enter if no open positions
                if signal.signal_type == SignalType.LONG:
                    trade = Trade(
                        entry_signal=signal,
                        entry_price=current_price,
                        entry_time=timestamp,
                        position_type=SignalType.LONG,
                        stop_loss=signal.ema_89 * 0.99,  # 1% below EMA89
                        risk_amount=self.initial_capital * 0.015,
                        position_size=100  # Simplified
                    )
                    open_trades["LONG"] = trade
                    self.signals_generated.append({
                        "timestamp": timestamp,
                        "symbol": symbol,
                        "signal": "LONG",
                        "price": current_price,
                        "ema_21": signal.ema_21,
                        "ema_89": signal.ema_89,
                        "ema_200": signal.ema_200
                    })
                    print(f"  [{timestamp}] LONG ENTRY: {current_price:.2f} | EMA: {signal.ema_21:.2f}/{signal.ema_89:.2f}/{signal.ema_200:.2f}")
                
                elif signal.signal_type == SignalType.SHORT:
                    trade = Trade(
                        entry_signal=signal,
                        entry_price=current_price,
                        entry_time=timestamp,
                        position_type=SignalType.SHORT,
                        stop_loss=signal.ema_89 * 1.01,  # 1% above EMA89
                        risk_amount=self.initial_capital * 0.015,
                        position_size=100  # Simplified
                    )
                    open_trades["SHORT"] = trade
                    self.signals_generated.append({
                        "timestamp": timestamp,
                        "symbol": symbol,
                        "signal": "SHORT",
                        "price": current_price,
                        "ema_21": signal.ema_21,
                        "ema_89": signal.ema_89,
                        "ema_200": signal.ema_200
                    })
                    print(f"  [{timestamp}] SHORT ENTRY: {current_price:.2f} | EMA: {signal.ema_21:.2f}/{signal.ema_89:.2f}/{signal.ema_200:.2f}")
            
            self.equity_curve.append({
                "timestamp": timestamp,
                "equity": current_equity,
                "price": current_price
            })
        
        # Close any remaining open trades at last price
        last_price = df['close'].iloc[-1]
        last_timestamp = df.index[-1]
        
        for position_type, trade in list(open_trades.items()):
            self._close_trade(
                trade,
                last_price,
                last_timestamp,
                "BACKTEST_END",
                open_trades
            )
            current_equity += trade.pnl
        
        # Calculate metrics
        metrics = self._calculate_metrics(current_equity, df)
        
        return {
            "symbol": symbol,
            "metrics": metrics,
            "trades": [self._trade_to_dict(t) for t in self.trades_executed],
            "signals": self.signals_generated,
            "equity_curve": self.equity_curve
        }
    
    def _close_trade(
        self,
        trade: Trade,
        exit_price: float,
        exit_time: pd.Timestamp,
        exit_reason: str,
        open_trades: Dict
    ):
        """Close a trade"""
        trade.exit_price = exit_price
        trade.exit_time = exit_time
        trade.exit_reason = exit_reason
        
        self.trades_executed.append(trade)
        
        # Remove from open trades
        key = "LONG" if trade.position_type == SignalType.LONG else "SHORT"
        if key in open_trades:
            del open_trades[key]
    
    def _calculate_metrics(self, final_equity: float, df: pd.DataFrame) -> Dict:
        """Calculate backtest metrics"""
        
        if not self.trades_executed:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "total_profit": 0,
                "cagr": 0,
                "sharpe_ratio": 0,
                "max_drawdown": 0
            }
        
        # Basic metrics
        total_trades = len(self.trades_executed)
        winning_trades = sum(1 for t in self.trades_executed if t.pnl > 0)
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_profit = final_equity - self.initial_capital
        profit_percent = (total_profit / self.initial_capital) * 100
        
        # CAGR
        days = (df.index[-1] - df.index[0]).days
        years = days / 365.0
        cagr = (((final_equity / self.initial_capital) ** (1 / years)) - 1) * 100 if years > 0 else 0
        
        # Sharpe Ratio (simplified)
        returns = np.diff([e["equity"] for e in self.equity_curve])
        returns_pct = returns / self.initial_capital * 100
        
        if len(returns_pct) > 0 and np.std(returns_pct) > 0:
            sharpe = (np.mean(returns_pct) / np.std(returns_pct)) * np.sqrt(252)
        else:
            sharpe = 0
        
        # Max Drawdown
        equity_vals = [e["equity"] for e in self.equity_curve]
        cummax = np.maximum.accumulate(equity_vals)
        drawdown = (np.array(equity_vals) - cummax) / cummax * 100
        max_drawdown = abs(np.min(drawdown)) if len(drawdown) > 0 else 0
        
        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 2),
            "total_profit": round(total_profit, 2),
            "profit_percent": round(profit_percent, 2),
            "cagr": round(cagr, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown": round(max_drawdown, 2),
            "final_equity": round(final_equity, 2)
        }
    
    def _trade_to_dict(self, trade: Trade) -> Dict:
        """Convert trade to dictionary"""
        return {
            "entry_price": trade.entry_price,
            "entry_time": str(trade.entry_time),
            "exit_price": trade.exit_price,
            "exit_time": str(trade.exit_time) if trade.exit_time else None,
            "position_type": trade.position_type.value,
            "pnl": round(trade.pnl, 2),
            "pnl_percent": round(trade.pnl_percent, 2),
            "exit_reason": trade.exit_reason
        }


class DataLoader:
    """Load historical data from yfinance"""
    
    @staticmethod
    def load_data(
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1h"
    ) -> pd.DataFrame:
        """
        Load historical OHLCV data
        
        Args:
            symbol: stock symbol (e.g., 'TSLA')
            start_date: start date (YYYY-MM-DD)
            end_date: end date (YYYY-MM-DD)
            interval: '1h' for hourly, '1d' for daily, etc.
        
        Returns:
            DataFrame with columns: open, high, low, close, volume
        """
        
        print(f"Loading {symbol} data from {start_date} to {end_date}...")
        
        df = yf.download(symbol, start=start_date, end=end_date, interval=interval, progress=False)
        
        # Ensure columns are lowercase
        df.columns = [col.lower() for col in df.columns]
        
        # Rename adjusted close to close if it exists
        if 'adj close' in df.columns:
            df.rename(columns={'adj close': 'close'}, inplace=True)
        
        # Remove NaN values
        df = df.dropna()
        
        print(f"Loaded {len(df)} candles")
        
        return df


if __name__ == "__main__":
    # Example usage
    print("Loading data and running backtest...")
    
    # Load data
    loader = DataLoader()
    df = loader.load_data("TSLA", "2024-01-01", "2025-12-31", interval="1h")
    
    # Create strategy and backtester
    strategy = StrategyEngine()
    backtester = BacktestEngine(strategy)
    
    # Run backtest
    results = backtester.run_backtest(df, "TSLA")
    
    # Print results
    print("\n" + "="*60)
    print("BACKTEST RESULTS")
    print("="*60)
    for key, value in results["metrics"].items():
        print(f"{key}: {value}")
