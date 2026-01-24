"""
Quick test - just download data and check format
"""

import yfinance as yf
import pandas as pd

print("Downloading TSLA...")
df = yf.download("TSLA", start="2025-01-01", end="2025-01-24", interval="1d", progress=False)

print(f"\nType of df: {type(df)}")
print(f"Columns: {df.columns.tolist()}")
print(f"Index type: {type(df.index)}")
print(f"Index name: {df.index.name}")
print(f"Shape: {df.shape}")
print("\nFirst few rows:")
print(df.head())

# Reset index
df_reset = df.reset_index()
print(f"\nAfter reset_index:")
print(f"Columns: {df_reset.columns.tolist()}")
print(df_reset.head())
