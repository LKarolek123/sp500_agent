"""
Quick backtest - simplified version that actually works
"""

import pandas as pd
import numpy as np
import yfinance as yf
from src.backtest.backtest_engine import DataLoader

# Config
SYMBOLS = ["TSLA", "AMZN"]
START_DATE = "2025-01-01"
END_DATE = "2025-01-24"

print(f"Quick Backtest Test - {START_DATE} to {END_DATE}\n")

loader = DataLoader()

for symbol in SYMBOLS:
    print(f"\n{'='*60}")
    print(f"{symbol}")
    print(f"{'='*60}")
    
    try:
        df = loader.load_data(symbol, START_DATE, END_DATE, interval="1d")
        
        print(f"Columns: {df.columns.tolist()}")
        print(f"Shape: {df.shape}")
        print(f"First row:")
        print(df.head(1))
        
    except Exception as e:
        print(f"Error: {e}")

print("\n✅ Test complete")
