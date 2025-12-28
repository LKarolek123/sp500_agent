import pandas as pd
import numpy as np
from typing import Tuple


def simulate_trades(df: pd.DataFrame,
                    signal_col: str = 'signal',
                    sl_atr: float = 1.0,
                    tp_atr: float = 2.0,
                    risk_per_trade: float = 0.01,
                    initial_capital: float = 100000.0,
                    max_notional_per_trade: float = 0.05,
                    slippage_pct: float = 0.0005,
                    commission_per_trade: float = 1.0,
                    min_qty: int = 1,
                    dynamic_notional: bool = False,
                    base_notional_per_trade: float = 0.05,
                    dynamic_window: int = 20,
                    max_qty: int = 100,
                    min_stop_distance_pct: float = 0.005,
                    max_notional_absolute: float = 50000.0) -> Tuple[pd.DataFrame, pd.Series]:
    """Simulate trades from discrete signals with ATR-based SL/TP and sizing.

    - Entries are on next-bar `Open` after a non-zero `signal` value.
    - Stop and take-profit are set relative to entry using ATR measured on the
      signal bar.
    - Position sizing uses `risk_per_trade` (fraction of equity) with an
      optional `max_notional_per_trade` cap and an optional `dynamic_notional`
      scaling that reduces notional when ATR is elevated.

    Returns a tuple (trades_df, equity_series).
    """
    df = df.copy()
    df = df.sort_index()

    trades = []
    equity = float(initial_capital)
    equity_curve = []

    # compute a stable ATR reference for dynamic sizing (single scalar)
    if dynamic_notional and 'ATR' in df.columns:
        try:
            atr_ref = float(df['ATR'].rolling(dynamic_window).median().dropna().median())
            if np.isnan(atr_ref) or atr_ref <= 0:
                atr_ref = float(df['ATR'].median(skipna=True) or 1.0)
        except Exception:
            atr_ref = float(df['ATR'].median(skipna=True) or 1.0)
    else:
        atr_ref = None

    n = len(df)
    for i in range(n - 1):
        signal = df.iloc[i].get(signal_col, 0) if signal_col in df.columns else 0
        if signal == 0 or pd.isna(signal):
            equity_curve.append(equity)
            continue

        entry_idx = i + 1
        if entry_idx >= n:
            equity_curve.append(equity)
            continue

        # prices and ATR at signal bar
        entry_price = df.iloc[entry_idx].get('Open', np.nan)
        atr = df.iloc[i].get('ATR', np.nan) if 'ATR' in df.columns else np.nan
        if pd.isna(entry_price) or pd.isna(atr) or atr <= 0:
            equity_curve.append(equity)
            continue

        direction = 1 if signal == 1 else -1
        stop_price = entry_price - direction * sl_atr * atr
        tp_price = entry_price + direction * tp_atr * atr

        # sizing: risk-based quantity
        stop_distance = abs(entry_price - stop_price)
        # enforce minimum stop distance as % of entry price
        min_stop = entry_price * min_stop_distance_pct
        if stop_distance < min_stop:
            stop_distance = min_stop
            stop_price = entry_price - direction * stop_distance
        if stop_distance == 0:
            equity_curve.append(equity)
            continue

        risk_amount = equity * float(risk_per_trade)
        raw_qty = risk_amount / stop_distance

        # determine effective notional cap
        effective_max_notional = equity * float(max_notional_per_trade)
        if dynamic_notional and atr_ref is not None and atr > 0:
            scaled = equity * float(base_notional_per_trade) * (atr_ref / float(atr))
            min_cap = equity * 0.001
            max_cap = equity * 0.5
            scaled = max(min(scaled, max_cap), min_cap)
            effective_max_notional = min(effective_max_notional, scaled)

        # cap by notional
        if entry_price > 0 and raw_qty * entry_price > effective_max_notional:
            raw_qty = effective_max_notional / entry_price
        
        # cap by absolute notional
        if entry_price > 0 and raw_qty * entry_price > max_notional_absolute:
            raw_qty = max_notional_absolute / entry_price

        qty = int(max(min_qty, int(raw_qty)))
        # enforce hard max_qty limit
        if qty > max_qty:
            qty = max_qty
        if qty <= 0:
            equity_curve.append(equity)
            continue

        # find exit by scanning subsequent bars for SL/TP
        exit_price = None
        exit_index = None
        exit_reason = None

        for j in range(entry_idx, n):
            high = df.iloc[j].get('High', np.nan)
            low = df.iloc[j].get('Low', np.nan)

            if direction == 1:
                if not pd.isna(low) and low <= stop_price:
                    exit_price = stop_price
                    exit_index = j
                    exit_reason = 'SL'
                    break
                if not pd.isna(high) and high >= tp_price:
                    exit_price = tp_price
                    exit_index = j
                    exit_reason = 'TP'
                    break
            else:
                if not pd.isna(high) and high >= stop_price:
                    exit_price = stop_price
                    exit_index = j
                    exit_reason = 'SL'
                    break
                if not pd.isna(low) and low <= tp_price:
                    exit_price = tp_price
                    exit_index = j
                    exit_reason = 'TP'
                    break

        # fallback: exit at last close
        if exit_price is None:
            exit_index = n - 1
            exit_price = df.iloc[exit_index].get('Close', entry_price)
            exit_reason = 'TIMEOUT'

        # costs
        slippage_cost = 2 * qty * entry_price * float(slippage_pct)
        commission = float(commission_per_trade)

        pl = direction * (exit_price - entry_price) * qty - slippage_cost - commission
        pnl_pct = pl / equity if equity != 0 else 0.0
        equity += pl

        trades.append({
            'entry_index': df.index[entry_idx],
            'exit_index': df.index[exit_index],
            'direction': direction,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'qty': qty,
            'pl': pl,
            'pnl_pct': pnl_pct,
        })

        equity_curve.append(equity)

    # pad equity curve
    while len(equity_curve) < n:
        equity_curve.append(equity)

    trades_df = pd.DataFrame(trades)
    equity_ser = pd.Series(equity_curve, index=df.index)
    return trades_df, equity_ser
