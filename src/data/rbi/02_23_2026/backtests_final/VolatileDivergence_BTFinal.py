import pandas as pd
from backtesting import Backtest, Strategy
import talib
import numpy as np
import pandas_ta as ta # 🌙 Moon Dev recommends pandas-ta for specialized indicators! ✨

# 🌙✨ Moon Dev's Package AI is loading your data... ✨🌙
try:
    # Load data
    data = pd.read_csv('F:/GitHub/moon-dev-ai-agents/moon-dev-ai-agents/src/data/rbi/BTC-USD-15m.csv', parse_dates=['datetime'])
    print("🌙 Data loaded successfully! Initiating Moon Dev's cleansing process... 🧹")
except FileNotFoundError:
    print("🚨 Moon Dev Error: Data file not found at 'F:/GitHub/moon-dev-ai-agents/moon-dev-ai-agents/src/data/rbi/BTC-USD-15m.csv'. Please ensure the path is correct. 🚀")
    exit() # Exit if data cannot be loaded

# Clean column names
data.columns = data.columns.str.strip().str.lower()
print("🌙 Column names are sparkling clean! ✨")

# Drop any unnamed columns
data = data.drop(columns=[col for col in data.columns if 'unnamed' in col.lower()], errors='ignore')
print("🌙 Unnamed columns banished to the void! 🌌")

# Ensure proper column mapping
data = data.rename(columns={
    'open