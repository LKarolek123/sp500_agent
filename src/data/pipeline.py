"""Data pipeline: download S&P500 daily via yfinance, resample to H4 and H1, and save CSVs.

Usage:
    python -m src.data.pipeline

Outputs:
    data/raw/sp500_raw.csv
    data/resampled/sp500_H4.csv
    data/resampled/sp500_H1.csv
"""
from pathlib import Path
import pandas as pd
from .download_data import download_sp500_daily
from .resample_data import resample_ohlcv


def run(ticker: str = "^GSPC", period: str = "max",
        raw_path: str = "data/raw/sp500_raw.csv", resampled_dir: str = "data/resampled"):
    Path(resampled_dir).mkdir(parents=True, exist_ok=True)
    print(f"Downloading {ticker} (period={period}) -> {raw_path}")
    df = download_sp500_daily(save_path=raw_path, ticker=ticker, period=period)

    if df is None or df.empty:
        raise RuntimeError("Downloaded data is empty")

    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    print("Resampling to H4...")
    h4 = resample_ohlcv(df, rule="4H")
    print(f"Saving H4 -> {resampled_dir}/sp500_H4.csv")
    h4.to_csv(Path(resampled_dir) / "sp500_H4.csv")

    print("Resampling to H1...")
    h1 = resample_ohlcv(df, rule="1H")
    print(f"Saving H1 -> {resampled_dir}/sp500_H1.csv")
    h1.to_csv(Path(resampled_dir) / "sp500_H1.csv")

    print("Pipeline complete.")
    return df, h4, h1


if __name__ == "__main__":
    run()
