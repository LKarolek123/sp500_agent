"""
Alpaca API Connector

- Reads API keys from config/alpaca_config.json (gitignored) or environment variables
- Provides account info, positions, quotes, and basic order placement

Requirements:
    pip install alpaca-trade-api
Docs:
    https://alpaca.markets/docs/
"""
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any

import alpaca_trade_api as tradeapi


def load_alpaca_config() -> Dict[str, Any]:
    """Load Alpaca credentials from config/alpaca_config.json or environment variables."""
    config_path = Path(__file__).parent.parent.parent / "config" / "alpaca_config.json"
    cfg = {
        "api_key": os.getenv("ALPACA_API_KEY", ""),
        "secret_key": os.getenv("ALPACA_SECRET_KEY", ""),
        "base_url": os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets"),
    }

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                file_cfg = json.load(f).get("alpaca", {})
                cfg["api_key"] = file_cfg.get("api_key", cfg["api_key"])
                cfg["secret_key"] = file_cfg.get("secret_key", cfg["secret_key"])
                cfg["base_url"] = file_cfg.get("base_url", cfg["base_url"])
        except Exception as e:
            print(f"Warning: could not read alpaca_config.json: {e}")
    return cfg


class AlpacaConnector:
    """Thin wrapper around alpaca-trade-api REST client."""

    def __init__(self, api_key: str, secret_key: str, base_url: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url
        self.api: Optional[tradeapi.REST] = None

    @classmethod
    def from_config(cls) -> "AlpacaConnector":
        cfg = load_alpaca_config()
        missing = [k for k in ["api_key", "secret_key"] if not cfg.get(k)]
        if missing:
            raise ValueError(f"Missing Alpaca credentials: {', '.join(missing)}")
        return cls(cfg["api_key"], cfg["secret_key"], cfg["base_url"])

    def connect(self):
        self.api = tradeapi.REST(
            key_id=self.api_key,
            secret_key=self.secret_key,
            base_url=self.base_url,
            api_version="v2",
        )
        return self

    def get_account(self) -> Optional[Dict[str, Any]]:
        try:
            acc = self.api.get_account()
            return acc._raw
        except Exception as e:
            print(f"Error getting account: {e}")
            return None

    def get_positions(self):
        try:
            return [p._raw for p in self.api.list_positions()]
        except Exception as e:
            print(f"Error getting positions: {e}")
            return []

    def get_clock(self) -> Optional[Dict[str, Any]]:
        try:
            return self.api.get_clock()._raw
        except Exception as e:
            print(f"Error getting market clock: {e}")
            return None

    def get_last_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch last/ latest quote. Uses get_latest_quote (v2) and falls back if needed."""
        try:
            if hasattr(self.api, "get_latest_quote"):
                quote = self.api.get_latest_quote(symbol)
            else:
                quote = self.api.get_last_quote(symbol)  # older clients
            return getattr(quote, "_raw", quote)
        except Exception as e:
            print(f"Error getting quote for {symbol}: {e}")
            return None

    def submit_market_order(self, symbol: str, qty: float, side: str, time_in_force: str = "day") -> Optional[Dict[str, Any]]:
        try:
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type="market",
                time_in_force=time_in_force,
            )
            return order._raw
        except Exception as e:
            print(f"Error submitting order: {e}")
            return None

    def submit_bracket_order(self,
                              symbol: str,
                              qty: float,
                              side: str,
                              take_profit: float,
                              stop_loss: float,
                              time_in_force: str = "day") -> Optional[Dict[str, Any]]:
        """Submit a market bracket order (entry + TP/SL)."""
        try:
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type="market",
                time_in_force=time_in_force,
                order_class="bracket",
                take_profit={"limit_price": take_profit},
                stop_loss={"stop_price": stop_loss},
            )
            return order._raw
        except Exception as e:
            print(f"Error submitting bracket order: {e}")
            return None

    def close_position(self, symbol: str) -> bool:
        try:
            resp = self.api.close_position(symbol)
            _ = getattr(resp, "_raw", resp)
            return True
        except Exception as e:
            print(f"Error closing position for {symbol}: {e}")
            return False

    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            pos = self.api.get_position(symbol)
            return pos._raw
        except Exception:
            return None


if __name__ == "__main__":
    print("Alpaca Connector Smoke Test")
    print("=" * 40)
    try:
        connector = AlpacaConnector.from_config().connect()
    except Exception as e:
        print(f"Credentials error: {e}")
        exit(1)

    acc = connector.get_account()
    if acc:
        print(f"Account status: {acc.get('status')}")
        print(f"Equity: {acc.get('equity')}")
    else:
        print("Could not fetch account info")

    clock = connector.get_clock()
    if clock:
        print(f"Market open: {clock.get('is_open')}, next close: {clock.get('next_close')}")

    quote = connector.get_last_quote("SPY")
    if quote:
        print(f"SPY bid: {quote.get('bidprice')}, ask: {quote.get('askprice')}")
