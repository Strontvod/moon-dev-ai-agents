import backtrader as bt
import talib
import pandas_ta as ta

class AdaptiveDivergenceVolatility(bt.Strategy):
    params = (
        ('macd_fast', 12),
        ('macd_slow', 26),
        ('macd_signal', 9),
        ('bb_period', 20),
        ('bb_devfactor', 2),
        ('atr_period', 14),
        ('risk_pct', 0.02),
    )

    def __init__(self):
        self.macd, self.macd_signal, self.macd_hist = self.I(talib.MACD, self.data.Close, fastperiod=self.params.macd_fast, slowperiod=self.params.macd_slow, signalperiod=self.params.macd_signal)
        self.bb_mid, self.bb_top, self.bb_bottom = self.I(talib.BBANDS, self.data.Close, timeperiod=self.params.bb_period, nbdevup=self.params.bb_devfactor, nbdevdn=self.params.bb_devfactor)
        self.atr = self.I(talib.ATR, self.data, timeperiod=self.params.atr_period)

        self.cross_above = (self.macd_hist[-2] < 0) & (self.macd_hist[-1] > 0)
        self.cross_below = (self.macd_hist[-2] > 0) & (self.macd_hist[-1] < 0)

        self.buy_signal = (self.cross_above) & (self.data.Volume > self.data.Volume.rolling(20).mean())
        self.sell_signal = (self.cross_below) & (self.data.Volume > self.data.Volume.rolling(20).mean())

    def next(self):
        if not self.position:
            if self.buy_signal:
                size = self.get_position_size()
                self.buy_bracket(
                    size=size,
                    exectype=bt.Order.Market,
                    stopprice=self.data.Close - 2 * self.atr[0],
                    limitprice=self.data.Close + 2 * self.atr[0]
                )
                print(f"🌙 Entering long position on {self.data.datetime.date(0)} with size {size} 🚀")
            elif self.sell_signal:
                size = self.get_position_size()
                self.sell_bracket(
                    size=size,
                    exectype=bt.Order.Market,
                    stopprice=self.data.Close + 2 * self.atr[0],
                    limitprice=self.data.Close - 2 * self.atr[0]
                )
                print(f"🌙 Entering short position on {self.data.datetime.date(0)} with size {size} 🔥")
        else:
            if self.macd_hist[-2] > 0 and self.macd_hist[-1] < 0 or self.atr[0] > self.atr.mean():
                self.close()
                print(f"✨ Exiting position on {self.data.datetime.date(0)} 💫")

    def get_position_size(self):
        risk_amount = self.broker.getvalue() * self.params.risk_pct
        atr = self.atr[0]
        position_size = int(round(risk_amount / atr))
        return position_size

cerebro = bt.Cerebro(stdstats=False)
cerebro.addstrategy(AdaptiveDivergenceVolatility)

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
    compression=15
)

cerebro.adddata(data)
cerebro.broker.setcash(1000000.0)
cerebro.run()
stats = cerebro.run()
print(stats)
print(stats[0]._strategy)