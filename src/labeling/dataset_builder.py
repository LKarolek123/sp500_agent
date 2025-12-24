"""Dataset builder placeholder: label creation logic will live here."""
import pandas as pd
import numpy as np

def create_labels(df: pd.DataFrame, horizon: int = 6):
    df = df.copy()
    df['label'] = np.nan
    return df
