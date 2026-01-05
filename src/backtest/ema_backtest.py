"""
Backtest EMA crossover strategy on historical data (yfinance).

- Downloads 1 year of data for each symbol
- Simulates EMA 10/100 crossover trades
- Reports: total trades, win rate, profit/loss, Sharpe ratio
- Compares performance across 18 symbols

Run:
    python src/backtest/ema_backtest.py --symbols MSFT AAPL NVDA --lookback 252
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.live.sp500_screener import get_sp500_symbols


def download_data(symbol: str, days: int = 365) -> pd.DataFrame:
    """Download OHLCV data from yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        print("Error: yfinance not installed. Run: pip install yfinance")
        return None

    end = datetime.now()
    start = end - timedelta(days=days)

    df = yf.download(symbol, start=start, end=end, progress=False, interval="1d")
    if df.empty:
        print(f"[NO_DATA] {symbol}")
        return None

    df = df.reset_index()
    df = df[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
    df["Close"] = df["Close"].astype(float)
    return df


def backtest_ema_crossover(
    df: pd.DataFrame,
    fast: int = 10,
    slow: int = 100,
    tp_pct: float = 0.06,  # 6% take profit
    sl_pct: float = 0.03,  # 3% stop loss
) -> Dict:
    """
    Backtest EMA crossover strategy.
    
    Returns:
        {trades, wins, losses, total_pnl, win_rate, avg_trade, sharpe}
    """
    if len(df) < slow + 1:
        return None

    df = df.copy()  # Avoid SettingWithCopyWarning
    df["EMA_fast"] = df["Close"].ewm(span=fast, adjust=False).mean()
    df["EMA_slow"] = df["Close"].ewm(span=slow, adjust=False).mean()

    # Generate signals
    df["Signal"] = 0.0
    df.loc[df["EMA_fast"] > df["EMA_slow"], "Signal"] = 1.0  # long
    df.loc[df["EMA_fast"] < df["EMA_slow"], "Signal"] = -1.0  # short

    # Detect crossovers (signal change)
    df["Signal_prev"] = df["Signal"].shift(1).fillna(0)
    df["Crossover"] = (df["Signal"] != df["Signal_prev"]) & (df["Signal"] != 0)
    
    # Convert to numpy for safer iteration
    signals = df["Signal"].values
    closes = df["Close"].values
    highs = df["High"].values
    lows = df["Low"].values
    crossovers = df["Crossover"].values
    dates = df["Date"].values

    # Simulate trades
    trades = []
    in_trade = False
    entry_price = 0.0
    entry_signal = 0.0
    entry_idx = 0
    tp = 0.0
    sl = 0.0

    for idx in range(len(df)):
        if not in_trade and crossovers[idx]:
            # Enter trade
            in_trade = True
            entry_price = closes[idx]
            entry_signal = signals[idx]
            entry_idx = idx
            tp = entry_price * (1 + tp_pct if entry_signal == 1 else 1 - tp_pct)
            sl = entry_price * (1 - sl_pct if entry_signal == 1 else 1 + sl_pct)

        elif in_trade:
            # Check exit conditions (TP/SL or signal reversal)
            exit_price = None
            exit_reason = None

            if entry_signal == 1:  # long
                if highs[idx] >= tp:
                    exit_price = tp
                    exit_reason = "TP"
                elif lows[idx] <= sl:
                    exit_price = sl
                    exit_reason = "SL"
            else:  # short
                if lows[idx] <= tp:
                    exit_price = tp
                    exit_reason = "TP"
                elif highs[idx] >= sl:
                    exit_price = sl
                    exit_reason = "SL"

            # Or exit on signal reversal
            if crossovers[idx] and signals[idx] != entry_signal:
                exit_price = closes[idx]
                exit_reason = "Reversal"

            if exit_price is not None:
                pnl = (exit_price - entry_price) * entry_signal
                pnl_pct = (pnl / entry_price) * 100
                trades.append({
                    "entry_date": str(dates[entry_idx]),
                    "exit_date": str(dates[idx]),
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "signal": int(entry_signal),
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "reason": exit_reason,
                })
                in_trade = False

    if not trades:
        return None

    # Calculate metrics
    df_trades = pd.DataFrame(trades)
    total_trades = len(df_trades)
    winning_trades = len(df_trades[df_trades["pnl"] > 0])
    losing_trades = len(df_trades[df_trades["pnl"] <= 0])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    total_pnl = float(df_trades["pnl"].sum())
    avg_trade = float(df_trades["pnl"].mean())
    
    # Sharpe ratio (annualized)
    returns = df_trades["pnl_pct"].values
    if len(returns) > 1:
        sharpe = float(np.mean(returns) / (np.std(returns) + 1e-8) * np.sqrt(252))
    else:
        sharpe = 0.0

    total_pnl_pct = (total_pnl / float(df.iloc[0]["Close"])) * 100

    return {
        "total_trades": int(total_trades),
        "winning_trades": int(winning_trades),
        "losing_trades": int(losing_trades),
        "win_rate": float(win_rate),
        "total_pnl": float(total_pnl),
        "total_pnl_pct": float(total_pnl_pct),
        "avg_trade": float(avg_trade),
        "sharpe": float(sharpe),
        "trades_df": df_trades,
    }


def run_backtest(symbols: List[str], lookback_days: int = 365):
    """Run backtest for multiple symbols."""
    print("[DATA] EMA Crossover Strategy Backtest")
    print(f"Period: {lookback_days} days")
    print("=" * 80)

    results = {}
    for symbol in symbols:
        print(f"[TEST] {symbol}...", end=" ", flush=True)

        df = download_data(symbol, days=lookback_days)
        if df is None:
            print("[FAIL]")
            continue

        metrics = backtest_ema_crossover(df, fast=10, slow=100)
        if metrics is None:
            print("[SKIP]")
            continue

        results[symbol] = metrics
        print(f"[OK] {metrics['total_trades']} tr, {metrics['win_rate']:.0f}% wr, {metrics['total_pnl_pct']:.2f}%")

    # Summary table
    print("\n" + "=" * 80)
    print("SUMMARY (All symbols)")
    print("=" * 80)
    print(f"{'Symbol':<10} {'Trades':>8} {'Win%':>8} {'P&L%':>10} {'Sharpe':>10}")
    print("-" * 80)

    for symbol in sorted(results.keys()):
        m = results[symbol]
        print(
            f"{symbol:<10} {m['total_trades']:>8} {m['win_rate']:>7.1f}% "
            f"{m['total_pnl_pct']:>9.2f}% {m['sharpe']:>9.2f}"
        )

    # Best/worst symbols
    if results:
        best = max(results.items(), key=lambda x: x[1]["win_rate"])
        worst = min(results.items(), key=lambda x: x[1]["win_rate"])
        print("\n" + "=" * 80)
        print(f"[BEST] {best[0]} ({best[1]['win_rate']:.1f}% WR)")
        print(f"[WORST] {worst[0]} ({worst[1]['win_rate']:.1f}% WR)")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="EMA Crossover Backtest")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=None,
        help="Symbols to test (default: top 18 S&P 500)",
    )
    parser.add_argument("--lookback", type=int, default=365, help="Days to backtest")
    args = parser.parse_args()

    symbols = args.symbols if args.symbols else get_sp500_symbols()
    symbols = [s for s in symbols if s != "SPX"]  # exclude index

    results = run_backtest(symbols, lookback_days=args.lookback)
