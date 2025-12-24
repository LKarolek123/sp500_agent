"""Market structure helpers.

Provides a simple, robust structure label used by the feature engine.

The implementation is intentionally conservative and easy to reason about:
- Compare current candle High/Low vs previous candle
- If both High and Low are higher -> bullish structure (1)
- If both High and Low are lower -> bearish structure (-1)
- Otherwise -> neutral (0)

This gives a per-row discrete signal useful for both rules and ML.
"""
import pandas as pd


def structure_state(df: pd.DataFrame) -> pd.Series:
    df = df.copy()
    s = pd.Series(index=df.index, data=0, dtype=int)

    if len(df) < 2:
        return s

    highs = df['High'].values
    lows = df['Low'].values

    for i in range(1, len(df)):
        if highs[i] > highs[i - 1] and lows[i] > lows[i - 1]:
            s.iat[i] = 1
        elif highs[i] < highs[i - 1] and lows[i] < lows[i - 1]:
            s.iat[i] = -1
        else:
            s.iat[i] = 0

    return s
