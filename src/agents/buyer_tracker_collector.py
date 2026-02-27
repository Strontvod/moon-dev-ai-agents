"""
Moon Dev's Buyer Tracker Collector
Tracks $5k+ buyers on BTC/ETH/SOL — accumulation signals.

Primary  : MoonDev API  /buyers/ endpoint
           Identifies large buyers (smart accumulation = bullish signal)
Fallback : HL recentTrades filtered for large buy-side trades

Writes to: src/data/buyer_history.csv
Format expected by signal_fusion_agent.py:
  timestamp, symbol, large_buy_count, large_buy_usd,
  accumulation_score, direction

Run standalone: python src/agents/buyer_tracker_collector.py
Or import:      from src.agents.buyer_tracker_collector import collect
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

OUTPUT_FILE           = "src/data/buyer_history.csv"
POLL_INTERVAL_SECONDS = 15 * 60   # Every 15 minutes

# Symbols to track
WATCHLIST = ["BTC", "ETH", "SOL"]

# MoonDev API
MOONDEV_API_KEY = os.getenv("MOONDEV_API_KEY", "")
MOONDEV_BASE    = "https://api.moondev.com"

# Free HL endpoints
HL_INFO_URL = "https://api.hyperliquid.xyz/info"

# Thresholds
LARGE_TRADE_USD   = 5_000    # $5k+ = large buyer (matches MoonDev definition)
RECENT_TRADES_N   = 500      # Number of recent trades to sample per symbol
# Accumulation score scale: $X in large buys maps to score of 1.0
SCALE_USD         = 10_000_000  # $10M in large buys = max score


# ── MoonDev primary ───────────────────────────────────────────────────────────

def _fetch_moondev_buyers(symbol: str) -> dict | None:
    """Fetch $5k+ buyer data from MoonDev API."""
    if not MOONDEV_API_KEY:
        return None
    try:
        # Try multiple possible endpoint patterns
        for path in [f"/buyers/{symbol}", f"/api/buyers/{symbol}", f"/buyers?symbol={symbol}"]:
            url = f"{MOONDEV_BASE}{path}"
            headers = {"X-API-Key": MOONDEV_API_KEY}
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                return r.json()
        return None
    except Exception as e:
        cprint(f"  MoonDev buyers error ({symbol}): {e}", "yellow")
        return None


def _score_from_moondev(symbol: str) -> dict | None:
    """Compute accumulation score from MoonDev buyer data."""
    data = _fetch_moondev_buyers(symbol)
    if not data:
        return None

    try:
        # Handle list or dict response
        records = data if isinstance(data, list) else data.get("buyers", data.get("data", []))
        if not records:
            return None

        large_buy_count = len(records)
        large_buy_usd   = sum(
            float(r.get("usd_value", r.get("size_usd", r.get("value", 0))) or 0)
            for r in records
        )

        # Normalize to [-1, +1]: positive = accumulation (bullish)
        acc_score = float(np.clip(large_buy_usd / SCALE_USD, 0.0, 1.0))
        direction = "ACCUMULATING" if acc_score > 0.1 else "NEUTRAL"

        return {
            "timestamp":          datetime.now(timezone.utc).isoformat(),
            "symbol":             symbol,
            "large_buy_count":    large_buy_count,
            "large_buy_usd":      round(large_buy_usd, 2),
            "accumulation_score": round(acc_score, 4),
            "direction":          direction,
            "source":             "moondev",
        }
    except Exception as e:
        cprint(f"  MoonDev buyer parse error ({symbol}): {e}", "yellow")
        return None


# ── Free HL fallback ──────────────────────────────────────────────────────────

def _fetch_hl_recent_trades(symbol: str) -> list:
    """Fetch recent trades from Hyperliquid for a symbol."""
    try:
        r = requests.post(
            HL_INFO_URL,
            json={"type": "recentTrades", "coin": symbol},
            timeout=15,
        )
        r.raise_for_status()
        return r.json() or []
    except Exception as e:
        cprint(f"  HL recentTrades error ({symbol}): {e}", "yellow")
        return []


def _score_from_hl_fallback(symbol: str) -> dict | None:
    """
    Estimate accumulation from HL recent trades.
    Filters for large buy-side trades (side='A' = buy on HL).
    """
    try:
        trades = _fetch_hl_recent_trades(symbol)
        if not trades:
            return None

        large_buys  = []
        large_sells = []

        for t in trades[:RECENT_TRADES_N]:
            side = str(t.get("side", "")).upper()
            px   = float(t.get("px",  t.get("price", 0)) or 0)
            sz   = float(t.get("sz",  t.get("size",  0)) or 0)
            usd  = px * sz

            if usd >= LARGE_TRADE_USD:
                if side == "A":    # A = buyer-initiated on HL
                    large_buys.append(usd)
                elif side == "B":  # B = seller-initiated
                    large_sells.append(usd)

        large_buy_usd  = sum(large_buys)
        large_sell_usd = sum(large_sells)
        total          = large_buy_usd + large_sell_usd

        if total == 0:
            return None

        # Net accumulation: positive = more large buying than selling
        net_ratio = (large_buy_usd - large_sell_usd) / total
        acc_score = float(np.clip(net_ratio, -1.0, 1.0))
        direction = "ACCUMULATING" if acc_score > 0.1 else (
                    "DISTRIBUTING" if acc_score < -0.1 else "NEUTRAL")

        return {
            "timestamp":          datetime.now(timezone.utc).isoformat(),
            "symbol":             symbol,
            "large_buy_count":    len(large_buys),
            "large_buy_usd":      round(large_buy_usd, 2),
            "accumulation_score": round(acc_score, 4),
            "direction":          direction,
            "source":             "hl_fallback",
        }

    except Exception as e:
        cprint(f"  HL buyer fallback error ({symbol}): {e}", "yellow")
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def collect() -> list[dict]:
    """
    Collect buyer/accumulation data for all watchlist symbols.
    Returns list of dicts (one per symbol).
    """
    results = []
    for symbol in WATCHLIST:
        rec = _score_from_moondev(symbol) or _score_from_hl_fallback(symbol)
        if rec:
            results.append(rec)
        else:
            cprint(f"  ⚠️  No buyer data for {symbol}", "yellow")
    return results


def save_to_csv(data: list[dict]):
    """Append buyer tracker records to CSV history file."""
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
    """Main loop — polls buyer data every 15 minutes."""
    cprint("Buyer Tracker Collector starting...", "cyan")
    cprint(f"  Output    : {OUTPUT_FILE}", "white")
    cprint(f"  Threshold : ${LARGE_TRADE_USD:,}+ per trade", "white")
    cprint(f"  Source    : {'MoonDev API' if MOONDEV_API_KEY else 'HL fallback (no MOONDEV_API_KEY)'}", "white")

    while True:
        data = collect()
        if data:
            save_to_csv(data)
            for d in data:
                score  = d["accumulation_score"]
                colour = "green" if score > 0.1 else ("red" if score < -0.1 else "white")
                cprint(f"  {d['symbol']}: {d['direction']} "
                       f"(score={score:+.3f}, buys=${d['large_buy_usd']:,.0f}, "
                       f"count={d['large_buy_count']}) [{d['source']}]", colour)
            cprint(f"Saved {len(data)} records → {OUTPUT_FILE}", "green")
        else:
            cprint("No buyer data this cycle", "yellow")

        cprint(f"Sleeping {POLL_INTERVAL_SECONDS // 60} minutes...\n", "white")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
