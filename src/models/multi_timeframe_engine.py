"""
Multi-Timeframe Strategy Engine

Combines signals from multiple EMA periods with different combination methods.

Timeframe Configurations:
- Fast (TF1):   MA10/MA25 EMA crossover   → Quick entries, volatile
- Medium (TF2): MA20/MA50 EMA crossover   → Baseline (original strategy)
- Slow (TF3):   MA50/MA100 EMA crossover  → Stable trends, fewer signals

Combination Methods:
1. Majority Vote:  ≥2/3 timeframes agree → Trade
2. Consensus:      All 3 timeframes agree → Most conservative
3. Weighted:       Fast=30%, Med=50%, Slow=20% confidence weighting
4. Strict Align:   All 3 aligned + volume confirmation → Rarest, highest conviction
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, List


class MultiTimeframeEngine:
    """Generate and combine MA crossover signals from multiple timeframes."""
    
    def __init__(self, use_volume_filter: bool = True):
        """
        Initialize multi-timeframe engine.
        
        Args:
            use_volume_filter: Apply volume confirmation for strict alignment method
        """
        self.use_volume_filter = use_volume_filter
        self.tf_configs = {
            'fast': {'fast_ma': 10, 'slow_ma': 25, 'weight': 0.3},
            'medium': {'fast_ma': 20, 'slow_ma': 50, 'weight': 0.5},
            'slow': {'fast_ma': 50, 'slow_ma': 100, 'weight': 0.2}
        }
    
    def generate_ma_signal(self, df: pd.DataFrame, fast_ma: int, slow_ma: int) -> pd.Series:
        """
        Generate MA crossover signal for given periods.
        
        Returns:
            Series with values 1 (bullish), -1 (bearish), 0 (neutral)
        """
        df = df.copy()
        ema_fast = df['Close'].ewm(span=fast_ma, adjust=False).mean()
        ema_slow = df['Close'].ewm(span=slow_ma, adjust=False).mean()
        
        signal = np.where(ema_fast > ema_slow, 1,
                         np.where(ema_fast < ema_slow, -1, 0))
        return pd.Series(signal, index=df.index, dtype=int)
    
    def generate_all_timeframes(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Generate signals for all three timeframes."""
        signals = {}
        for tf_name, config in self.tf_configs.items():
            signal = self.generate_ma_signal(
                df,
                fast_ma=config['fast_ma'],
                slow_ma=config['slow_ma']
            )
            signals[tf_name] = signal
            
        return signals
    
    def combine_majority_vote(self, signals: Dict[str, pd.Series]) -> pd.Series:
        """
        Majority Vote: ≥2/3 timeframes agree → Trade
        
        If 2+ timeframes show same direction, generate signal.
        Otherwise, stay neutral.
        """
        fast = signals['fast'].values
        medium = signals['medium'].values
        slow = signals['slow'].values
        
        combined = np.zeros(len(fast))
        
        # Count agreement
        for i in range(len(fast)):
            votes_bull = (fast[i] == 1) + (medium[i] == 1) + (slow[i] == 1)
            votes_bear = (fast[i] == -1) + (medium[i] == -1) + (slow[i] == -1)
            
            if votes_bull >= 2:
                combined[i] = 1
            elif votes_bear >= 2:
                combined[i] = -1
            else:
                combined[i] = 0
        
        return pd.Series(combined, index=signals['fast'].index, dtype=int)
    
    def combine_consensus(self, signals: Dict[str, pd.Series]) -> pd.Series:
        """
        Consensus: All 3 timeframes must agree → Most conservative
        
        Only generates signal when all timeframes align.
        Rare but highest conviction signals.
        """
        fast = signals['fast'].values
        medium = signals['medium'].values
        slow = signals['slow'].values
        
        combined = np.zeros(len(fast))
        
        for i in range(len(fast)):
            if fast[i] == medium[i] == slow[i] and fast[i] != 0:
                combined[i] = fast[i]
            else:
                combined[i] = 0
        
        return pd.Series(combined, index=signals['fast'].index, dtype=int)
    
    def combine_weighted(self, signals: Dict[str, pd.Series]) -> pd.Series:
        """
        Weighted: Confidence-based combination with weights
        
        Returns weighted combination:
        - Fast: 30% weight (responsive but noisy)
        - Medium: 50% weight (baseline, balanced)
        - Slow: 20% weight (stable, filtering)
        
        Thresholds:
        - Bull: weighted_sum >= 0.5 → signal 1
        - Bear: weighted_sum <= -0.5 → signal -1
        - Neutral: -0.5 < weighted_sum < 0.5 → signal 0
        """
        fast = signals['fast'].values * self.tf_configs['fast']['weight']
        medium = signals['medium'].values * self.tf_configs['medium']['weight']
        slow = signals['slow'].values * self.tf_configs['slow']['weight']
        
        weighted_sum = fast + medium + slow
        
        combined = np.where(weighted_sum >= 0.5, 1,
                           np.where(weighted_sum <= -0.5, -1, 0))
        
        return pd.Series(combined, index=signals['fast'].index, dtype=int)
    
    def combine_strict_alignment(self, df: pd.DataFrame, 
                                  signals: Dict[str, pd.Series]) -> pd.Series:
        """
        Strict Alignment: All 3 aligned + volume confirmation
        
        Only trades when:
        1. All 3 timeframes agree on direction
        2. Volume is above 20-period average (if volume_filter enabled)
        3. Creates rarest but most reliable signals
        """
        fast = signals['fast'].values
        medium = signals['medium'].values
        slow = signals['slow'].values
        
        combined = np.zeros(len(fast))
        
        # Calculate volume filter if enabled
        if self.use_volume_filter and 'Volume' in df.columns:
            vol_avg = df['Volume'].rolling(20).mean().values
            current_vol = df['Volume'].values
            vol_ratio = np.divide(current_vol, vol_avg, where=vol_avg > 0, 
                                 out=np.ones_like(vol_avg))
        else:
            vol_ratio = np.ones(len(fast))
        
        for i in range(len(fast)):
            # All must align and volume above average
            if (fast[i] == medium[i] == slow[i] and 
                fast[i] != 0 and 
                vol_ratio[i] >= 1.0):
                combined[i] = fast[i]
            else:
                combined[i] = 0
        
        return pd.Series(combined, index=signals['fast'].index, dtype=int)
    
    def run_all_methods(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        Generate signals using all 4 combination methods.
        
        Returns:
            Dictionary with keys: 'majority', 'consensus', 'weighted', 'strict'
        """
        # Generate base signals
        signals = self.generate_all_timeframes(df)
        
        # Combine using all methods
        combined = {
            'majority': self.combine_majority_vote(signals),
            'consensus': self.combine_consensus(signals),
            'weighted': self.combine_weighted(signals),
            'strict': self.combine_strict_alignment(df, signals)
        }
        
        return combined
    
    @staticmethod
    def get_signal_statistics(signals: Dict[str, pd.Series]) -> Dict:
        """Get statistics on signal generation for each method."""
        stats = {}
        for method_name, signal_series in signals.items():
            bullish = (signal_series == 1).sum()
            bearish = (signal_series == -1).sum()
            total = bullish + bearish
            
            stats[method_name] = {
                'bullish_signals': int(bullish),
                'bearish_signals': int(bearish),
                'total_signals': int(total),
                'bullish_pct': float(bullish / max(total, 1) * 100),
                'bearish_pct': float(bearish / max(total, 1) * 100)
            }
        
        return stats
    
    @staticmethod
    def compare_signals(signals: Dict[str, pd.Series]) -> pd.DataFrame:
        """
        Create comparison table showing signals across all methods.
        
        Useful for understanding how methods differ.
        """
        comparison = pd.DataFrame(signals)
        return comparison


def demonstrate_multi_timeframe():
    """Demonstration of multi-timeframe engine."""
    print("Multi-Timeframe Strategy Engine")
    print("=" * 60)
    
    # Create sample data
    dates = pd.date_range('2020-01-01', periods=500, freq='D')
    price = 100 + np.cumsum(np.random.randn(500) * 2)
    volume = np.random.uniform(1000000, 5000000, 500)
    
    df = pd.DataFrame({
        'Close': price,
        'Volume': volume,
        'High': price + np.abs(np.random.randn(500)),
        'Low': price - np.abs(np.random.randn(500))
    }, index=dates)
    
    # Create engine and run
    engine = MultiTimeframeEngine(use_volume_filter=True)
    signals = engine.run_all_methods(df)
    
    # Print statistics
    stats = engine.get_signal_statistics(signals)
    print("\nSignal Statistics:")
    for method, stat in stats.items():
        print(f"\n{method.upper()}:")
        print(f"  Bullish:  {stat['bullish_signals']:3d} ({stat['bullish_pct']:5.1f}%)")
        print(f"  Bearish:  {stat['bearish_signals']:3d} ({stat['bearish_pct']:5.1f}%)")
        print(f"  Total:    {stat['total_signals']:3d}")
    
    # Show sample signals
    print("\n" + "=" * 60)
    print("Sample Signals (last 10 bars):")
    print("=" * 60)
    sample = df.tail(10).copy()
    sample['majority'] = signals['majority'].tail(10).values
    sample['consensus'] = signals['consensus'].tail(10).values
    sample['weighted'] = signals['weighted'].tail(10).values
    sample['strict'] = signals['strict'].tail(10).values
    
    print(sample[['Close', 'majority', 'consensus', 'weighted', 'strict']].to_string())


if __name__ == '__main__':
    demonstrate_multi_timeframe()
