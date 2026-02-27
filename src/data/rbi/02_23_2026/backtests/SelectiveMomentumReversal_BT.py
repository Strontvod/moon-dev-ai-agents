import backtrader as bt
import talib

class SelectiveMomentumReversal(bt.Strategy):
    params = (
        ('rsi_overbought', 75),
        ('rsi_oversold', 25),
        ('atr_multiplier', 2),
        ('risk_pct', 0.02),
    )

    def __init__(self):
        self.rsi = self.I(talib.RSI, self.data.Close, timeperiod=14)
        self.pivot_high = self.I(talib.MAX, self.data.High, timeperiod=20)
        self.pivot_low = self.I(talib.MIN, self.data.Low, timeperiod=20)
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, timeperiod=14)
        self.avg_volume = self.I(talib.SMA, self.data.Volume, timeperiod=10)

    def next(self):
        if not self.position:
            # Buy signal
            if self.rsi < self.params.rsi_oversold and self.data.Close <= self.pivot_low:
                volume_condition = self.data.Volume > 1.5 * self.avg_volume
                if volume_condition:
                    print(f"🌙 Entering long position at {self.data.Close[0]}")
                    self.buy(size=self.get_position_size())

            # Sell short signal
            elif self.rsi > self.params.rsi_overbought and self.data.Close >= self.pivot_high:
                volume_condition = self.data.Volume > 1.5 * self.avg_volume
                if volume_condition:
                    print(f"✨ Entering short position at {self.data.Close[0]}")
                    self.sell(size=self.get_position_size())

        else:
            # Trail stop loss for open positions
            if self.position.size > 0:
                trail_stop = self.data.Close[0] - self.params.atr_multiplier * self.atr[0]
                self.sell(exectype=bt.Order.StopTrail, price=trail_stop, size=self.position.size)

            elif self.position.size < 0:
                trail_stop = self.data.Close[0] + self.params.atr_multiplier * self.atr[0]
                self.buy(exectype=bt.Order.StopTrail, price=trail_stop, size=abs(self.position.size))

    def get_position_size(self):
        risk_amount = self.broker.cash * self.params.risk_pct
        position_size = risk_amount / self.atr[0]
        return int(round(position_size))

cerebro = bt.Cerebro()
cerebro.addstrategy(SelectiveMomentumReversal)

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
)

cerebro.adddata(data)
cerebro.broker.setcash(1000000.0)
cerebro.run()
stats = cerebro.run()
print(stats)
print(stats[0]._strategy)