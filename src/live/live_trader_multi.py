"""
Multi-symbol live trader for top 18 S&P 500 stocks + SPX index.

- Monitors 18 symbols simultaneously
- EMA crossover on each symbol independently
- Max N concurrent positions (configurable)
- Risk sizing per symbol
- Bracket orders (entry + TP/SL)

Run:
    python src/live/live_trader_multi.py --symbols MSFT AAPL NVDA --max-positions 5 --check-interval 120
"""
import sys
import time
import math
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.live.alpaca_connector import AlpacaConnector
from src.live.sp500_screener import get_sp500_symbols, get_profitable_8_symbols


class MultiSymbolTrader:
    def __init__(
        self,
        alpaca: AlpacaConnector,
        symbols: List[str],
        max_positions: int = 5,
        fast_ma: int = 10,
        slow_ma: int = 100,
        tp_atr_mult: float = 5.0,
        sl_atr_mult: float = 1.75,
        risk_per_trade: float = 0.008,
        check_interval: int = 60,
    ):
        self.alpaca = alpaca
        self.symbols = symbols
        self.max_positions = max_positions
        self.fast_ma = fast_ma
        self.slow_ma = slow_ma
        self.tp_atr_mult = tp_atr_mult
        self.sl_atr_mult = sl_atr_mult
        self.risk_per_trade = risk_per_trade
        self.check_interval = check_interval

        self.running = False
        # History: {symbol: [{'timestamp': ..., 'price': ...}, ...]}
        self.price_history: Dict[str, List[Dict]] = {s: [] for s in symbols}

        print("Multi-Symbol Trader initialized")
        print(f"  Symbols: {len(symbols)} ({', '.join(symbols[:5])}...)")
        print(f"  Max positions: {max_positions}")
        print(f"  MA: {fast_ma}/{slow_ma}")
        print(f"  Risk: {risk_per_trade*100:.2f}% per trade")

    def start(self):
        print("\n" + "=" * 60)
        print("🤖 MULTI-SYMBOL LIVE TRADER (ALPACA)")
        print("=" * 60)
        print(f"Time: {datetime.now():%Y-%m-%d %H:%M:%S}")

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

        now = datetime.now()

        # Fetch batch quotes
        quotes = self.alpaca.get_batch_quotes(self.symbols)
        
        # Update price history
        for symbol, quote in quotes.items():
            if quote:
                price = self._extract_price(quote)
                if price:
                    self.price_history[symbol].append({"timestamp": now, "price": price})
                    if len(self.price_history[symbol]) > 300:
                        self.price_history[symbol] = self.price_history[symbol][-300:]

        # Check current positions
        open_positions = self.alpaca.get_all_positions()
        open_symbols = {p["symbol"] for p in open_positions}
        
        print(f"\n⏰ {now:%H:%M:%S} | Open positions: {len(open_symbols)}/{self.max_positions}")
        if open_symbols:
            for pos in open_positions:
                pnl = float(pos.get("unrealized_pl", 0))
                print(f"  📊 {pos['symbol']} | Qty: {pos['qty']} | P&L: {pnl:.2f}")

        # Generate signals for all symbols
        signals = self._generate_all_signals()
        
        # Filter: only symbols with strong signal and enough history
        candidates = [
            (symbol, signal) for symbol, signal in signals.items()
            if signal != 0 and symbol not in open_symbols
        ]
        
        if not candidates:
            print("  No new signals")
            return

        # Limit to available slots
        slots_available = self.max_positions - len(open_symbols)
        if slots_available <= 0:
            print(f"  Max positions ({self.max_positions}) reached. No new entries.")
            return

        candidates = candidates[:slots_available]
        print(f"  🎯 New signals: {[(s, sig) for s, sig in candidates]}")

        for symbol, signal in candidates:
            price = self.price_history[symbol][-1]["price"] if self.price_history[symbol] else None
            if price:
                self._execute_signal(symbol, signal, price)

    def _extract_price(self, quote: Dict) -> Optional[float]:
        bid = quote.get("bidprice") or quote.get("bp")
        ask = quote.get("askprice") or quote.get("ap")
        if bid and ask:
            return (float(bid) + float(ask)) / 2
        if ask:
            return float(ask)
        if bid:
            return float(bid)
        return None

    def _generate_all_signals(self) -> Dict[str, int]:
        """Generate signal for each symbol: 1=long, -1=short, 0=neutral."""
        signals = {}
        for symbol in self.symbols:
            history = self.price_history[symbol]
            if len(history) < max(self.slow_ma, 20) + 1:
                signals[symbol] = 0
                continue

            df = pd.DataFrame(history)
            df["Close"] = df["price"]
            ema_fast = df["Close"].ewm(span=self.fast_ma, adjust=False).mean()
            ema_slow = df["Close"].ewm(span=self.slow_ma, adjust=False).mean()

            fast_now, slow_now = ema_fast.iloc[-1], ema_slow.iloc[-1]
            fast_prev, slow_prev = ema_fast.iloc[-2], ema_slow.iloc[-2]

            if fast_prev <= slow_prev and fast_now > slow_now:
                signals[symbol] = 1  # long
            elif fast_prev >= slow_prev and fast_now < slow_now:
                signals[symbol] = -1  # short
            else:
                signals[symbol] = 0
        return signals

    def _execute_signal(self, symbol: str, signal: int, price: float):
        history = self.price_history[symbol]
        df = pd.DataFrame(history)
        df["Close"] = df["price"]
        
        # ATR (simplified: 20-bar high-low range)
        df["high"] = df["Close"]
        df["low"] = df["Close"]
        atr = (df["high"].rolling(20).max() - df["low"].rolling(20).min()).iloc[-1]
        if pd.isna(atr) or atr <= 0:
            atr = price * 0.02

        # Position sizing
        acc = self.alpaca.get_account()
        if not acc:
            return
        equity = float(acc.get("equity", 0))
        risk_dollars = equity * self.risk_per_trade
        stop_distance = atr * self.sl_atr_mult
        qty = math.floor(risk_dollars / stop_distance)
        qty = max(1, qty)

        side = "buy" if signal == 1 else "sell"
        if signal == 1:
            tp_price = price + atr * self.tp_atr_mult
            sl_price = price - stop_distance
        else:
            tp_price = price - atr * self.tp_atr_mult
            sl_price = price + stop_distance

        tp_price = round(tp_price, 2)
        sl_price = round(sl_price, 2)

        print(f"  🚀 {symbol} | {side.upper()} {qty} @ {price:.2f} | TP: {tp_price} | SL: {sl_price}")
        order = self.alpaca.submit_bracket_order(
            symbol=symbol,
            qty=qty,
            side=side,
            take_profit=tp_price,
            stop_loss=sl_price,
        )
        if order:
            print(f"  ✅ Order submitted: {order.get('id')}")
        else:
            print(f"  ❌ Order failed for {symbol}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Multi-Symbol Live Trader")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=None,
        help="List of symbols (default: top 18 S&P 500 + SPX)",
    )
    parser.add_argument("--max-positions", type=int, default=5, help="Max concurrent positions")
    parser.add_argument("--check-interval", type=int, default=120, help="Seconds between checks")
    parser.add_argument("--fast", type=int, default=10, help="Fast EMA period")
    parser.add_argument("--slow", type=int, default=100, help="Slow EMA period")
    parser.add_argument("--auto-start", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    # Use provided symbols, default to top 8 profitable symbols
    symbols = args.symbols if args.symbols else get_profitable_8_symbols()
    symbols = [s for s in symbols if s != "SPX"]  # exclude index from trading
    
    print(f"Trading {len(symbols)} symbols: {', '.join(symbols)}")

    if not args.auto_start:
    print(f"⚠️  This will trade 8 profitable symbols on Alpaca paper account.")
        resp = input("Type START to continue: ")
        if resp.strip().upper() != "START":
            print("Aborted.")
            sys.exit(0)

    connector = AlpacaConnector.from_config().connect()
    trader = MultiSymbolTrader(
        alpaca=connector,
        symbols=symbols,
        max_positions=args.max_positions,
        fast_ma=args.fast,
        slow_ma=args.slow,
        check_interval=args.check_interval,
    )
    trader.start()
