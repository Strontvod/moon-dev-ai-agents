import backtrader as bt
import talib

class AdaptiveTrendCapture(bt.Strategy):
    params = (
        ('fast_ema', 8),
        ('medium_ema', 21),
        ('slow_ema', 55),
        ('adx_threshold', 25),
        ('atr_multiplier', 3),
        ('risk_pct', 0.02),
    )

    def __init__(self):
        self.data_close = self.datas[0].close
        self.data_volume = self.datas[0].volume

        self.fast_ema = self.I(talib.EMA, self.data_close, timeperiod=self.params.fast_ema)
        self.medium_ema = self.I(talib.EMA, self.data_close, timeperiod=self.params.medium_ema)
        self.slow_ema = self.I(talib.EMA, self.data_close, timeperiod=self.params.slow_ema)
        self.adx = self.I(talib.ADX, self.data_high, self.data_low, timeperiod=14)
        self.atr = self.I(talib.ATR, self.data_high, self.data_low, self.data_close, timeperiod=14)
        self.vwap = self.I(bt.ind.VWAP)

        self.trend_direction = 0
        self.trailing_stop = None

    def next(self):
        if not self.position:
            # Check for a new trend
            if self.fast_ema > self.medium_ema > self.slow_ema and self.adx > self.params.adx_threshold:
                self.trend_direction = 1
                self.log(f'🌙 Bullish trend detected! 🚀')
            elif self.fast_ema < self.medium_ema < self.slow_ema and self.adx > self.params.adx_threshold:
                self.trend_direction = -1
                self.log(f'🌙 Bearish trend detected! 🔻')
            else:
                self.trend_direction = 0

            # Enter the market
            if self.trend_direction != 0 and self.data_close < self.medium_ema:
                self.buy_size = int(round(self.broker.cash * self.params.risk_pct / self.atr))
                self.buy(size=self.buy_size)
                self.trailing_stop = self.data_close - self.params.atr_multiplier * self.atr
                self.log(f'🌙 Entered the market! 💰 Size: {self.buy_size}')

        else:
            # Update the trailing stop
            if self.trend_direction == 1 and self.data_close > self.vwap:
                self.trailing_stop = max(self.trailing_stop, self.data_close - self.params.atr_multiplier * self.atr)
            elif self.trend_direction == -1 and self.data_close < self.vwap:
                self.trailing_stop = min(self.trailing_stop, self.data_close + self.params.atr_multiplier * self.atr)

            # Check for exit conditions
            if self.fast_ema < self.medium_ema and self.trend_direction == 1:
                self.sell()
                self.log(f'🌙 Exited the market! 🤑')
            elif self.fast_ema > self.medium_ema and self.trend_direction == -1:
                self.sell()
                self.log(f'🌙 Exited the market! 🤑')
            elif self.data_close <= self.trailing_stop:
                self.sell()
                self.log(f'🌙 Stopped out! 💔')

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')

if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(AdaptiveTrendCapture)

    data = bt.feeds.GenericCSVData(
        dataname='F:/GitHub/moon-dev-ai-agents/moon-dev-ai-agents/src/data/rbi/BTC-USD-15m.csv',
        datetime=0,
        open=1,
        high=2,
        low=3,
        close=4,
        volume=5,
        dtformat='%Y-%m-%d %H:%M:%S',
        timeframe=bt.TimeFrame.Minutes,
        compression=15,
        nullvalue=0.0
    )

    cerebro.adddata(data)
    cerebro.broker.setcash(1000000.0)
    cerebro.run()
    stats = cerebro.run()
    print(stats)
    print(stats[0])