"""Download helpers for OHLCV data (yfinance).

Placeholder: function to download daily S&P500 and save to data/raw.
"""
import yfinance as yf
import pandas as pd
from pathlib import Path

def download_sp500_daily(save_path: str = "data/raw/sp500_raw.csv", ticker: str = "^GSPC", period: str = "max"):
    df = yf.download(ticker, period=period, progress=False)
    df.to_csv(save_path)
    return df
