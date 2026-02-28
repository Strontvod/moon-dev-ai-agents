"""
Moon Dev's Base Strategy Class
All custom strategies should inherit from this or implement the same interface.
"""

import pandas as pd


class BaseStrategy:
    def __init__(self, name: str = "BaseStrategy"):
        self.name = name

    def analyze(self, df: pd.DataFrame, token: str = "BTC") -> dict:
        """Analyze OHLCV data and return a trading signal.

        Args:
            df: DataFrame with columns [open, high, low, close, volume], datetime index.
            token: Symbol string (e.g., "BTC", "ETH", "SOL").

        Returns:
            dict: {
                'token': str,          # Same as input token
                'signal': float,       # Signal strength (0.0 - 1.0)
                'direction': str,      # 'BUY', 'SELL', or 'NEUTRAL'
                'metadata': dict       # Optional strategy-specific data
            }
        """
        raise NotImplementedError("Strategy must implement analyze(df, token)")
