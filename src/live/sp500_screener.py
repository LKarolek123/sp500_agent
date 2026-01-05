"""
S&P 500 screener - zwraca top 18 spółek + indeks rynkowy (SPX).

Top 18 by market cap:
1. MSFT, AAPL, NVDA, GOOGL, AMZN, META, TSLA, BRK.B, JNJ, V, WMT, JPM, PG, XOM, MA, HD, PFE, DIS

+ SPX (S&P 500 index) dla referencji rynkowej.
"""


def get_sp500_symbols():
    """Zwraca listę 18 top spółek + SPX."""
    return [
        # Top 18 by market cap
        "MSFT",  # Microsoft
        "AAPL",  # Apple
        "NVDA",  # NVIDIA
        "GOOGL",  # Alphabet
        "AMZN",  # Amazon
        "META",  # Meta
        "TSLA",  # Tesla
        "BRK.B",  # Berkshire Hathaway B
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
        # Index reference
        "SPX",  # S&P 500 (index, no trading)
    ]


if __name__ == "__main__":
    symbols = get_sp500_symbols()
    print(f"📊 S&P 500 Top 18 + Market Index ({len(symbols)} symbols)")
    for i, sym in enumerate(symbols, 1):
        print(f"  {i:2d}. {sym}")
