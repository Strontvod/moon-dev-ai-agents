"""
Moon Dev's Position Snapshot Collector
Tracks positions within 15% of liquidation — squeeze & cascade signals.

Primary  : MoonDev API  /api/position_snapshots/symbol/{symbol}
Fallback : Free HL metaAndAssetCtxs — estimates squeeze pressure from
           OI concentration + funding rate extremes when no API key.

Writes to: src/data/position_snapshot_history.csv
Format expected by signal_fusion_agent.py:
  timestamp, symbol, at_risk_long_usd, at_risk_short_usd,
  squeeze_score, direction

Run standalone: python src/agents/position_snapshot_collector.py
Or import:      from src.agents.position_snapshot_collector import collect
"""

import os
import csv
import time
import numpy as np
import requests
from datetime import datetime, timezone
from termcolor import cprint
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

OUTPUT_FILE       = "src/data/position_snapshot_history.csv"
POLL_INTERVAL_SECONDS = 15 * 60   # Every 15 minutes

# Symbols to track (must match MoonDev supported list)
WATCHLIST = ["BTC", "ETH", "SOL"]

# MoonDev API
MOONDEV_API_KEY = os.getenv("MOONDEV_API_KEY", "")
MOONDEV_BASE    = "https://api.moondev.com"

# Free HL endpoints
HL_INFO_URL  = "https://api.hyperliquid.xyz/info"
HL_STATS_URL = "https://stats-data.hyperliquid.xyz/Mainnet"

# Squeeze score thresholds
# Positive score  → many longs near liquidation → potential long squeeze (bearish)
# Negative score  → many shorts near liquidation → potential short squeeze (bullish)
EXTREME_FUNDING_THRESHOLD = 0.01   # 1% per 8h = extreme


# ── MoonDev primary ───────────────────────────────────────────────────────────

def _fetch_moondev_snapshots(symbol: str) -> dict | None:
    """Fetch position snapshots from MoonDev API."""
    if not MOONDEV_API_KEY:
        return None
    try:
        url = f"{MOONDEV_BASE}/api/position_snapshots/symbol/{symbol}"
        headers = {"X-API-Key": MOONDEV_API_KEY}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        cprint(f"  MoonDev position_snapshots error ({symbol}): {e}", "yellow")
        return None


def _score_from_moondev(symbol: str) -> dict | None:
    """Compute squeeze score from MoonDev position snapshot data."""
    data = _fetch_moondev_snapshots(symbol)
    if not data:
        return None

    # MoonDev returns list of position records or a dict with 'snapshots' key
    records = data if isinstance(data, list) else data.get("snapshots", data.get("data", []))
    if not records:
        return None

    at_risk_long_usd  = 0.0
    at_risk_short_usd = 0.0

    for rec in records:
        side = str(rec.get("side", rec.get("position_side", ""))).lower()
        val  = float(rec.get("position_value", rec.get("value", rec.get("size_usd", 0))) or 0)
        if side in ("long", "buy", "b"):
            at_risk_long_usd += val
        elif side in ("short", "sell", "s"):
            at_risk_short_usd += val

    total = at_risk_long_usd + at_risk_short_usd
    if total == 0:
        return None

    # Positive squeeze_score → longs at risk → bearish pressure
    # Negative squeeze_score → shorts at risk → bullish pressure (short squeeze)
    raw = (at_risk_long_usd - at_risk_short_usd) / total
    squeeze_score = float(np.clip(raw, -1.0, 1.0))
    direction = "SHORT_SQUEEZE" if squeeze_score < -0.1 else (
                "LONG_SQUEEZE"  if squeeze_score >  0.1 else "NEUTRAL")

    return {
        "timestamp":          datetime.now(timezone.utc).isoformat(),
        "symbol":             symbol,
        "at_risk_long_usd":   round(at_risk_long_usd, 2),
        "at_risk_short_usd":  round(at_risk_short_usd, 2),
        "squeeze_score":      round(squeeze_score, 4),
        "direction":          direction,
        "source":             "moondev",
    }


# ── Free HL fallback ──────────────────────────────────────────────────────────

def _fetch_hl_meta() -> list:
    """Fetch metaAndAssetCtxs from Hyperliquid."""
    try:
        r = requests.post(HL_INFO_URL, json={"type": "metaAndAssetCtxs"}, timeout=15)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and len(data) >= 2:
            return data[0].get("universe", []), data[1]
    except Exception as e:
        cprint(f"  HL metaAndAssetCtxs error: {e}", "yellow")
    return [], []


def _score_from_hl_fallback(symbol: str) -> dict | None:
    """
    Estimate squeeze pressure from HL funding rate + OI.
    Extreme positive funding → longs paying shorts → long squeeze risk (bearish).
    Extreme negative funding → shorts paying longs → short squeeze risk (bullish).
    """
    try:
        universe, ctxs = _fetch_hl_meta()
        if not universe or not ctxs:
            return None

        # Find symbol index
        idx = next((i for i, u in enumerate(universe) if u.get("name") == symbol), None)
        if idx is None or idx >= len(ctxs):
            return None

        ctx = ctxs[idx]
        funding     = float(ctx.get("funding", 0) or 0)   # per 8h
        oi_usd      = float(ctx.get("openInterest", 0) or 0) * float(ctx.get("markPx", 0) or 0)
        mark_px     = float(ctx.get("markPx", 0) or 0)

        if mark_px == 0:
            return None

        # Normalize funding to squeeze score
        # funding > EXTREME_FUNDING_THRESHOLD → longs at risk → positive score (bearish)
        squeeze_score = float(np.clip(funding / EXTREME_FUNDING_THRESHOLD, -1.0, 1.0))

        # Estimate at-risk USD using OI * 15% (positions within 15% of liq)
        at_risk_est = oi_usd * 0.15
        at_risk_long_usd  = at_risk_est * max(0, squeeze_score)
        at_risk_short_usd = at_risk_est * max(0, -squeeze_score)

        direction = "SHORT_SQUEEZE" if squeeze_score < -0.1 else (
                    "LONG_SQUEEZE"  if squeeze_score >  0.1 else "NEUTRAL")

        return {
            "timestamp":          datetime.now(timezone.utc).isoformat(),
            "symbol":             symbol,
            "at_risk_long_usd":   round(at_risk_long_usd, 2),
            "at_risk_short_usd":  round(at_risk_short_usd, 2),
            "squeeze_score":      round(squeeze_score, 4),
            "direction":          direction,
            "source":             "hl_fallback",
        }

    except Exception as e:
        cprint(f"  HL fallback error ({symbol}): {e}", "yellow")
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def collect() -> list[dict]:
    """
    Collect position snapshot data for all watchlist symbols.
    Returns list of dicts (one per symbol).
    """
    results = []
    for symbol in WATCHLIST:
        rec = _score_from_moondev(symbol) or _score_from_hl_fallback(symbol)
        if rec:
            results.append(rec)
        else:
            cprint(f"  ⚠️  No position snapshot data for {symbol}", "yellow")
    return results


def save_to_csv(data: list[dict]):
    """Append position snapshot records to CSV history file."""
    if not data:
        return
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    file_exists = os.path.isfile(OUTPUT_FILE)
    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        if not file_exists:
            writer.writeheader()
        writer.writerows(data)


def run():
    """Main loop — polls position snapshots every 15 minutes."""
    cprint("Position Snapshot Collector starting...", "cyan")
    cprint(f"  Output : {OUTPUT_FILE}", "white")
    cprint(f"  Source : {'MoonDev API' if MOONDEV_API_KEY else 'HL fallback (no MOONDEV_API_KEY)'}", "white")

    while True:
        data = collect()
        if data:
            save_to_csv(data)
            for d in data:
                score = d["squeeze_score"]
                colour = "red" if score > 0.1 else ("green" if score < -0.1 else "white")
                cprint(f"  {d['symbol']}: {d['direction']} (squeeze={score:+.3f}) "
                       f"[{d['source']}]", colour)
            cprint(f"Saved {len(data)} records → {OUTPUT_FILE}", "green")
        else:
            cprint("No position snapshot data this cycle", "yellow")

        cprint(f"Sleeping {POLL_INTERVAL_SECONDS // 60} minutes...\n", "white")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
