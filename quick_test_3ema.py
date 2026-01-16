"""
Quick Single-Stock Test for 3EMA + BX Trender
Fast validation of strategy logic
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project to path
sys.path.insert(0, 'c:\\Users\\karol\\OneDrive\\Desktop\\habits\\sp500_agent')

from src.strategy.strategy_engine import StrategyEngine, SignalType
from src.backtest.backtest_engine import DataLoader


def quick_test():
    """Run quick test on TSLA data"""
    
    print("="*70)
    print("QUICK TEST: 3EMA + BX Trender on TSLA")
    print("="*70)
    
    try:
        # Load 3 months of data
        loader = DataLoader()
        print("\n1. Loading TSLA data (last 3 months)...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        df = loader.load_data("TSLA", start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), interval="1h")
        
        if len(df) < 200:
            print(f"❌ Not enough data: {len(df)} candles (need 200+)")
            return False
        
        print(f"✅ Loaded {len(df)} hourly candles")
        
        # Test strategy
        print("\n2. Testing strategy engine...")
        strategy = StrategyEngine()
        
        # Sample test on a few candles
        signals_found = 0
        last_signals = []
        
        for idx in range(200, min(300, len(df))):
            signal = strategy.generate_signal(df, idx)
            if signal:
                signals_found += 1
                last_signals.append({
                    "idx": idx,
                    "time": df.index[idx],
                    "type": signal.signal_type.value,
                    "price": signal.price,
                    "ema_21": signal.ema_21,
                    "ema_89": signal.ema_89,
                    "ema_200": signal.ema_200
                })
        
        print(f"✅ Strategy engine working")
        print(f"   Found {signals_found} signals in first 100 candles")
        
        if last_signals:
            print(f"\n3. Sample Signals:")
            for sig in last_signals[:3]:
                print(f"   [{sig['time']}] {sig['type']}: ${sig['price']:.2f}")
                print(f"      EMA: {sig['ema_21']:.2f} / {sig['ema_89']:.2f} / {sig['ema_200']:.2f}")
        
        print("\n✅ Quick test PASSED - Strategy engine is working!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = quick_test()
    sys.exit(0 if success else 1)
