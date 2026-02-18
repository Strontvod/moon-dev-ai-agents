"""
🌙 Moon Dev's Signal Fusion Agent
Built with love by Moon Dev 🚀

Combines outputs from Sentiment, Whale (OI), Funding, and Liquidation agents
into a single unified signal score before the Trading Agent fires.

Scores range from -100 (strong short) to +100 (strong long).
Each source is weighted and clamped independently before fusion.

Output:
  src/data/signal_fusion/latest_signal.json
  src/data/signal_fusion/signal_history.csv

Usage:
  python src/agents/signal_fusion_agent.py   # standalone
  from src.agents.signal_fusion_agent import get_fused_signal  # import
"""

import os
import json
import csv
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from pathlib import Path
from termcolor import cprint

# ─── Output ───────────────────────────────────────────────────────────────────
OUTPUT_DIR = "src/data/signal_fusion"
LATEST_FILE = os.path.join(OUTPUT_DIR, "latest_signal.json")
HISTORY_FILE = os.path.join(OUTPUT_DIR, "signal_history.csv")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─── Source Data Paths ────────────────────────────────────────────────────────
SENTIMENT_CSV   = "src/data/sentiment_history.csv"
FUNDING_CSV     = "src/data/funding_history.csv"
OI_CSV          = "src/data/oi_history.csv"
LIQUIDATION_CSV = "src/data/liquidation_history.csv"

# ─── Signal Weights (must sum to 1.0) ────────────────────────────────────────
WEIGHTS = {
    "sentiment":   0.25,   # Social sentiment (Twitter/news)
    "funding":     0.30,   # Perpetual funding rates (strongest edge)
    "oi":          0.25,   # Open interest / whale moves
    "liquidation": 0.20,   # Liquidation pressure
}

# ─── Staleness threshold: ignore data older than this ────────────────────────
MAX_DATA_AGE_HOURS = 2


# ──────────────────────────────────────────────────────────────────────────────
# COMPONENT READERS
# Each returns a float in [-1, +1] or None if data unavailable/stale.
# ──────────────────────────────────────────────────────────────────────────────

def _is_fresh(ts: pd.Timestamp) -> bool:
    """Check if a timestamp is within MAX_DATA_AGE_HOURS."""
    cutoff = datetime.now() - timedelta(hours=MAX_DATA_AGE_HOURS)
    return ts.to_pydatetime().replace(tzinfo=None) >= cutoff


def _cutoff() -> pd.Timestamp:
    """Return a timezone-naive cutoff timestamp for CSV comparisons."""
    return pd.Timestamp.now() - pd.Timedelta(hours=MAX_DATA_AGE_HOURS)


def read_sentiment_signal() -> float | None:
    """
    Reads sentiment_history.csv.
    Expects columns: timestamp, sentiment_score  (score in [-1, +1])
    """
    try:
        df = pd.read_csv(SENTIMENT_CSV)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        recent = df[df['timestamp'] >= pd.Timestamp.now() - pd.Timedelta(hours=MAX_DATA_AGE_HOURS)]
        if recent.empty:
            cprint("⚠️  Sentiment data stale or missing", "yellow")
            return None
        score = float(recent['sentiment_score'].iloc[-1])
        return np.clip(score, -1, 1)
    except Exception as e:
        cprint(f"⚠️  Sentiment read error: {e}", "yellow")
        return None


def read_funding_signal() -> float | None:
    """
    Reads funding_history.csv.
    Expects columns: timestamp, annual_rate  (e.g. 25.0 = 25% APR)

    Logic:
      - Extremely negative funding (< -10%) → contrarian LONG signal (+1)
      - Extremely positive funding (> +50%) → contrarian SHORT signal (-1)
      - Neutral funding (−10% to +20%) → slight direction lean
    """
    try:
        df = pd.read_csv(FUNDING_CSV)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        recent = df[df['timestamp'] >= pd.Timestamp.now() - pd.Timedelta(hours=MAX_DATA_AGE_HOURS)]
        if recent.empty:
            cprint("⚠️  Funding data stale or missing", "yellow")
            return None

        rate = float(recent['annual_rate'].iloc[-1])

        # Map funding rate → signal (contrarian: high positive = short signal)
        if rate > 100:
            signal = -1.0      # Extreme greed — short
        elif rate > 50:
            signal = -0.75
        elif rate > 20:
            signal = -0.30
        elif rate > 10:
            signal = -0.10
        elif rate > -5:
            signal = 0.0       # Neutral zone
        elif rate > -10:
            signal = 0.30
        else:
            signal = 1.0       # Extreme fear — long

        return np.clip(signal, -1, 1)
    except Exception as e:
        cprint(f"⚠️  Funding read error: {e}", "yellow")
        return None


def read_oi_signal() -> float | None:
    """
    Reads oi_history.csv (Open Interest — whale agent output).
    Expects columns: timestamp, oi_change_pct

    Logic:
      - Surging OI + price rising → confirms uptrend (+)
      - Surging OI + price falling → confirms downtrend (-)
      - Falling OI → position unwinding, reduce confidence
    """
    try:
        df = pd.read_csv(OI_CSV)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        recent = df[df['timestamp'] >= pd.Timestamp.now() - pd.Timedelta(hours=MAX_DATA_AGE_HOURS)]
        if recent.empty:
            cprint("⚠️  OI data stale or missing", "yellow")
            return None

        oi_chg = float(recent['oi_change_pct'].iloc[-1])

        # Normalize: ±25% OI change → ±1.0 signal
        signal = np.clip(oi_chg / 25.0, -1, 1)
        return signal
    except Exception as e:
        cprint(f"⚠️  OI read error: {e}", "yellow")
        return None


def read_liquidation_signal() -> float | None:
    """
    Reads liquidation_history.csv.
    Expects columns: timestamp, long_liq_usd, short_liq_usd

    Logic:
      - More longs liquidated → price was falling → oversold bounce potential (+)
      - More shorts liquidated → price was rising → overbought caution (-)
    """
    try:
        df = pd.read_csv(LIQUIDATION_CSV)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        recent = df[df['timestamp'] >= pd.Timestamp.now() - pd.Timedelta(hours=MAX_DATA_AGE_HOURS)]
        if recent.empty:
            cprint("⚠️  Liquidation data stale or missing", "yellow")
            return None

        long_liq  = float(recent['long_liq_usd'].iloc[-1])
        short_liq = float(recent['short_liq_usd'].iloc[-1])
        total      = long_liq + short_liq

        if total == 0:
            return 0.0

        # Ratio: +1 = all longs wiped (bullish bounce), -1 = all shorts wiped (bearish)
        ratio = (long_liq - short_liq) / total
        return np.clip(ratio, -1, 1)
    except Exception as e:
        cprint(f"⚠️  Liquidation read error: {e}", "yellow")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# FUSION ENGINE
# ──────────────────────────────────────────────────────────────────────────────

def get_fused_signal(verbose: bool = True) -> dict:
    """
    Reads all agent outputs, applies weights, returns fused signal dict.

    Returns:
        {
            "score":      float,   # -100 to +100
            "direction":  str,     # STRONG_LONG / LONG / NEUTRAL / SHORT / STRONG_SHORT
            "confidence": float,   # 0-100 (higher = more sources agree)
            "sources": {
                "sentiment":   float | None,
                "funding":     float | None,
                "oi":          float | None,
                "liquidation": float | None,
            },
            "timestamp": str,
            "active_sources": int,
        }
    """
    raw = {
        "sentiment":   read_sentiment_signal(),
        "funding":     read_funding_signal(),
        "oi":          read_oi_signal(),
        "liquidation": read_liquidation_signal(),
    }

    # Only score sources that returned data
    active = {k: v for k, v in raw.items() if v is not None}
    active_count = len(active)

    if active_count == 0:
        cprint("❌ No signal sources available", "red")
        result = {
            "score": 0.0,
            "direction": "NEUTRAL",
            "confidence": 0.0,
            "sources": raw,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_sources": 0,
        }
        _save(result)
        return result

    # Renormalize weights for available sources
    total_weight = sum(WEIGHTS[k] for k in active)
    weighted_sum = sum((v * WEIGHTS[k]) / total_weight for k, v in active.items())

    # Scale to -100 / +100
    score = round(weighted_sum * 100, 2)

    # Direction label
    if score >= 60:
        direction = "STRONG_LONG"
    elif score >= 25:
        direction = "LONG"
    elif score <= -60:
        direction = "STRONG_SHORT"
    elif score <= -25:
        direction = "SHORT"
    else:
        direction = "NEUTRAL"

    # Confidence: how many sources agree on direction, scaled by active count
    signs = [np.sign(v) for v in active.values()]
    agree = signs.count(np.sign(score)) if score != 0 else len(signs)
    confidence = round((agree / active_count) * 100 * (active_count / 4), 1)
    confidence = min(confidence, 100.0)

    result = {
        "score":          score,
        "direction":      direction,
        "confidence":     confidence,
        "sources":        raw,
        "timestamp":      datetime.now(timezone.utc).isoformat(),
        "active_sources": active_count,
    }

    _save(result)

    if verbose:
        _print_summary(result)

    return result


def _save(result: dict):
    """Persist to latest JSON and append to CSV history."""
    with open(LATEST_FILE, "w") as f:
        json.dump(result, f, indent=2, default=str)

    row = {
        "timestamp":      result["timestamp"],
        "score":          result["score"],
        "direction":      result["direction"],
        "confidence":     result["confidence"],
        "active_sources": result["active_sources"],
        **{f"src_{k}": v for k, v in result["sources"].items()},
    }
    file_exists = os.path.isfile(HISTORY_FILE)
    with open(HISTORY_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def _print_summary(result: dict):
    colour_map = {
        "STRONG_LONG":  "green",
        "LONG":         "green",
        "NEUTRAL":      "white",
        "SHORT":        "red",
        "STRONG_SHORT": "red",
    }
    colour = colour_map.get(result["direction"], "white")

    cprint("\n" + "═" * 50, "cyan")
    cprint("🌙  SIGNAL FUSION RESULT", "cyan")
    cprint("═" * 50, "cyan")
    cprint(f"  Score:       {result['score']:+.1f} / 100", colour)
    cprint(f"  Direction:   {result['direction']}", colour, attrs=["bold"])
    cprint(f"  Confidence:  {result['confidence']:.1f}%", "white")
    cprint(f"  Sources:     {result['active_sources']}/4 active", "white")
    cprint("─" * 50, "cyan")
    for k, v in result["sources"].items():
        val_str = f"{v:+.3f}" if v is not None else "N/A (stale)"
        cprint(f"  {k:<14} {val_str}", "white")
    cprint("═" * 50, "cyan")


# ──────────────────────────────────────────────────────────────────────────────
# TRADING GATE — call this from trading_agent before placing orders
# ──────────────────────────────────────────────────────────────────────────────

def should_trade(
    min_score: float = 25.0,
    min_confidence: float = 40.0,
    min_sources: int = 2,
) -> tuple[bool, str, dict]:
    """
    Returns (ok_to_trade, reason, signal_dict).

    Example:
        ok, reason, sig = should_trade()
        if not ok:
            cprint(f"⛔ Signal fusion blocked trade: {reason}", "yellow")
            return
        if sig['direction'] in ('STRONG_LONG', 'LONG'):
            nf.market_buy(...)
        elif sig['direction'] in ('STRONG_SHORT', 'SHORT'):
            nf.market_sell(...)
    """
    sig = get_fused_signal(verbose=False)

    if sig["active_sources"] < min_sources:
        return False, f"Only {sig['active_sources']} active sources (need {min_sources})", sig

    if sig["confidence"] < min_confidence:
        return False, f"Confidence {sig['confidence']:.1f}% < threshold {min_confidence}%", sig

    if abs(sig["score"]) < min_score:
        return False, f"Score {sig['score']:+.1f} inside neutral band ±{min_score}", sig

    return True, "Signal green", sig


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cprint("🌙 Moon Dev's Signal Fusion Agent", "cyan", attrs=["bold"])
    signal = get_fused_signal(verbose=True)
    cprint(f"\n💾 Saved → {LATEST_FILE}", "green")
