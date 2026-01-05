"""
Live trading bot using Alpaca paper/live API.

- Uses simple EMA crossover (fast/slow) on latest quotes.
- Places market bracket orders (entry + TP/SL).
- Position sizing: risk_per_trade fraction of equity / stop distance.

Run (paper):
    python src/live/live_trader_alpaca.py --symbol SPY --check-interval 60

Requires valid keys in config/alpaca_config.json or env vars.
"""
import sys
import time
import math
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional

# Project root on path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.live.alpaca_connector import AlpacaConnector


class LiveTraderAlpaca:
    def __init__(
        self,
        alpaca: AlpacaConnector,
        symbol: str = "SPY",
        fast_ma: int = 10,
        slow_ma: int = 100,
        tp_atr_mult: float = 5.0,
        sl_atr_mult: float = 1.75,
        risk_per_trade: float = 0.008,
        check_interval: int = 60,
    ):
        self.alpaca = alpaca
        self.symbol = symbol
        self.fast_ma = fast_ma
        self.slow_ma = slow_ma
        self.tp_atr_mult = tp_atr_mult
        self.sl_atr_mult = sl_atr_mult
        self.risk_per_trade = risk_per_trade
        self.check_interval = check_interval

        self.running = False
        self.current_side: Optional[str] = None  # 'buy' or 'sell'

        self.price_history = []  # list of {timestamp, price}

        print("LiveTraderAlpaca initialized")
        print(f"  Symbol: {symbol}")
        print(f"  MA: {fast_ma}/{slow_ma}")
        print(f"  TP: {tp_atr_mult}×ATR, SL: {sl_atr_mult}×ATR")
        print(f"  Risk: {risk_per_trade*100:.2f}% per trade")

    def start(self):
        print("\n" + "=" * 60)
        print("🤖 LIVE TRADING BOT (ALPACA)")
        print("=" * 60)
        print(f"Time: {datetime.now():%Y-%m-%d %H:%M:%S}")
        print(f"Symbol: {self.symbol}")

        # Account info
        acc = self.alpaca.get_account()
        if acc:
            print(f"💰 Equity: {acc.get('equity')}")
            print(f"   Cash: {acc.get('cash')}")

        self.running = True
        try:
            while self.running:
                self._trading_cycle()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            print("\n⚠️  Interrupted by user")
        finally:
            self.stop()

    def stop(self):
        self.running = False
        print("\n🛑 Bot stopped")

    def _trading_cycle(self):
        # Check market clock
        clock = self.alpaca.get_clock()
        if clock and not clock.get("is_open", False):
            print(f"⏸️  Market closed. Next open: {clock.get('next_open')}")
            return

        price = self._get_last_price()
        if price is None:
            print("⚠️  No price available")
            return

        now = datetime.now()
        self.price_history.append({"timestamp": now, "price": price})
        if len(self.price_history) > 300:
            self.price_history = self.price_history[-300:]

        if len(self.price_history) < max(self.slow_ma, 20) + 1:
            print(f"⏳ Building history ({len(self.price_history)} bars)...")
            return

        signal = self._generate_signal()
        print(f"⏰ {now:%H:%M:%S} | Price {price:.2f} | Signal {signal}")

        # If a position exists, skip new entry (simple 1-position bot)
        pos = self.alpaca.get_position(self.symbol)
        if pos:
            unrealized = float(pos.get("unrealized_pl", 0))
            print(f"📊 Position open | Qty: {pos.get('qty')} | Side: {pos.get('side')} | P&L: {unrealized:.2f}")
            return

        if signal == 0:
            return

        self._execute_signal(signal, price)

    def _get_last_price(self) -> Optional[float]:
        quote = self.alpaca.get_last_quote(self.symbol)
        if not quote:
            return None
        bid = quote.get("bidprice") or quote.get("bp")
        ask = quote.get("askprice") or quote.get("ap")
        if bid and ask:
            return (float(bid) + float(ask)) / 2
        if ask:
            return float(ask)
        if bid:
            return float(bid)
        return None

    def _generate_signal(self) -> int:
        df = pd.DataFrame(self.price_history)
        df["Close"] = df["price"]
        ema_fast = df["Close"].ewm(span=self.fast_ma, adjust=False).mean()
        ema_slow = df["Close"].ewm(span=self.slow_ma, adjust=False).mean()

        fast_now, slow_now = ema_fast.iloc[-1], ema_slow.iloc[-1]
        fast_prev, slow_prev = ema_fast.iloc[-2], ema_slow.iloc[-2]

        if fast_prev <= slow_prev and fast_now > slow_now:
            return 1  # long
        if fast_prev >= slow_prev and fast_now < slow_now:
            return -1  # short
        return 0

    def _calculate_atr(self) -> float:
        if len(self.price_history) < 20:
            return 0.0
        df = pd.DataFrame(self.price_history)
        df["returns"] = df["price"].pct_change().abs()
        atr = df["returns"].rolling(14).mean().iloc[-1] * df["price"].iloc[-1]
        return float(atr) if pd.notna(atr) else 0.0

    def _calculate_qty(self, entry: float, stop: float) -> int:
        acc = self.alpaca.get_account()
        if not acc:
            return 0
        equity = float(acc.get("equity", 0))
        risk_amount = equity * self.risk_per_trade
        stop_dist = abs(entry - stop)
        if stop_dist == 0:
            return 0
        qty = math.floor(risk_amount / stop_dist)
        return max(qty, 1)

    def _execute_signal(self, signal: int, entry_price: float):
        atr = self._calculate_atr()
        if atr == 0:
            print("⚠️  ATR unavailable, skipping")
            return

        if signal == 1:
            side = "buy"
            stop = entry_price - atr * self.sl_atr_mult
            tp = entry_price + atr * self.tp_atr_mult
        else:
            side = "sell"
            stop = entry_price + atr * self.sl_atr_mult
            tp = entry_price - atr * self.tp_atr_mult

        qty = self._calculate_qty(entry_price, stop)
        if qty <= 0:
            print("⚠️  Qty calc failed, skipping")
            return

        print(f"🎯 NEW {side.upper()} | Entry {entry_price:.2f} | SL {stop:.2f} | TP {tp:.2f} | Qty {qty}")
        order = self.alpaca.submit_bracket_order(
            symbol=self.symbol,
            qty=qty,
            side=side,
            take_profit=tp,
            stop_loss=stop,
        )
        if order:
            print(f"✅ Order submitted: {order.get('id')}")
        else:
            print("❌ Order submission failed")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Alpaca Live Trader (paper)")
    parser.add_argument("--symbol", default="SPY", help="Symbol to trade")
    parser.add_argument("--check-interval", type=int, default=60, help="Seconds between checks")
    parser.add_argument("--fast", type=int, default=10, help="Fast EMA period")
    parser.add_argument("--slow", type=int, default=100, help="Slow EMA period")
    parser.add_argument("--auto-start", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    if not args.auto_start:
        print("⚠️  This will place paper trades on Alpaca.")
        resp = input("Type START to continue: ")
        if resp.strip().upper() != "START":
            print("Aborted.")
            sys.exit(0)

    connector = AlpacaConnector.from_config().connect()
    trader = LiveTraderAlpaca(
        alpaca=connector,
        symbol=args.symbol,
        fast_ma=args.fast,
        slow_ma=args.slow,
        check_interval=args.check_interval,
    )
    trader.start()
