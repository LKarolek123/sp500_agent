"""
ML-based weight optimization for scoring system.

Uses Optuna to find optimal weights for:
  - EMA Crossover
  - RSI Confirmation
  - MACD Histogram
  - S/R Bounce
  - Volume Confirmation

Constraint: weights sum to 90 (10 reserved for future indicators).

Run:
    python optimize_weights.py --symbols TSLA DIS GOOGL JNJ JPM LLY META AMZN SPY --trials 100
"""
import sys
import argparse
from pathlib import Path
from typing import List, Dict
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from src.backtest.ema_backtest import download_data, backtest_ema_crossover
from src.live.sp500_screener import get_sp500_symbols
from src.live.technical_indicators import (
    calculate_rsi, calculate_macd, calculate_support_resistance,
    detect_support_resistance_signal, calculate_volume_ma
)

try:
    import optuna
except ImportError:
    print("Error: optuna not installed. Run: pip install optuna")
    sys.exit(1)


def score_trade_custom(
    df: pd.DataFrame,
    ema_signal: int,
    rsi: float,
    macd_hist: float,
    sr_signal: int,
    volume_ratio: float,
    weights: Dict[str, float]
) -> int:
    """
    Score a trade with custom weights.
    
    weights = {
        'ema': X,
        'rsi': Y,
        'macd': Z,
        'sr': W,
        'vol': V
    } where X+Y+Z+W+V = 90
    """
    score = 0
    
    # EMA
    if ema_signal != 0:
        score += weights['ema']
    
    # RSI
    if ema_signal == 1:
        if rsi < 30:
            rsi_score = weights['rsi'] * 0.5
        elif rsi < 50:
            rsi_score = weights['rsi']
        elif rsi < 70:
            rsi_score = weights['rsi'] * 0.5
        else:
            rsi_score = 0
    elif ema_signal == -1:
        if rsi > 70:
            rsi_score = weights['rsi'] * 0.5
        elif rsi > 50:
            rsi_score = weights['rsi']
        elif rsi > 30:
            rsi_score = weights['rsi'] * 0.5
        else:
            rsi_score = 0
    else:
        rsi_score = 0
    score += rsi_score
    
    # MACD
    if ema_signal == 1 and macd_hist > 0:
        score += weights['macd']
    elif ema_signal == -1 and macd_hist < 0:
        score += weights['macd']
    elif ema_signal != 0:
        score += weights['macd'] * 0.25
    
    # S/R
    if sr_signal == ema_signal and sr_signal != 0:
        score += weights['sr']
    elif sr_signal == 0 and ema_signal != 0:
        score += weights['sr'] * 0.5
    
    # Volume
    if volume_ratio >= 1.0:
        score += weights['vol']
    
    return int(score)


def backtest_with_weights(
    symbols: List[str],
    lookback: int,
    weights: Dict[str, float]
) -> float:
    """
    Backtest with custom weights, return total P&L%.
    """
    total_pnl = 0.0
    count = 0
    
    for symbol in symbols:
        df = download_data(symbol, days=lookback)
        if df is None or len(df) < 110:
            continue
        
        # Add indicators
        df["Close_orig"] = df["Close"]
        df["RSI"] = calculate_rsi(df["Close"], period=14)
        macd_line, signal_line, histogram = calculate_macd(df["Close"])
        df["MACD_Hist"] = histogram
        
        # EMA signals
        df["EMA_fast"] = df["Close"].ewm(span=10, adjust=False).mean()
        df["EMA_slow"] = df["Close"].ewm(span=100, adjust=False).mean()
        df["EMA_signal"] = 0
        df.loc[df["EMA_fast"] > df["EMA_slow"], "EMA_signal"] = 1
        df.loc[df["EMA_fast"] < df["EMA_slow"], "EMA_signal"] = -1
        
        # S/R
        support_list = []
        resistance_list = []
        for i in range(len(df)):
            if i < 20:
                support_list.append(None)
                resistance_list.append(None)
            else:
                recent = df.iloc[max(0, i-20):i]
                support_list.append(recent["Low"].min())
                resistance_list.append(recent["High"].max())
        df["Support"] = support_list
        df["Resistance"] = resistance_list
        
        # Volume MA
        df["Volume_MA"] = calculate_volume_ma(df["Volume"], period=20)
        df["Volume_Ratio"] = df["Volume"] / (df["Volume_MA"] + 1e-8)
        
        # Detect crossovers
        df["Signal_prev"] = df["EMA_signal"].shift(1).fillna(0)
        df["Crossover"] = (df["EMA_signal"] != df["Signal_prev"]) & (df["EMA_signal"] != 0)
        
        # Simulate trades with custom scoring
        trades = []
        in_trade = False
        entry_price = 0.0
        entry_signal = 0
        entry_idx = 0
        
        for idx in range(len(df)):
            if not in_trade and df["Crossover"].iloc[idx]:
                ema_sig = int(df["EMA_signal"].iloc[idx])
                rsi_val = df["RSI"].iloc[idx]
                macd_hist_val = df["MACD_Hist"].iloc[idx]
                support = df["Support"].iloc[idx]
                resistance = df["Resistance"].iloc[idx]
                sr_sig = detect_support_resistance_signal(df["Close"].iloc[idx], support, resistance)
                vol_ratio = df["Volume_Ratio"].iloc[idx]
                
                score = score_trade_custom(
                    df, ema_sig, rsi_val, macd_hist_val, sr_sig, vol_ratio, weights
                )
                
                if score >= 40:
                    in_trade = True
                    entry_price = df["Close"].iloc[idx]
                    entry_signal = ema_sig
                    entry_idx = idx
            
            elif in_trade:
                tp = entry_price * 1.06 if entry_signal == 1 else entry_price * 0.94
                sl = entry_price * 0.97 if entry_signal == 1 else entry_price * 1.03
                
                exit_price = None
                if entry_signal == 1:
                    if df["High"].iloc[idx] >= tp:
                        exit_price = tp
                    elif df["Low"].iloc[idx] <= sl:
                        exit_price = sl
                else:
                    if df["Low"].iloc[idx] <= tp:
                        exit_price = tp
                    elif df["High"].iloc[idx] >= sl:
                        exit_price = sl
                
                if exit_price:
                    pnl_pct = (exit_price - entry_price) / entry_price * 100 * entry_signal
                    trades.append(pnl_pct)
                    in_trade = False
        
        if trades:
            symbol_pnl = sum(trades) / len(trades) * len(trades) / 10  # normalize
            total_pnl += symbol_pnl
            count += 1
    
    return total_pnl / max(1, count)


def objective(trial, symbols: List[str], lookback: int):
    """Optuna objective: maximize avg P&L% with weights summing to 90."""
    # Sample weights that sum to 90
    ema_w = trial.suggest_float("ema", 20.0, 60.0)
    rsi_w = trial.suggest_float("rsi", 5.0, 40.0)
    macd_w = trial.suggest_float("macd", 5.0, 40.0)
    sr_w = trial.suggest_float("sr", 5.0, 40.0)
    vol_w = trial.suggest_float("vol", 0.0, 15.0)
    
    # Normalize to sum to 90
    total = ema_w + rsi_w + macd_w + sr_w + vol_w
    weights = {
        'ema': (ema_w / total) * 90,
        'rsi': (rsi_w / total) * 90,
        'macd': (macd_w / total) * 90,
        'sr': (sr_w / total) * 90,
        'vol': (vol_w / total) * 90,
    }
    
    avg_pnl = backtest_with_weights(symbols, lookback, weights)
    return avg_pnl


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimize indicator weights with ML")
    parser.add_argument("--symbols", nargs="+", default=None, help="Symbols to optimize on")
    parser.add_argument("--lookback", type=int, default=900, help="Days to backtest")
    parser.add_argument("--trials", type=int, default=100, help="Number of Optuna trials")
    args = parser.parse_args()
    
    symbols = args.symbols if args.symbols else [s for s in get_sp500_symbols() if s != "SPX"]
    
    print(f"[ML OPTIMIZE] Symbols: {len(symbols)}, Lookback: {args.lookback} days, Trials: {args.trials}")
    print("=" * 80)
    
    study = optuna.create_study(direction="maximize", study_name="weights_optimization")
    study.optimize(lambda trial: objective(trial, symbols, args.lookback), n_trials=args.trials)
    
    print("\n" + "=" * 80)
    print("BEST WEIGHTS (sum=90):")
    print("=" * 80)
    
    best_params = study.best_params
    total = sum(best_params.values())
    
    optimal_weights = {
        'ema': (best_params['ema'] / total) * 90,
        'rsi': (best_params['rsi'] / total) * 90,
        'macd': (best_params['macd'] / total) * 90,
        'sr': (best_params['sr'] / total) * 90,
        'vol': (best_params['vol'] / total) * 90,
    }
    
    for name, weight in optimal_weights.items():
        print(f"  {name.upper():<8} {weight:>6.2f}%")
    
    print(f"\nBest Avg P&L: {study.best_value:.2f}%")
    print("\nUpdate src/live/technical_indicators.py score_trade() with these weights!")
