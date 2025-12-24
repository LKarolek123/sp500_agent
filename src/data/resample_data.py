"""Resample D1 -> H4/H1 helpers (placeholder).
"""
import pandas as pd


def resample_ohlcv(df: pd.DataFrame, rule: str = "4H") -> pd.DataFrame:
    o = df['Open'].resample(rule).first()
    h = df['High'].resample(rule).max()
    l = df['Low'].resample(rule).min()
    c = df['Close'].resample(rule).last()
    v = df['Volume'].resample(rule).sum()
    res = pd.concat([o,h,l,c,v], axis=1)
    res.columns = ['Open','High','Low','Close','Volume']
    return res.dropna()
