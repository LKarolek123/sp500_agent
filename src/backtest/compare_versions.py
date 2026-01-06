"""
Compare v1 vs v2 strategy configurations on the same symbols and period.

v1: no reversal exit, no time-stop
v2: reversal exit enabled, time-stop = 3 days

Usage:
    python src/backtest/compare_versions.py --symbols TSLA AMZN SPY --lookback 900
    python src/backtest/compare_versions.py  # defaults to top 18 (excluding SPX)
"""
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.backtest.ema_backtest import run_backtest
from src.live.sp500_screener import get_sp500_symbols


def summarize(label: str, results: dict):
    if not results:
        print(f"[SUMMARY] {label}: no results")
        return
    total_pnl_pct = sum(m["total_pnl_pct"] for m in results.values())
    avg_pnl_pct = total_pnl_pct / max(1, len(results))
    avg_win_rate = sum(m["win_rate"] for m in results.values()) / max(1, len(results))
    print("\n" + "=" * 80)
    print(f"SUMMARY: {label}")
    print("=" * 80)
    print(f"Symbols: {len(results)} | Avg P&L%: {avg_pnl_pct:.2f}% | Avg Win%: {avg_win_rate:.1f}%")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Compare v1 vs v2 strategy configs")
    parser.add_argument("--symbols", nargs="+", default=None, help="Symbols to test")
    parser.add_argument("--lookback", type=int, default=900, help="Days to backtest")
    args = parser.parse_args()

    symbols: List[str] = args.symbols if args.symbols else [s for s in get_sp500_symbols() if s != "SPX"]

    print("\n[COMPARE] V1 (no reversal, no time-stop)")
    v1 = run_backtest(symbols, lookback_days=args.lookback, use_reversal_exit=False, time_stop_days=None)
    summarize("V1", v1)

    print("\n[COMPARE] V2 (reversal exit, time-stop=3d)")
    v2 = run_backtest(symbols, lookback_days=args.lookback, use_reversal_exit=True, time_stop_days=3)
    summarize("V2", v2)

    # Simple preference decision
    def avg(results: dict, key: str) -> float:
        if not results:
            return 0.0
        return sum(m[key] for m in results.values()) / max(1, len(results))

    v1_score = avg(v1, "total_pnl_pct") + 0.5 * avg(v1, "win_rate")
    v2_score = avg(v2, "total_pnl_pct") + 0.5 * avg(v2, "win_rate")

    print("\n" + "-" * 80)
    print(f"Preference score → V1: {v1_score:.2f} vs V2: {v2_score:.2f}")
    print("Pick higher score; you can tailor weights as needed.")
