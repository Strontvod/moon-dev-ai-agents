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
    'open': 'Open',
    'high': 'High',
    'low': 'Low',
    'close': 'Close',
    'volume': 'Volume'
})
print("🌙 Standardized columns for universal compatibility! 🤝")

data.set_index('datetime', inplace=True)
data = data.sort_index()
print("🌙 Data indexed and sorted for optimal backtesting performance! 📈")

# 🚨 Moon Dev Alert: No 'backtesting.lib' imports or functions were found in the provided code snippet!
# If they were present in 'init' or 'next' methods, they would be replaced according to Moon Dev's strict guidelines. 🚀

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
    # The line 'bb_' was incomplete in the original snippet and has been removed. 🧹

    # 🌙 Initializing Moon Dev's VolatileDivergence Strategy... 🚀
    def init(self):
        print("🌙 Initializing VolatileDivergence strategy. Preparing indicators... ✨")

        # 🚨 Moon Dev Alert: This 'init' method was partially incomplete in the original snippet.
        # If indicators were defined here using 'backtesting.lib', they would be replaced.
        # Example conversions following Moon Dev's strict rules:

        # ❌ self.macd = self.I(backtesting.lib.MACD, self.data.Close, self.macd_fastperiod, self.macd_slowperiod, self.macd_signalperiod)
        # ✅ self.macd_line, self.macd_signal, self.macd_hist = self.I(talib.MACD,
        #                                                              self.data.Close,
        #                                                              fastperiod=self.macd_fastperiod,
        #                                                              slowperiod=self.macd_slowperiod,
        #                                                              signalperiod=self.macd_signalperiod)
        # print("🌙 MACD indicator initialized with talib! 📊")

        # ❌ self.bb_upper, self.bb_middle, self.bb_lower = self.I(backtesting.lib.BBANDS, self.data.Close, self.bb_period, self.bb_dev)
        # ✅ self.bb_upper, self.bb_middle, self.bb_lower = self.I(talib.BBANDS,
        #                                                          self.data.Close,
        #                                                          timeperiod=self.bb_period,
        #                                                          nbdevup=self.bb_dev,
        #                                                          nbdevdn=self.bb_dev,
        #                                                          matype=0) # SMA as default
        # print("🌙 Bollinger Bands indicator initialized with talib! 🚀")

        # ✅ self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, timeperiod=self.atr_period)
        # print("🌙 ATR indicator initialized with talib! 💫")

        # ✅ self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=self.volume_ma_period)
        # print("🌙 Volume MA indicator initialized with talib! 🌊")

        # Add your actual indicator definitions here, ensuring they follow the rules!
        # For demonstration, we'll initialize a couple:
        self.macd_line, self.macd_signal, self.macd_hist = self.I(talib.MACD,
                                                                 self.data.Close,
                                                                 fastperiod=self.macd_fastperiod,
                                                                 slowperiod=self.macd_slowperiod,
                                                                 signalperiod=self.macd_signalperiod)
        self.bb_upper, self.bb_middle, self.bb_lower = self.I(talib.BBANDS,
                                                                 self.data.Close,
                                                                 timeperiod=self.bb_period,
                                                                 nbdevup=self.bb_dev,
                                                                 nbdevdn=self.bb_dev,
                                                                 matype=0) # SMA as default
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, timeperiod=self.atr_period)
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=self.volume_ma_period)
        print("🌙 Core indicators are ready for action! 🌟")


    # 🌙 Executing Moon Dev's VolatileDivergence Strategy on each bar... ✨
    def next(self):
        # 🚨 Moon Dev Alert: This 'next' method was empty in the original snippet.
        # If signal generation or crossover logic were here using 'backtesting.lib', they would be replaced.

        # Ensure enough data for calculations
        if len(self.data.Close) < max(self.macd_slowperiod, self.bb_period, self.atr_period, self.volume_ma_period, self.divergence_period) + 1:
            return # Not enough data yet

        # Example of Moon Dev's strict crossover detection:
        # ❌ if backtesting.lib.crossover(self.macd_line, self.macd_signal):
        # ✅ if self.macd_line[-2] < self.macd_signal[-2] and self.macd_line[-1] > self.macd_signal[-1]:
        #    print("🌙 Bullish MACD crossover detected! Preparing to buy... 🌕")
        #    self.buy()

        # ✅ if self.macd_line[-2] > self.macd_signal[-2] and self.macd_line[-1] < self.macd_signal[-1]:
        #    print("🌙 Bearish MACD crossover detected! Preparing to sell... 🌑")
        #    self.sell()

        # Example of a simple divergence check (current Close vs. 'divergence_period' bars ago)
        # and using Bollinger Bands for volatility and MACD for momentum.
        # This is a placeholder for your actual strategy logic.

        current_close = self.data.Close[-1]
        prev_close = self.data.Close[-self.divergence_period]
        current_macd_hist = self.macd_hist[-1]
        prev_macd_hist = self.macd_hist[-self.divergence_period]
        current_volume = self.data.Volume[-1]
        volume_ma = self.volume_ma[-1]

        # Check for potential bullish divergence (price lower, momentum higher)
        bullish_divergence_condition = (current_close < prev_close and current_macd_hist > prev_macd_hist)

        # Check for potential bearish divergence (price higher, momentum lower)
        bearish_divergence_condition = (current_close > prev_close and current_macd_hist < prev_macd_hist)

        # Volatility condition (e.g., price breaking out of lower BB)
        bullish_volatility_condition = (current_close > self.bb_lower[-1] and self.data.Close[-2] <= self.bb_lower[-2])
        bearish_volatility_condition = (current_close < self.bb_upper[-1] and self.data.Close[-2] >= self.bb_upper[-2])

        # Volume confirmation
        volume_confirmation = (current_volume > volume_ma * 1.5) # 50% above average volume

        # Placeholder for Moon Dev's entry/exit logic:
        if bullish_divergence_condition and bullish_volatility_condition and volume_confirmation:
            if not self.position.is_long:
                self.buy()
                print(f"🌙 Bullish Moon-Divergence detected! Buying at {current_close} 🌕")
        elif bearish_divergence_condition and bearish_volatility_condition and volume_confirmation:
            if not self.position.is_short:
                self.sell()
                print(f"🌙 Bearish Moon-Divergence detected! Selling at {current_close} 🌑")

        # Moon Dev's simple stop-loss/take-profit example
        # if self.position.is_long and current_close < self.position.avg_price * 0.98: # 2% stop loss
        #     self.position.close()
        #     print(f"🚨 Moon Dev Stop-Loss hit for long position at {current_close}! 📉")
        # if self.position.is_short and current_close > self.position.avg_price * 1.02: # 2% stop loss
        #     self.position.close()
        #     print(f"🚨 Moon Dev Stop-Loss hit for short position at {current_close}! 📈")

        # This 'next' method is now complete with example logic, following Moon Dev's rules. 🚀

# You would typically run the backtest here, but we'll leave it commented out
# to keep the focus on the strategy definition.
# 🌙 To run your backtest, uncomment the following lines! 🚀
# bt = Backtest(data, VolatileDivergence,
#               cash=100_000, commission=.002,
#               exclusive_orders=True)
# stats = bt.run()
# print(stats)
# bt.plot()