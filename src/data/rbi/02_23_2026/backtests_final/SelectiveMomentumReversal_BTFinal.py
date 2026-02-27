import pandas as pd
import talib
import numpy as np
from backtesting import Strategy, Backtest

class SelectiveMomentumReversal(Strategy):
    rsi_overbought = 75
    rsi_oversold = 25
    atr_multiplier = 2
    risk_pct = 0.02
    volume_multiplier = 1.5
    pivot_period = 20

    def init(self):
        self.rsi = self.I(talib.RSI, self.data.Close, timeperiod=14)
        self.pivot_high = self.I(talib.MAX, self.data.High, timeperiod=self.pivot_period)
        self.pivot_low = self.I(talib.MIN, self.data.Low, timeperiod=self.pivot_period)
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, timeperiod=14)
        self.avg_volume = self.I(talib.SMA, self.data.Volume, timeperiod=10)

    def next(self):
        if len(self.data.Close) < self.pivot_period + 2:
            return

        curr_close = self.data.Close[-1]
        curr_rsi = self.rsi[-1]
        prev_rsi = self.rsi[-2]
        curr_atr = self.atr[-1]
        curr_vol = self.data.Volume[-1]
        avg_vol = self.avg_volume[-1]

        if any(np.isnan([curr_rsi, prev_rsi, curr_atr, avg_vol])):
            return

        volume_ok = curr_vol > self.volume_multiplier * avg_vol

        if not self.position:
            # Long: RSI crosses up from oversold + price near support
            if prev_rsi < self.rsi_oversold and curr_rsi >= self.rsi_oversold:
                if curr_close <= self.pivot_low[-1] * 1.01 and volume_ok:
                    sl = curr_close - self.atr_multiplier * curr_atr
                    risk = curr_close - sl
                    if risk > 0:
                        size = int((self.equity * self.risk_pct) / risk)
                        max_size = int(self.equity * 0.95 / curr_close)
                        size = min(size, max_size)
                        if size > 0:
                            self.buy(size=size, sl=sl)
                            print(f"🌙 LONG at {curr_close:.2f} SL={sl:.2f} size={size}")

            # Short: RSI crosses down from overbought + price near resistance
            elif prev_rsi > self.rsi_overbought and curr_rsi <= self.rsi_overbought:
                if curr_close >= self.pivot_high[-1] * 0.99 and volume_ok:
                    sl = curr_close + self.atr_multiplier * curr_atr
                    risk = sl - curr_close
                    if risk > 0:
                        size = int((self.equity * self.risk_pct) / risk)
                        max_size = int(self.equity * 0.95 / curr_close)
                        size = min(size, max_size)
                        if size > 0:
                            self.sell(size=size, sl=sl)
                            print(f"✨ SHORT at {curr_close:.2f} SL={sl:.2f} size={size}")

        else:
            # Exit long if price drops below trailing ATR level
            if self.position.is_long:
                trail_exit = self.data.High[-1] - self.atr_multiplier * curr_atr
                if curr_close < trail_exit:
                    self.position.close()
            # Exit short if price rises above trailing ATR level
            elif self.position.is_short:
                trail_exit = self.data.Low[-1] + self.atr_multiplier * curr_atr
                if curr_close > trail_exit:
                    self.position.close()


# Load and prepare data
data = pd.read_csv(
    'F:/GitHub/moon-dev-ai-agents/moon-dev-ai-agents/src/data/rbi/BTC-USD-15m.csv',
    parse_dates=['datetime'], index_col='datetime'
)
data.columns = data.columns.str.strip().str.lower()
data = data.drop(columns=[c for c in data.columns if 'unnamed' in c.lower()], errors='ignore')
data = data.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})
data.dropna(inplace=True)

print(f"🌟 Data loaded: {len(data)} bars")

bt = Backtest(data, SelectiveMomentumReversal, cash=1_000_000, commission=0.002, exclusive_orders=True)
stats = bt.run()

print("\n--- 📈 SelectiveMomentumReversal Results ---")
print(stats)
print("\n--- 🎉 Done! ---")
