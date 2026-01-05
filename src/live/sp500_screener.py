"""
S&P 500 screener - zwraca top 18 spółek + indeks rynkowy (SPX).

Top 18 by market cap (bez BRK.B - problematyczne w yfinance):
1. MSFT, AAPL, NVDA, GOOGL, AMZN, META, TSLA, JNJ, V, WMT, JPM, PG, XOM, MA, HD, PFE, DIS, LLY

+ SPX (S&P 500 index) dla referencji rynkowej.
"""


def get_sp500_symbols():
    """Zwraca listę 18 top spółek + SPX."""
    return [
        # Top 18 by market cap (bez BRK.B)
        "MSFT",  # Microsoft
        "AAPL",  # Apple
        "NVDA",  # NVIDIA
        "GOOGL",  # Alphabet
        "AMZN",  # Amazon
        "META",  # Meta
        "TSLA",  # Tesla
        "JNJ",  # Johnson & Johnson
        "V",  # Visa
        "WMT",  # Walmart
        "JPM",  # JPMorgan
        "PG",  # Procter & Gamble
        "XOM",  # ExxonMobil
        "MA",  # Mastercard
        "HD",  # Home Depot
        "PFE",  # Pfizer
        "DIS",  # Disney
        "LLY",  # Eli Lilly
        # Index reference
        "SPX",  # S&P 500 (index, no trading)
    ]


def get_profitable_8_symbols():
    """
    Zwraca 8 spółek, które najlepiej działają z strategią EMA 10/100 (TP=6%, SL=3%).
    Backtest na 2 latach pokazał dodatni P&L dla tych symboli.
    """
    return [
        "TSLA",   # +30.87% (83.3% WR, 6 trades) - GWIAZDA
        "DIS",    # +14.95% (50.0% WR, 8 trades)
        "GOOGL",  # +14.10% (50.0% WR, 8 trades)
        "JNJ",    # +11.37% (40.0% WR, 10 trades)
        "JPM",    # +7.97%  (50.0% WR, 4 trades)
        "LLY",    # +6.88%  (40.0% WR, 10 trades)
        "META",   # +4.92%  (33.3% WR, 6 trades)
        "AMZN",   # +1.20%  (37.5% WR, 8 trades)
    ]


if __name__ == "__main__":
    symbols = get_sp500_symbols()
    print(f"S&P 500 Top 18 + Market Index ({len(symbols)} symbols)")
    for i, sym in enumerate(symbols, 1):
        print(f"  {i:2d}. {sym}")
    
    print(f"\nTop 8 Profitable Symbols (EMA 10/100, TP=6%, SL=3%):")
    profitable = get_profitable_8_symbols()
    for i, sym in enumerate(profitable, 1):
        print(f"  {i}. {sym}")
