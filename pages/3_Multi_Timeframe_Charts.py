"""
Multi-Timeframe Charts page

- Left nav entry alongside main app and Risk Dashboard
- Single chart with timeframe selector (D1 default) and trade markers
- Quick toggles for overlays: moving averages, MACD, RSI
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.backtest.simulator_core import simulate_trades

st.set_page_config(page_title="Multi-Timeframe Charts", page_icon="📈", layout="wide")

TIMEFRAME_CONFIG = {
    "D1": {"path": "data/processed/sp500_features_labeled.csv", "freq": None},
    "H4": {"path": "data/resampled/sp500_H4.csv", "freq": None},
    "H1": {"path": "data/resampled/sp500_H1.csv", "freq": None},
    "M15": {"path": None, "freq": "15T"},
}


def compute_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def compute_rsi(close: pd.Series, period: int = 14):
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


@st.cache_data
def load_price_data(timeframe: str):
    cfg = TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG["D1"])
    note = None
    try:
        if cfg.get("path"):
            df = pd.read_csv(cfg["path"], parse_dates=["Date"])
            df = df.sort_values("Date").set_index("Date")
        else:
            fallback_cfg = TIMEFRAME_CONFIG.get("H1")
            if fallback_cfg and fallback_cfg.get("path"):
                base = pd.read_csv(fallback_cfg["path"], parse_dates=["Date"])
            else:
                base = pd.read_csv(TIMEFRAME_CONFIG["D1"]["path"], parse_dates=["Date"])
            base = base.sort_values("Date").set_index("Date")
            recent_cut = base.index.max() - pd.DateOffset(months=6)
            base_recent = base[base.index >= recent_cut]
            df = base_recent.resample(cfg["freq"]).ffill()
            note = "Brak surowych danych M15 – pokazuję ostatnie 6 mies. zagęszczone z H1/D1 (podgląd)."
        df = df[["Open", "High", "Low", "Close", "Volume"]]
        return df, note
    except Exception as e:
        st.error(f"Error loading {timeframe} data: {e}")
        return None, None


@st.cache_data
def load_best_trades():
    """Rebuild trades using best Optuna params for plotting."""
    try:
        with open("experiments/exp_031_optuna_optimization/best_parameters.json") as f:
            best = json.load(f)
        params = best.get("best_params", {})
        tp_mult = float(params.get("tp_mult", 5.0))
        sl_mult = float(params.get("sl_mult", 1.0))
        risk_per_trade = float(params.get("risk_per_trade", 0.01))
        fast_ma = int(params.get("fast_ma", 20))
        slow_ma = int(params.get("slow_ma", 50))
    except Exception as e:
        st.warning(f"Could not load best parameters: {e}")
        return []

    try:
        df = pd.read_csv("data/processed/sp500_features_labeled.csv", parse_dates=["Date"])
        df = df.sort_values("Date").set_index("Date")
        ema_fast = df["Close"].ewm(span=fast_ma, adjust=False).mean()
        ema_slow = df["Close"].ewm(span=slow_ma, adjust=False).mean()
        signal = np.where(ema_fast > ema_slow, 1, np.where(ema_fast < ema_slow, -1, 0))
        df["signal"] = signal

        trades_df, _ = simulate_trades(
            df,
            signal_col="signal",
            tp_atr=tp_mult,
            sl_atr=sl_mult,
            risk_per_trade=risk_per_trade,
            initial_capital=10000.0,
        )
        return trades_df.to_dict("records") if not trades_df.empty else []
    except Exception as e:
        st.warning(f"Could not generate trades: {e}")
        return []


def create_candlestick_chart(df_chart: pd.DataFrame, trades, timeframe: str, add_ma: bool, ma_fast: int, ma_slow: int):
    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=df_chart.index,
            open=df_chart["Open"],
            high=df_chart["High"],
            low=df_chart["Low"],
            close=df_chart["Close"],
            name="Price",
            increasing_line_color="#06a77d",
            decreasing_line_color="#d62728",
        )
    )

    if add_ma:
        ema_fast = df_chart["Close"].ewm(span=ma_fast, adjust=False).mean()
        ema_slow = df_chart["Close"].ewm(span=ma_slow, adjust=False).mean()
        fig.add_trace(go.Scatter(x=df_chart.index, y=ema_fast, mode="lines", name=f"EMA {ma_fast}", line=dict(color="#1f77b4", width=1.4)))
        fig.add_trace(go.Scatter(x=df_chart.index, y=ema_slow, mode="lines", name=f"EMA {ma_slow}", line=dict(color="#ff7f0e", width=1.4)))

    entry_dates, entry_prices = [], []
    for trade in trades:
        try:
            entry_date = pd.Timestamp(trade["entry_index"])
            if entry_date in df_chart.index:
                entry_dates.append(entry_date)
                entry_prices.append(float(trade["entry_price"]))
        except Exception:
            pass

    if entry_dates:
        fig.add_trace(
            go.Scatter(
                x=entry_dates,
                y=entry_prices,
                mode="markers",
                name="Entry",
                marker=dict(size=9, color="#06a77d", symbol="circle"),
                hovertemplate="<b>Entry</b><br>Price: %{y:.2f}<extra></extra>",
            )
        )

    exit_dates, exit_prices = [], []
    for trade in trades:
        try:
            exit_date = pd.Timestamp(trade["exit_index"])
            if exit_date in df_chart.index:
                exit_dates.append(exit_date)
                exit_prices.append(float(trade["exit_price"]))
        except Exception:
            pass

    if exit_dates:
        fig.add_trace(
            go.Scatter(
                x=exit_dates,
                y=exit_prices,
                mode="markers",
                name="Exit",
                marker=dict(size=9, color="#d62728", symbol="x"),
                hovertemplate="<b>Exit</b><br>Price: %{y:.2f}<extra></extra>",
            )
        )

    fig.update_layout(
        title=f"S&P 500 - {timeframe}",
        yaxis_title="Price (USD)",
        xaxis_title="Date",
        template="plotly_white",
        height=560,
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig


def macd_chart(df_chart: pd.DataFrame, macd_line, signal_line, hist):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_chart.index, y=hist, name="Hist", marker_color="#999999", opacity=0.4))
    fig.add_trace(go.Scatter(x=df_chart.index, y=macd_line, name="MACD", line=dict(color="#1f77b4", width=1.2)))
    fig.add_trace(go.Scatter(x=df_chart.index, y=signal_line, name="Signal", line=dict(color="#ff7f0e", width=1.2)))
    fig.update_layout(title="MACD", height=240, template="plotly_white", margin=dict(l=0, r=0, t=40, b=0))
    return fig


def rsi_chart(df_chart: pd.DataFrame, rsi: pd.Series):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_chart.index, y=rsi, name="RSI", line=dict(color="#1f77b4", width=1.2)))
    fig.add_hline(y=70, line_dash="dash", line_color="#d62728", opacity=0.6)
    fig.add_hline(y=30, line_dash="dash", line_color="#06a77d", opacity=0.6)
    fig.update_layout(title="RSI", yaxis_title="RSI", height=220, template="plotly_white", margin=dict(l=0, r=0, t=40, b=0))
    return fig


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.title("📈 Multi-Timeframe Charts")
st.markdown("Wybierz interwał (D1 domyślnie), a następnie włącz/wyłącz MA, MACD, RSI. Punkty buy/sell pochodzą z najlepszych parametrów Optuna.")

timeframe = st.selectbox(
    "Interwał",
    options=list(TIMEFRAME_CONFIG.keys()),
    index=0,
    help="Przełącz wykres między D1 / H4 / H1 / M15"
)

prices_df, tf_note = load_price_data(timeframe)
trades = load_best_trades()

if prices_df is None:
    st.error("Nie udało się wczytać danych cenowych")
    st.stop()

if tf_note:
    st.info(tf_note)

chart_placeholder = st.empty()

# Settings rendered below the chart area
with st.expander("Ustawienia wykresu", expanded=False):
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        months_back = st.slider("Pokaż ostatnie N miesięcy", min_value=1, max_value=60, value=12, step=1)
    with col_b:
        add_ma = st.checkbox("Pokaż EMA", value=True)
        ma_fast = st.number_input("EMA fast", min_value=2, max_value=200, value=20, step=1)
        ma_slow = st.number_input("EMA slow", min_value=5, max_value=400, value=50, step=1)
    with col_c:
        show_macd = st.checkbox("Pokaż MACD", value=False)
        macd_fast = st.number_input("MACD fast", min_value=2, max_value=100, value=12, step=1)
        macd_slow = st.number_input("MACD slow", min_value=5, max_value=150, value=26, step=1)
        macd_signal = st.number_input("MACD signal", min_value=2, max_value=100, value=9, step=1)
        show_rsi = st.checkbox("Pokaż RSI", value=False)
        rsi_len = st.number_input("RSI length", min_value=2, max_value=200, value=14, step=1)

cutoff_date = prices_df.index[-1] - pd.DateOffset(months=months_back)
chart_df = prices_df[prices_df.index >= cutoff_date].copy()
trades_recent = [t for t in trades if pd.Timestamp(t.get("entry_index", chart_df.index[0])) >= cutoff_date]

st.markdown(f"Pokazuję {len(trades_recent)} transakcji z ostatnich {months_back} miesięcy")

fig_price = create_candlestick_chart(chart_df, trades_recent, timeframe, add_ma, int(ma_fast), int(ma_slow))
chart_placeholder.plotly_chart(fig_price, use_container_width=True)

if show_macd:
    macd_line, signal_line, hist = compute_macd(chart_df["Close"], fast=int(macd_fast), slow=int(macd_slow), signal=int(macd_signal))
    fig_macd = macd_chart(chart_df, macd_line, signal_line, hist)
    st.plotly_chart(fig_macd, use_container_width=True)

if show_rsi:
    rsi_vals = compute_rsi(chart_df["Close"], period=int(rsi_len))
    fig_rsi = rsi_chart(chart_df, rsi_vals)
    st.plotly_chart(fig_rsi, use_container_width=True)

st.markdown("### Statystyki transakcji")
if trades_recent:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Liczba transakcji", len(trades_recent))
    with col2:
        winning_trades = len([t for t in trades_recent if float(t.get("pl", 0)) > 0])
        win_rate = (winning_trades / len(trades_recent) * 100) if trades_recent else 0
        st.metric("Win Rate", f"{win_rate:.1f}%")
    with col3:
        total_pl = sum(float(t.get("pl", 0)) for t in trades_recent)
        st.metric("Total P&L", f"{total_pl:.2f} PLN", delta_color="off")
else:
    st.info("Brak transakcji w wybranym okresie lub nie udało się ich odtworzyć – pokazuję sam wykres ceny.")
