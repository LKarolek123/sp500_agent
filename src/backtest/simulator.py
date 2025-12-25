"""Backtest simulator: execute trades based on discrete signals and ATR-based SL/TP.

Assumptions:
- Input DataFrame must be chronological and contain columns: Open, High, Low, Close, ATR
- Signals are discrete per bar in column `signal` with values {-1,0,1}
- Entry is on next bar `Open` after signal (i+1). SL/TP are set relative to entry using ATR at signal bar.

Output: trades DataFrame and equity series.
"""
from typing import Tuple
import pandas as pd
import numpy as np


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
                    dynamic_window: int = 20) -> Tuple[pd.DataFrame, pd.Series]:
    df = df.copy()
    df = df.sort_index()

    trades = []
    equity = initial_capital
    equity_curve = []

    # prepare reference ATR for dynamic notional scaling
    if dynamic_notional and 'ATR' in df.columns:
        # use rolling median of ATR as reference volatility
        try:
            atr_ref = float(df['ATR'].rolling(dynamic_window).median().median())
        except Exception:
            atr_ref = float(df['ATR'].median(skipna=True)) if not df['ATR'].dropna().empty else 1.0
    else:
        atr_ref = None

    n = len(df)
    for i in range(n - 1):
        signal = df.iloc[i][signal_col] if signal_col in df.columns else 0
        if signal == 0 or pd.isna(signal):
            equity_curve.append(equity)
            continue

        entry_idx = i + 1
        if entry_idx >= n:
            equity_curve.append(equity)
            continue

        entry_price = df.iloc[entry_idx]['Open']
        atr = df.iloc[i].get('ATR', np.nan)
        if pd.isna(atr) or atr <= 0:
            equity_curve.append(equity)
            continue

        direction = 1 if signal == 1 else -1
        stop_price = entry_price - direction * sl_atr * atr
        tp_price = entry_price + direction * tp_atr * atr

        # position sizing (shares/contracts) via risk_per_trade
        stop_distance = abs(entry_price - stop_price)
        if stop_distance == 0:
            equity_curve.append(equity)
            continue

        risk_amount = equity * risk_per_trade
        raw_qty = risk_amount / stop_distance

        # determine effective max notional per trade (supports dynamic scaling by ATR)
        effective_max_notional = equity * max_notional_per_trade
        if dynamic_notional and atr_ref is not None and atr > 0:
            # scale base notional inversely with current ATR: when ATR is high, reduce notional
            scaled = equity * base_notional_per_trade * (atr_ref / float(atr))
            # clip reasonable bounds
            min_cap = equity * 0.001
            max_cap = equity * 0.5
            scaled = max(min(scaled, max_cap), min_cap)
            effective_max_notional = min(effective_max_notional, scaled)

        if raw_qty * entry_price > effective_max_notional and entry_price > 0:
            raw_qty = effective_max_notional / entry_price

        qty = int(max(min_qty, int(raw_qty)))
        if qty <= 0:
            equity_curve.append(equity)
            continue

        # walk-forward to find exit
        exit_price = None
        exit_index = None
        exit_reason = None

        for j in range(entry_idx, n):
            high = df.iloc[j]['High']
            low = df.iloc[j]['Low']

            if direction == 1:
                # LONG: TP hit if high >= tp_price; SL hit if low <= stop_price
                if low <= stop_price:
                    exit_price = stop_price
                    exit_index = j
                    exit_reason = 'SL'
                    break
                if high >= tp_price:
                    exit_price = tp_price
                    exit_index = j
                    exit_reason = 'TP'
                    break
            else:
                # SHORT
                if high >= stop_price:
                    exit_price = stop_price
                    exit_index = j
                    exit_reason = 'SL'
                    break
                if low <= tp_price:
                    exit_price = tp_price
                    exit_index = j
                    exit_reason = 'TP'
                    break

        # if neither hit, exit at last available close
        if exit_price is None:
            exit_index = n - 1
            exit_price = df.iloc[exit_index]['Close']
            exit_reason = 'TIMEOUT'

        # slippage and commission (approximate)
        slippage_cost = 2 * qty * entry_price * slippage_pct  # entry + exit
        commission = commission_per_trade

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

    # pad equity_curve to full length
    while len(equity_curve) < n:
        equity_curve.append(equity)

    trades_df = pd.DataFrame(trades)
    equity_ser = pd.Series(equity_curve, index=df.index)
    return trades_df, equity_ser
"""Backtest simulator: execute trades based on discrete signals and ATR-based SL/TP.

Assumptions:
- Input DataFrame must be chronological and contain columns: Open, High, Low, Close, ATR
- Signals are discrete per bar in column `signal` with values {-1,0,1}
- Entry is on next bar `Open` after signal (i+1). SL/TP are set relative to entry using ATR at signal bar.

Output: trades DataFrame and equity series.
"""
from typing import Tuple
import pandas as pd
import numpy as np


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
                    base_notional_per_trade: float = 0.05) -> Tuple[pd.DataFrame, pd.Series]:
    df = df.copy()
    df = df.sort_index()

    trades = []
    equity = initial_capital
    equity_curve = []

    # prepare reference ATR for dynamic notional scaling
    if dynamic_notional and 'ATR' in df.columns:
        atr_ref = float(df['ATR'].median(skipna=True)) if not df['ATR'].dropna().empty else 1.0
    else:
        atr_ref = None

    n = len(df)
        if dynamic_notional and 'ATR' in df.columns:
            atr_ref = float(df['ATR'].rolling(dynamic_window).median().median()) if not df['ATR'].dropna().empty else 1.0
        else:
            atr_ref = None
            continue

        entry_idx = i + 1
        if entry_idx >= n:
            equity_curve.append(equity)
            continue

        entry_price = df.iloc[entry_idx]['Open']
        atr = df.iloc[i].get('ATR', np.nan)
        if pd.isna(atr) or atr <= 0:
            equity_curve.append(equity)
            continue

        direction = 1 if signal == 1 else -1
        stop_price = entry_price - direction * sl_atr * atr
        tp_price = entry_price + direction * tp_atr * atr

        # position sizing (shares/contracts) via risk_per_trade
        stop_distance = abs(entry_price - stop_price)
        if stop_distance == 0:
            equity_curve.append(equity)
            continue

        risk_amount = equity * risk_per_trade
        raw_qty = risk_amount / stop_distance

        # determine effective max notional per trade (supports dynamic scaling by ATR)
        effective_max_notional = equity * max_notional_per_trade
        if dynamic_notional and atr_ref is not None and atr > 0:
            # scale base notional inversely with current ATR: when ATR is high, reduce notional
            scaled = equity * base_notional_per_trade * (atr_ref / float(atr))
            # clip reasonable bounds
            min_cap = equity * 0.001
            effective_max_notional = equity * max_notional_per_trade
            if dynamic_notional and atr_ref is not None and atr > 0:
                # scale base notional inversely with current ATR: when ATR is high, reduce notional
                scaled = equity * base_notional_per_trade * (atr_ref / float(atr))
                # clip reasonable bounds
                min_cap = equity * 0.001
                max_cap = equity * 0.5
                scaled = max(min(scaled, max_cap), min_cap)
                effective_max_notional = min(effective_max_notional, scaled)
            equity_curve.append(equity)
            continue

        # walk-forward to find exit
        exit_price = None
        exit_index = None
        exit_reason = None

                    dynamic_notional: bool = False,
                    base_notional_per_trade: float = 0.05) -> Tuple[pd.DataFrame, pd.Series]:
        for j in range(entry_idx, n):
            high = df.iloc[j]['High']
            low = df.iloc[j]['Low']

            if direction == 1:
                # LONG: TP hit if high >= tp_price; SL hit if low <= stop_price
                if low <= stop_price:
                    exit_price = stop_price
                    exit_index = j
                    exit_reason = 'SL'
                    break
                if high >= tp_price:
                    exit_price = tp_price
                    exit_index = j
                    exit_reason = 'TP'
                    break
            else:
                # SHORT
                if high >= stop_price:
                    exit_price = stop_price
                    exit_index = j
                    exit_reason = 'SL'
                    break
                if low <= tp_price:
                    exit_price = tp_price
                    exit_index = j
                    exit_reason = 'TP'
                    break

        # if neither hit, exit at last available close
        if exit_price is None:
            exit_index = n - 1
            exit_price = df.iloc[exit_index]['Close']
            exit_reason = 'TIMEOUT'

        # slippage and commission (approximate)
        slippage_cost = 2 * qty * entry_price * slippage_pct  # entry + exit
        commission = commission_per_trade

        pl = direction * (exit_price - entry_price) * qty - slippage_cost - commission
        pnl_pct = pl / equity
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

        if raw_qty * entry_price > effective_max_notional and entry_price > 0:

    # pad equity_curve to full length
    while len(equity_curve) < n:
        equity_curve.append(equity)

    trades_df = pd.DataFrame(trades)
    equity_ser = pd.Series(equity_curve, index=df.index)
    return trades_df, equity_ser
"""Backtest simulator placeholder."""

def simulate():
    pass
