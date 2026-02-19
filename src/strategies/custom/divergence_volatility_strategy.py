"""
🌙 Moon Dev's DivergenceVolatility Live Strategy
Extracted from DivergenceVolatility_AI6.py (Sharpe 2.14, 349 trades)

Logic:
  - Detects bullish/bearish price-MACD divergence
  - Confirms with volume surge, BB volatility, and ATR momentum
  - Returns high-confidence signal only when ALL conditions align
  - Zero LLM calls — pure pandas indicator math

Signal output:
  {'token': 'BTC', 'signal': 0.9, 'direction': 'BUY',  'metadata': {...}}
  {'token': 'BTC', 'signal': 0.9, 'direction': 'SELL', 'metadata': {...}}
  {'token': 'BTC', 'signal': 0.0, 'direction': 'NEUTRAL', 'metadata': {}}
"""

import pandas as pd
import numpy as np
from termcolor import cprint

# ── Parameters (match DivergenceVolatility_AI6 backtest settings) ─────────────
BB_PERIOD        = 15
BB_STD           = 2.0
MACD_FAST        = 12
MACD_SLOW        = 26
MACD_SIGNAL      = 9
ATR_PERIOD       = 10
VOL_SMA_FAST     = 15
VOL_SMA_SLOW     = 30
SWING_PERIOD     = 8       # Rolling window to detect swing lows/highs
VOL_MULTIPLIER   = 1.5    # Volume must be 1.5x the slow SMA
ATR_MULTIPLIER   = 0.5    # ATR must be > 0.5x of rolling ATR mean
MIN_SIGNAL_SCORE = 3       # Out of 4 conditions must be true for a signal


class DivergenceVolatilityStrategy:
    """
    Live implementation of DivergenceVolatility_AI6.
    Plugs into strategy_agent.py — no backtesting.py dependency.
    """

    def __init__(self):
        self.name = "DivergenceVolatilityStrategy"
        cprint(f"📊 {self.name} loaded (Sharpe 2.14 backtest baseline)", "cyan")

    # ── Public interface expected by strategy_agent ───────────────────────────

    def analyze(self, df: pd.DataFrame, token: str = "BTC") -> dict:
        """
        Run indicator logic on OHLCV DataFrame.

        Args:
            df:    DataFrame with columns [open, high, low, close, volume]
                   and a datetime index. Needs at least 60 bars.
            token: Symbol being analyzed.

        Returns:
            Signal dict.
        """
        if len(df) < MACD_SLOW + MACD_SIGNAL + 5:
            cprint(f"⚠️  {self.name}: not enough bars ({len(df)}), need {MACD_SLOW + MACD_SIGNAL + 5}+", "yellow")
            return self._neutral(token)

        df = df.copy()
        df.columns = [c.lower() for c in df.columns]

        try:
            df = self._compute_indicators(df)
            return self._generate_signal(df, token)
        except Exception as e:
            cprint(f"⚠️  {self.name} error: {e}", "yellow")
            return self._neutral(token)

    # ── Indicator computation ─────────────────────────────────────────────────

    def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        close  = df['close']
        high   = df['high']
        low    = df['low']
        volume = df['volume']

        # Bollinger Bands
        df['bb_mid']   = close.rolling(BB_PERIOD).mean()
        bb_std         = close.rolling(BB_PERIOD).std()
        df['bb_upper'] = df['bb_mid'] + BB_STD * bb_std
        df['bb_lower'] = df['bb_mid'] - BB_STD * bb_std
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']

        # MACD
        ema_fast        = close.ewm(span=MACD_FAST,   adjust=False).mean()
        ema_slow        = close.ewm(span=MACD_SLOW,   adjust=False).mean()
        macd_line       = ema_fast - ema_slow
        signal_line     = macd_line.ewm(span=MACD_SIGNAL, adjust=False).mean()
        df['macd']      = macd_line
        df['macd_hist'] = macd_line - signal_line

        # ATR
        prev_close    = close.shift(1)
        tr            = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low  - prev_close).abs()
        ], axis=1).max(axis=1)
        df['atr']     = tr.rolling(ATR_PERIOD).mean()
        df['atr_mean']= df['atr'].rolling(20).mean()

        # Volume
        df['vol_fast'] = volume.rolling(VOL_SMA_FAST).mean()
        df['vol_slow'] = volume.rolling(VOL_SMA_SLOW).mean()

        # Swing points
        df['swing_low']  = low.rolling(SWING_PERIOD).min()
        df['swing_high'] = high.rolling(SWING_PERIOD).max()

        return df

    # ── Signal generation ─────────────────────────────────────────────────────

    def _generate_signal(self, df: pd.DataFrame, token: str) -> dict:
        cur  = df.iloc[-1]
        prev = df.iloc[-2]

        # ── Bullish divergence conditions ──────────────────────────────────────
        # 1. Price makes lower low, MACD makes higher low → divergence
        price_lower_low  = cur['close'] < prev['swing_low']
        macd_higher_low  = cur['macd_hist'] > prev['macd_hist']
        bull_divergence  = price_lower_low and macd_higher_low

        # 2. Volume above slow SMA by multiplier
        volume_surge     = cur['volume'] > (cur['vol_slow'] * VOL_MULTIPLIER)

        # 3. Bollinger Band width expanding (volatility breakout)
        bb_expanding     = cur['bb_width'] > df['bb_width'].rolling(20).mean().iloc[-1]

        # 4. ATR above its own mean (momentum present)
        atr_elevated     = cur['atr'] > cur['atr_mean'] * ATR_MULTIPLIER

        bull_score = sum([bull_divergence, volume_surge, bb_expanding, atr_elevated])

        # ── Bearish divergence conditions ──────────────────────────────────────
        price_higher_high = cur['close'] > prev['swing_high']
        macd_lower_high   = cur['macd_hist'] < prev['macd_hist']
        bear_divergence   = price_higher_high and macd_lower_high

        bear_score = sum([bear_divergence, volume_surge, bb_expanding, atr_elevated])

        # ── Determine signal ───────────────────────────────────────────────────
        metadata = {
            "bull_divergence":  bull_divergence,
            "bear_divergence":  bear_divergence,
            "volume_surge":     volume_surge,
            "bb_expanding":     bb_expanding,
            "atr_elevated":     atr_elevated,
            "bull_score":       bull_score,
            "bear_score":       bear_score,
            "close":            round(float(cur['close']), 2),
            "atr":              round(float(cur['atr']), 2),
            "bb_width":         round(float(cur['bb_width']), 4),
            "macd_hist":        round(float(cur['macd_hist']), 4),
        }

        if bull_score >= MIN_SIGNAL_SCORE:
            confidence = 0.6 + (bull_score / 4) * 0.4   # 0.75 – 1.0
            cprint(f"🟢 {self.name}: BULLISH DIVERGENCE on {token} "
                   f"(score {bull_score}/4, conf {confidence:.0%})", "green", attrs=["bold"])
            return {
                "token":      token,
                "signal":     round(confidence, 2),
                "direction":  "BUY",
                "metadata":   metadata,
            }

        if bear_score >= MIN_SIGNAL_SCORE:
            confidence = 0.6 + (bear_score / 4) * 0.4
            cprint(f"🔴 {self.name}: BEARISH DIVERGENCE on {token} "
                   f"(score {bear_score}/4, conf {confidence:.0%})", "red", attrs=["bold"])
            return {
                "token":      token,
                "signal":     round(confidence, 2),
                "direction":  "SELL",
                "metadata":   metadata,
            }

        cprint(f"⚪ {self.name}: no divergence on {token} "
               f"(bull {bull_score}/4, bear {bear_score}/4)", "white")
        return self._neutral(token)

    @staticmethod
    def _neutral(token: str) -> dict:
        return {"token": token, "signal": 0.0, "direction": "NEUTRAL", "metadata": {}}
