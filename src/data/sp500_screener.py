"""
S&P 500 Stock Screener

Fetches top N stocks from S&P 500 by market cap or liquidity.
Can filter by volume, spread, and other criteria.

Usage:
    python src/data/sp500_screener.py --top 20 --min-volume 1000000
"""
import sys
import pandas as pd
from pathlib import Path
from typing import List, Dict

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    print("Warning: yfinance not installed. Use --use-cached for hardcoded list.")


def get_sp500_tickers() -> List[str]:
    """Get list of S&P 500 tickers from Wikipedia."""
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        sp500_table = tables[0]
        tickers = sp500_table["Symbol"].tolist()
        # Clean tickers (replace . with -)
        tickers = [t.replace(".", "-") for t in tickers]
        return tickers
    except Exception as e:
        print(f"Error fetching S&P 500 list: {e}")
        return []


def get_top_stocks_by_market_cap(tickers: List[str], top_n: int = 20) -> List[Dict]:
    """
    Get top N stocks by market capitalization.
    
    Returns:
        List of dicts with {symbol, market_cap, volume, name}
    """
    if not HAS_YFINANCE:
        raise ImportError("yfinance not installed. Use --use-cached or install: pip install yfinance")
    
    print(f"Fetching data for {len(tickers)} tickers...")
    stocks_data = []
    
    for i, ticker in enumerate(tickers):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            market_cap = info.get("marketCap", 0)
            volume = info.get("averageVolume", 0) or info.get("volume", 0)
            name = info.get("shortName", ticker)
            
            if market_cap and volume:
                stocks_data.append({
                    "symbol": ticker,
                    "market_cap": market_cap,
                    "volume": volume,
                    "name": name
                })
            
            if (i + 1) % 50 == 0:
                print(f"  Processed {i + 1}/{len(tickers)}...")
                
        except Exception as e:
            print(f"  Error for {ticker}: {e}")
            continue
    
    # Sort by market cap descending
    stocks_data.sort(key=lambda x: x["market_cap"], reverse=True)
    
    return stocks_data[:top_n]


def filter_by_liquidity(stocks: List[Dict], min_volume: int = 1_000_000) -> List[Dict]:
    """Filter stocks by minimum average volume."""
    return [s for s in stocks if s["volume"] >= min_volume]


def save_to_json(stocks: List[Dict], filepath: Path):
    """Save screened stocks to JSON file."""
    import json
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(stocks, f, indent=2)
    print(f"\n✅ Saved {len(stocks)} stocks to {filepath}")


def display_stocks(stocks: List[Dict]):
    """Pretty print stocks table."""
    df = pd.DataFrame(stocks)
    df["market_cap_b"] = df["market_cap"] / 1e9
    df["volume_m"] = df["volume"] / 1e6
    
    print("\n" + "=" * 80)
    print(f"TOP {len(stocks)} STOCKS BY MARKET CAP")
    print("=" * 80)
    print(df[["symbol", "name", "market_cap_b", "volume_m"]].to_string(index=False))
    print("=" * 80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Screen S&P 500 stocks")
    parser.add_argument("--top", type=int, default=20, help="Number of top stocks")
    parser.add_argument("--min-volume", type=int, default=1_000_000, help="Min avg volume")
    parser.add_argument("--output", default="config/top_stocks.json", help="Output JSON file")
    parser.add_argument("--use-cached", action="store_true", help="Use hardcoded top 20 (fast)")
    args = parser.parse_args()
    
    # Option 1: Fast hardcoded top 20 (by market cap as of 2024)
    if args.use_cached:
        top_stocks = [
            {"symbol": "AAPL", "name": "Apple Inc.", "market_cap": 3000000000000, "volume": 50000000},
            {"symbol": "MSFT", "name": "Microsoft Corporation", "market_cap": 2800000000000, "volume": 25000000},
            {"symbol": "GOOGL", "name": "Alphabet Inc.", "market_cap": 1700000000000, "volume": 20000000},
            {"symbol": "AMZN", "name": "Amazon.com Inc.", "market_cap": 1500000000000, "volume": 40000000},
            {"symbol": "NVDA", "name": "NVIDIA Corporation", "market_cap": 1400000000000, "volume": 45000000},
            {"symbol": "META", "name": "Meta Platforms Inc.", "market_cap": 900000000000, "volume": 15000000},
            {"symbol": "TSLA", "name": "Tesla Inc.", "market_cap": 800000000000, "volume": 100000000},
            {"symbol": "BRK-B", "name": "Berkshire Hathaway Inc.", "market_cap": 780000000000, "volume": 3000000},
            {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "market_cap": 500000000000, "volume": 10000000},
            {"symbol": "V", "name": "Visa Inc.", "market_cap": 480000000000, "volume": 7000000},
            {"symbol": "UNH", "name": "UnitedHealth Group Inc.", "market_cap": 450000000000, "volume": 3000000},
            {"symbol": "XOM", "name": "Exxon Mobil Corporation", "market_cap": 440000000000, "volume": 20000000},
            {"symbol": "JNJ", "name": "Johnson & Johnson", "market_cap": 380000000000, "volume": 6000000},
            {"symbol": "WMT", "name": "Walmart Inc.", "market_cap": 370000000000, "volume": 8000000},
            {"symbol": "MA", "name": "Mastercard Inc.", "market_cap": 360000000000, "volume": 3000000},
            {"symbol": "PG", "name": "Procter & Gamble Co.", "market_cap": 350000000000, "volume": 7000000},
            {"symbol": "HD", "name": "The Home Depot Inc.", "market_cap": 330000000000, "volume": 3000000},
            {"symbol": "CVX", "name": "Chevron Corporation", "market_cap": 280000000000, "volume": 8000000},
            {"symbol": "ABBV", "name": "AbbVie Inc.", "market_cap": 270000000000, "volume": 6000000},
            {"symbol": "COST", "name": "Costco Wholesale Corp.", "market_cap": 260000000000, "volume": 2000000},
        ]
        print("✅ Using cached top 20 stocks (fast mode)")
    else:
        # Option 2: Fetch live from yfinance (slow, ~5-10 min)
        tickers = get_sp500_tickers()
        if not tickers:
            print("❌ Failed to fetch S&P 500 tickers")
            sys.exit(1)
        
        print(f"Found {len(tickers)} S&P 500 tickers")
        top_stocks = get_top_stocks_by_market_cap(tickers, top_n=args.top)
        top_stocks = filter_by_liquidity(top_stocks, min_volume=args.min_volume)
    
    if not top_stocks:
        print("❌ No stocks passed screening")
        sys.exit(1)
    
    display_stocks(top_stocks)
    
    # Save to config
    output_path = Path(__file__).parent.parent.parent / args.output
    save_to_json(top_stocks, output_path)
    
    print(f"\n📋 Symbols: {', '.join([s['symbol'] for s in top_stocks])}")
