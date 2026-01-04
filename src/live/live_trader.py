"""
Live Trading Engine

High-level trading logic that:
1. Monitors market data via XTB API
2. Generates signals using strategy
3. Executes trades with risk management
4. Logs all activity
"""
import sys
import time
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.live.xtb_connector import XTBConnector
from src.features.feature_engine import build_features


class LiveTrader:
    """Live trading bot for XTB."""
    
    def __init__(self,
                 xtb: XTBConnector,
                 symbol: str = "US500",
                 fast_ma: int = 20,
                 slow_ma: int = 50,
                 tp_atr_mult: float = 3.5,
                 sl_atr_mult: float = 1.0,
                 risk_per_trade: float = 0.005,
                 check_interval: int = 60):
        """
        Initialize live trader.
        
        Args:
            xtb: XTB connector instance
            symbol: Trading symbol (default: US500 = S&P 500)
            fast_ma: Fast EMA period
            slow_ma: Slow EMA period
            tp_atr_mult: Take profit ATR multiplier
            sl_atr_mult: Stop loss ATR multiplier
            risk_per_trade: Risk per trade as fraction of capital
            check_interval: Seconds between signal checks
        """
        self.xtb = xtb
        self.symbol = symbol
        self.fast_ma = fast_ma
        self.slow_ma = slow_ma
        self.tp_atr_mult = tp_atr_mult
        self.sl_atr_mult = sl_atr_mult
        self.risk_per_trade = risk_per_trade
        self.check_interval = check_interval
        
        # State
        self.running = False
        self.current_position = None  # None, 'long', or 'short'
        self.current_order_id = None
        
        # Price history for indicators
        self.price_history = []
        
        print(f"LiveTrader initialized:")
        print(f"  Symbol: {symbol}")
        print(f"  MA: {fast_ma}/{slow_ma}")
        print(f"  TP: {tp_atr_mult}×ATR, SL: {sl_atr_mult}×ATR")
        print(f"  Risk: {risk_per_trade*100:.2f}% per trade")
    
    def start(self):
        """Start live trading loop."""
        print("\n" + "="*60)
        print("🤖 LIVE TRADING BOT STARTED")
        print("="*60)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Mode: {self.xtb.mode.upper()}")
        print()
        
        if not self.xtb.connected:
            print("❌ Not connected to XTB API")
            return
        
        # Get initial account info
        acc_info = self.xtb.get_account_info()
        if acc_info:
            print(f"💰 Account Balance: {acc_info['balance']} {acc_info['currency']}")
            print(f"   Equity: {acc_info['equity']}")
            print(f"   Free Margin: {acc_info['margin_free']}")
        
        self.running = True
        
        try:
            while self.running:
                self._trading_cycle()
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            print("\n⚠️  Interrupted by user")
        except Exception as e:
            print(f"\n❌ Error in trading loop: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stop()
    
    def stop(self):
        """Stop trading bot."""
        print("\n" + "="*60)
        print("🛑 STOPPING LIVE TRADING BOT")
        print("="*60)
        
        self.running = False
        
        # Close any open positions
        if self.current_order_id:
            print(f"Closing open position (Order #{self.current_order_id})...")
            trades = self.xtb.get_open_trades()
            for trade in trades:
                if trade['order'] == self.current_order_id:
                    self.xtb.close_trade(trade['order'], trade['volume'])
                    break
        
        print("Bot stopped.")
    
    def _trading_cycle(self):
        """Single trading cycle: check signal, manage position."""
        try:
            # Update price data
            current_price = self.xtb.get_current_price(self.symbol)
            if not current_price:
                print("⚠️  Could not get current price")
                return
            
            timestamp = datetime.now()
            self.price_history.append({
                'timestamp': timestamp,
                'price': current_price
            })
            
            # Keep only last N bars for indicators
            if len(self.price_history) > 200:
                self.price_history = self.price_history[-200:]
            
            # Need enough history for indicators
            if len(self.price_history) < max(self.slow_ma, 20) + 1:
                print(f"⏳ Building price history... ({len(self.price_history)}/{max(self.slow_ma, 20)+1})")
                return
            
            # Generate signal
            signal = self._generate_signal()
            
            # Log status
            print(f"\n⏰ {timestamp.strftime('%H:%M:%S')} | Price: {current_price:.2f} | Signal: {signal}")
            
            # Check existing position
            if self.current_order_id:
                self._check_existing_position()
            
            # Execute new signal if no position
            if signal != 0 and not self.current_position:
                self._execute_signal(signal, current_price)
                
        except Exception as e:
            print(f"❌ Error in trading cycle: {e}")
    
    def _generate_signal(self) -> int:
        """
        Generate trading signal based on MA crossover.
        
        Returns:
            1 for LONG, -1 for SHORT, 0 for no signal
        """
        # Convert price history to DataFrame
        df = pd.DataFrame(self.price_history)
        df['Close'] = df['price']
        
        # Calculate EMAs
        ema_fast = df['Close'].ewm(span=self.fast_ma, adjust=False).mean()
        ema_slow = df['Close'].ewm(span=self.slow_ma, adjust=False).mean()
        
        # Current values
        fast_now = ema_fast.iloc[-1]
        slow_now = ema_slow.iloc[-1]
        
        # Previous values
        fast_prev = ema_fast.iloc[-2]
        slow_prev = ema_slow.iloc[-2]
        
        # Crossover detection
        if fast_prev <= slow_prev and fast_now > slow_now:
            return 1  # Bullish crossover - LONG
        elif fast_prev >= slow_prev and fast_now < slow_now:
            return -1  # Bearish crossover - SHORT
        
        return 0  # No signal
    
    def _calculate_position_size(self, entry_price: float, stop_price: float) -> float:
        """
        Calculate position size based on risk management.
        
        Args:
            entry_price: Entry price
            stop_price: Stop loss price
            
        Returns:
            Volume in lots
        """
        acc_info = self.xtb.get_account_info()
        if not acc_info:
            return 0.01  # Minimum size
        
        balance = acc_info['balance']
        risk_amount = balance * self.risk_per_trade
        
        # Risk per point
        stop_distance = abs(entry_price - stop_price)
        if stop_distance == 0:
            return 0.01
        
        # XTB US500: 1 lot = $1 per point
        # Volume = risk_amount / stop_distance
        volume = risk_amount / stop_distance
        
        # Round to 2 decimals (min 0.01)
        volume = max(0.01, round(volume, 2))
        
        # Cap at reasonable size (max 1.0 lot for demo)
        volume = min(volume, 1.0)
        
        return volume
    
    def _calculate_atr(self) -> float:
        """Calculate current ATR."""
        if len(self.price_history) < 20:
            return 0
        
        df = pd.DataFrame(self.price_history)
        
        # Simple ATR approximation from price range
        # (In real implementation, would need OHLC data)
        df['returns'] = df['price'].pct_change().abs()
        atr = df['returns'].rolling(14).mean().iloc[-1] * df['price'].iloc[-1]
        
        return atr if not pd.isna(atr) else 0
    
    def _execute_signal(self, signal: int, entry_price: float):
        """
        Execute trading signal.
        
        Args:
            signal: 1 for LONG, -1 for SHORT
            entry_price: Current price
        """
        print(f"\n🎯 NEW SIGNAL: {'LONG' if signal == 1 else 'SHORT'}")
        
        # Calculate ATR for stops
        atr = self._calculate_atr()
        if atr == 0:
            print("⚠️  Cannot calculate ATR, skipping trade")
            return
        
        # Calculate SL/TP
        if signal == 1:  # LONG
            stop_loss = entry_price - (atr * self.sl_atr_mult)
            take_profit = entry_price + (atr * self.tp_atr_mult)
            cmd_type = 0  # BUY
        else:  # SHORT
            stop_loss = entry_price + (atr * self.sl_atr_mult)
            take_profit = entry_price - (atr * self.tp_atr_mult)
            cmd_type = 1  # SELL
        
        # Calculate position size
        volume = self._calculate_position_size(entry_price, stop_loss)
        
        print(f"  Entry: {entry_price:.2f}")
        print(f"  SL: {stop_loss:.2f} (ATR: {atr:.2f})")
        print(f"  TP: {take_profit:.2f}")
        print(f"  Volume: {volume} lots")
        
        # Execute trade
        order_id = self.xtb.open_trade(
            symbol=self.symbol,
            cmd_type=cmd_type,
            volume=volume,
            sl=stop_loss,
            tp=take_profit,
            comment=f"Bot-{self.fast_ma}/{self.slow_ma}"
        )
        
        if order_id:
            self.current_order_id = order_id
            self.current_position = 'long' if signal == 1 else 'short'
            print(f"✅ Trade opened: Order #{order_id}")
        else:
            print("❌ Trade execution failed")
    
    def _check_existing_position(self):
        """Check status of existing position."""
        trades = self.xtb.get_open_trades()
        
        # Check if our order is still open
        order_found = False
        for trade in trades:
            if trade['order'] == self.current_order_id:
                order_found = True
                profit = trade.get('profit', 0)
                print(f"  📊 Position: Order #{trade['order']} | P&L: {profit:.2f}")
                break
        
        # Position was closed (SL/TP hit)
        if not order_found and self.current_order_id:
            print(f"  ✓ Position closed: Order #{self.current_order_id}")
            self.current_order_id = None
            self.current_position = None


# Quick test
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Live Trading Bot for XTB')
    parser.add_argument('--user', required=True, help='XTB login')
    parser.add_argument('--password', required=True, help='XTB password')
    parser.add_argument('--mode', default='demo', choices=['demo', 'real'], help='Trading mode')
    parser.add_argument('--symbol', default='US500', help='Trading symbol')
    parser.add_argument('--check-interval', type=int, default=60, help='Seconds between checks')
    
    args = parser.parse_args()
    
    print("🤖 Live Trading Bot")
    print("="*60)
    print("⚠️  WARNING: This bot will execute real trades!")
    print(f"   Mode: {args.mode.upper()}")
    print(f"   Symbol: {args.symbol}")
    print()
    
    response = input("Type 'START' to begin trading: ")
    if response.upper() != 'START':
        print("Aborted.")
        exit(0)
    
    # Connect to XTB
    with XTBConnector(args.user, args.password, mode=args.mode) as xtb:
        if not xtb.connected:
            print("❌ Failed to connect to XTB")
            exit(1)
        
        # Create trader
        trader = LiveTrader(
            xtb=xtb,
            symbol=args.symbol,
            check_interval=args.check_interval
        )
        
        # Start trading
        trader.start()
