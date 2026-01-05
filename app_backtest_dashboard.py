"""
Streamlit Dashboard - Trading Strategy Backtest Results
Shows statistics from all historical tests on S&P 500 stocks
"""
import streamlit as st
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from src.backtest.ema_backtest import download_data, backtest_ema_crossover
from src.live.sp500_screener import get_profitable_8_symbols, get_sp500_symbols

# Page config
st.set_page_config(
    page_title="S&P 500 Trading Bot Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title
st.title("📊 S&P 500 Trading Strategy Dashboard")
st.markdown("*Historical Backtest Results & Performance Metrics*")

# Sidebar configuration
st.sidebar.header("Configuration")
backtest_mode = st.sidebar.selectbox(
    "Select Backtest Mode",
    ["Top 8 Profitable Stocks", "All 18 Stocks", "Custom Symbols"],
    index=0
)

lookback_days = st.sidebar.slider(
    "Historical Data (years)",
    1, 5, 2,
    help="How many years of historical data to test"
)

tp_pct = st.sidebar.slider("Take Profit %", 1, 15, 6, step=1, help="Take profit level") / 100
sl_pct = st.sidebar.slider("Stop Loss %", 1, 10, 3, step=1, help="Stop loss level") / 100

# Select symbols based on mode
if backtest_mode == "Top 8 Profitable Stocks":
    symbols = get_profitable_8_symbols()
elif backtest_mode == "All 18 Stocks":
    symbols = [s for s in get_sp500_symbols() if s != "SPX"]
else:
    custom_input = st.sidebar.text_input(
        "Enter symbols (comma-separated)",
        "TSLA,GOOGL,AMZN",
        help="e.g., TSLA,GOOGL,AMZN"
    )
    symbols = [s.strip().upper() for s in custom_input.split(",")]

run_backtest = st.sidebar.button("Run Backtest", use_container_width=True)

# Main content
if run_backtest:
    st.info(f"Running backtest on {len(symbols)} symbols for {lookback_days} years...")
    
    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    results = {}
    total_pnl = 0
    profitable_count = 0
    
    for idx, sym in enumerate(symbols):
        status_text.text(f"Processing {sym}... ({idx+1}/{len(symbols)})")
        
        # Download data
        df = download_data(sym, days=lookback_days * 365)
        
        if df is not None:
            # Run backtest
            result = backtest_ema_crossover(df, fast=10, slow=100, tp_pct=tp_pct, sl_pct=sl_pct)
            if result:
                results[sym] = result
                total_pnl += result['total_pnl_pct']
                if result['total_pnl_pct'] > 0:
                    profitable_count += 1
        
        # Update progress
        progress_bar.progress((idx + 1) / len(symbols))
    
    status_text.text("Backtest completed!")
    
    if results:
        # Create results DataFrame
        results_df = pd.DataFrame(results).T
        results_df = results_df.sort_values('total_pnl_pct', ascending=False)
        
        # Summary metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "Total Symbols",
                len(results),
                f"{profitable_count}/{len(results)} profitable"
            )
        
        with col2:
            avg_pnl = total_pnl / len(results) if results else 0
            st.metric(
                "Average P&L",
                f"{avg_pnl:.2f}%",
                f"{avg_pnl - 0.91:.2f}pp vs baseline"
            )
        
        with col3:
            st.metric(
                "Best Performer",
                results_df.index[0],
                f"+{results_df.iloc[0]['total_pnl_pct']:.2f}%"
            )
        
        with col4:
            st.metric(
                "Worst Performer",
                results_df.index[-1],
                f"{results_df.iloc[-1]['total_pnl_pct']:.2f}%"
            )
        
        with col5:
            profitable_pct = (profitable_count / len(results)) * 100 if results else 0
            st.metric(
                "Profitability Rate",
                f"{profitable_pct:.0f}%",
                f"{profitable_count}/{len(results)} symbols"
            )
        
        # Detailed results table
        st.subheader("Detailed Results")
        
        # Format results for display
        display_df = results_df.copy()
        display_df.columns = ["Trades", "Wins", "Losses", "Win Rate %", "Total P&L %", "Avg Trade %", "Sharpe"]
        display_df["Win Rate %"] = display_df["Win Rate %"].apply(lambda x: f"{x:.1f}%")
        display_df["Total P&L %"] = display_df["Total P&L %"].apply(lambda x: f"{x:.2f}%")
        display_df["Avg Trade %"] = display_df["Avg Trade %"].apply(lambda x: f"{x:.2f}%")
        display_df["Sharpe"] = display_df["Sharpe"].apply(lambda x: f"{x:.2f}")
        display_df.index.name = "Symbol"
        
        st.dataframe(
            display_df,
            use_container_width=True,
            height=400
        )
        
        # Charts
        st.subheader("Performance Visualization")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.bar_chart(
                results_df[['total_pnl_pct']].rename(columns={'total_pnl_pct': 'P&L %'}),
                use_container_width=True
            )
            st.caption("Total P&L by Symbol")
        
        with col2:
            st.bar_chart(
                results_df[['win_rate']].rename(columns={'win_rate': 'Win Rate %'}),
                use_container_width=True
            )
            st.caption("Win Rate by Symbol")
        
        # Trade distribution
        st.subheader("Trade Statistics")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Total Trades",
                int(results_df['total_trades'].sum()),
                f"Avg {results_df['total_trades'].mean():.1f} per symbol"
            )
        
        with col2:
            st.metric(
                "Total Wins",
                int(results_df['total_wins'].sum()),
                f"Avg {results_df['total_wins'].mean():.1f} per symbol"
            )
        
        # Settings info
        st.subheader("Backtest Settings")
        st.info(
            f"""
            **Strategy**: EMA 10/100 Crossover
            **Period**: {lookback_days} year(s)
            **Take Profit**: {tp_pct*100:.1f}%
            **Stop Loss**: {sl_pct*100:.1f}%
            **Timestamp**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
        )
    else:
        st.error("No valid results. Check if symbols are correct and data is available.")
else:
    # Show static info
    st.markdown("""
    ### Welcome to the S&P 500 Trading Strategy Dashboard
    
    This dashboard allows you to run and analyze historical backtests of the EMA 10/100 crossover strategy.
    
    **Features:**
    - 📊 Backtest on top 8 profitable stocks or all 18 S&P 500 stocks
    - ⚙️ Customize Take Profit and Stop Loss levels
    - 📈 View detailed performance metrics for each symbol
    - 📉 Compare strategies and performance
    
    **Current Strategy:**
    - **Signal**: EMA 10/100 crossover
    - **Default TP**: 6% | **Default SL**: 3%
    - **Risk Management**: Max 5 concurrent positions
    
    **Top 8 Profitable Symbols:**
    1. TSLA (+30.87%)
    2. DIS (+14.95%)
    3. GOOGL (+14.10%)
    4. JNJ (+11.37%)
    5. JPM (+7.97%)
    6. LLY (+6.88%)
    7. META (+4.92%)
    8. AMZN (+1.20%)
    
    👈 Configure your backtest in the sidebar and click **Run Backtest** to start!
    """)
    
    # Show comparison info
    st.markdown("""
    ### Strategy Comparison Results
    
    **EMA 10/100 vs MA20/MA50 (2 years, 8 symbols)**
    
    | Metric | EMA 10/100 | MA20/MA50 | Winner |
    |--------|-----------|----------|--------|
    | Total P&L | 327.00% | 318.00% | EMA +9pp |
    | Symbols Better | 4/8 | 4/8 | Tie |
    | Conclusion | Recommended | Alternative | ✅ EMA |
    
    ➜ **Recommendation**: Keep EMA 10/100 strategy as default (wins by 9pp)
    """)

# Footer
st.markdown("---")
st.markdown(
    "📱 **S&P 500 Trading Bot v2** | Live Trading: Top 8 + SPX Index | "
    "[GitHub](https://github.com/LKarolek123/sp500_agent)"
)
