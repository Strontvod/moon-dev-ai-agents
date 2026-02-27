import pandas as pd
from backtesting import Backtest, Strategy
import talib
import numpy as np

# Load data
data = pd.read_csv('F:/GitHub/moon-dev-ai-agents/moon-dev-ai-agents/src/data/rbi/BTC-USD-15m.csv', parse_dates=['datetime'])

# Clean column names
data.columns = data.columns.str.strip().str.lower()

# Drop any unnamed columns
data = data.drop(columns=[col for col in data.columns if 'unnamed' in col.lower()], errors='ignore')

# Ensure proper column mapping
data = data.rename(columns={
    'open': 'Open',
    'high': 'High',
    'low': 'Low',
    'close': 'Close',
    'volume': 'Volume'
})

data.set_index('datetime', inplace=True)
data = data.sort_index()

class VolatileDivergence(Strategy):
    # Strategy parameters
    macd_fastperiod = 12
    macd_slowperiod = 26
    macd_signalperiod = 9
    bb_period = 20
    bb_dev = 2.0
    atr_period = 14
    divergence_period = 10 # Lookback for simple divergence check (current vs. X bars ago)
    volume_ma_period = 20
    bb_