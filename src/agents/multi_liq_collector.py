"""
Moon Dev's Multi-Exchange Liquidation Collector
Combines liquidation data from Hyperliquid + Binance + Bybit + OKX.

Primary  : MoonDev API  /api/all_liquidations/{timeframe}.json
           (29x faster than legacy — 30-second updates for live timeframes)
Fallback : Existing liquidation_collector.py (HL-only, free)

Writes to: src/data/multi_liq_history.csv
Format expected by signal_fusion_agent.py:
  timestamp, long_liq_usd, short_liq_usd, total_liq_usd,
  liq_ratio, exchanges

Run standalone: python src/agents/multi_liq_collector.py
Or import:      from src.agents.multi_liq_collector import collect
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

OUTPUT_FILE           = "src/data/multi_liq_history.csv"
POLL_INTERVAL_SECONDS = 15 * 60   # Every 15 minutes

# MoonDev API
MOONDEV_API_KEY = os.getenv("MOONDEV_API_KEY", "")
MOONDEV_BASE    = "https://api.moondev.com"

# Timeframe to fetch (live endpoints: 10m, 1h, 4h, 12h, 24h, 2d, 5d)
TIMEFRAME = "1h"


# ── MoonDev primary ───────────────────────────────────────────────────────────

def _fetch_moondev_all_liqs(timeframe: str = TIMEFRAME) -> dict | None:
    """Fetch combined multi-exchange liquidations from MoonDev API."""
    if not MOONDEV_API_KEY:
        return None
    try:
        url = f"{MOONDEV_BASE}/api/all_liquidations/{timeframe}.json"
        headers = {"X-API-Key": MOONDEV_API_KEY}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        cprint(f"  MoonDev all_liquidations error: {e}", "yellow")
        return None


def _parse_moondev_liqs(data: dict) -> dict | None:
    """Parse MoonDev multi-liq response into normalized record."""
    if not data:
        return None
    try:
        # MoonDev response structure (may vary — handle multiple formats)
        long_liq  = 0.0
        short_liq = 0.0
        exchanges = []

        # Try top-level keys first
        for key in ["long_liquidations", "long_liq_usd", "longs_usd", "long"]:
            if key in data:
                long_liq = float(data[key] or 0)
                break

        for key in ["short_liquidations", "short_liq_usd", "shorts_usd", "short"]:
            if key in data:
                short_liq = float(data[key] or 0)
                break

        # Try nested 'total' or 'summary' key
        if long_liq == 0 and short_liq == 0:
            summary = data.get("total", data.get("summary", data.get("stats", {})))
            if isinstance(summary, dict):
                for key in ["long_liquidations", "long_liq_usd", "longs_usd"]:
                    if key in summary:
                        long_liq = float(summary[key] or 0)
                        break
                for key in ["short_liquidations", "short_liq_usd", "shorts_usd"]:
                    if key in summary:
                        short_liq = float(summary[key] or 0)
                        break

        # Try 'exchanges' breakdown
        if "exchanges" in data and isinstance(data["exchanges"], dict):
            for ex_name, ex_data in data["exchanges"].items():
                exchanges.append(ex_name)
                if isinstance(ex_data, dict) and long_liq == 0:
                    long_liq  += float(ex_data.get("long_liq_usd",  ex_data.get("longs",  0)) or 0)
                    short_liq += float(ex_data.get("short_liq_usd", ex_data.get("shorts", 0)) or 0)

        total = long_liq + short_liq
        if total == 0:
            return None

        # liq_ratio: positive → more longs liquidated (bearish pressure)
        liq_ratio = float(np.clip((long_liq - short_liq) / total, -1.0, 1.0))

        return {
            "timestamp":     datetime.now(timezone.utc).isoformat(),
            "long_liq_usd":  round(long_liq, 2),
            "short_liq_usd": round(short_liq, 2),
            "total_liq_usd": round(total, 2),
            "liq_ratio":     round(liq_ratio, 4),
            "exchanges":     ",".join(exchanges) if exchanges else "HL+Binance+Bybit+OKX",
            "source":        "moondev",
        }
    except Exception as e:
        cprint(f"  MoonDev liq parse error: {e}", "yellow")
        return None


# ── Free HL fallback ──────────────────────────────────────────────────────────

def _fetch_hl_fallback() -> dict | None:
    """Fall back to HL-only liquidation_collector when no MoonDev key."""
    try:
        from src.agents.liquidation_collector import collect as hl_collect
        records = hl_collect()
        if not records:
            return None
        # Aggregate across all records returned
        long_liq  = sum(float(r.get("long_liq_usd",  0)) for r in records)
        short_liq = sum(float(r.get("short_liq_usd", 0)) for r in records)
        total     = long_liq + short_liq
        if total == 0:
            return None
        liq_ratio = float(np.clip((long_liq - short_liq) / total, -1.0, 1.0))
        return {
            "timestamp":     datetime.now(timezone.utc).isoformat(),
            "long_liq_usd":  round(long_liq, 2),
            "short_liq_usd": round(short_liq, 2),
            "total_liq_usd": round(total, 2),
            "liq_ratio":     round(liq_ratio, 4),
            "exchanges":     "hyperliquid",
            "source":        "hl_fallback",
        }
    except Exception as e:
        cprint(f"  HL fallback liq error: {e}", "yellow")
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def collect() -> list[dict]:
    """
    Collect multi-exchange liquidation data.
    Returns list with one aggregated record.
    """
    # Try MoonDev first
    raw = _fetch_moondev_all_liqs(TIMEFRAME)
    rec = _parse_moondev_liqs(raw)

    # Fall back to HL-only
    if rec is None:
        rec = _fetch_hl_fallback()

    if rec:
        return [rec]

    cprint("⚠️  No multi-liq data available", "yellow")
    return []


def save_to_csv(data: list[dict]):
    """Append multi-liq records to CSV history file."""
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
    """Main loop — polls multi-exchange liquidations every 15 minutes."""
    cprint("Multi-Exchange Liquidation Collector starting...", "cyan")
    cprint(f"  Output : {OUTPUT_FILE}", "white")
    cprint(f"  Source : {'MoonDev API (4 exchanges)' if MOONDEV_API_KEY else 'HL fallback (no MOONDEV_API_KEY)'}", "white")

    while True:
        data = collect()
        if data:
            save_to_csv(data)
            for d in data:
                ratio  = d["liq_ratio"]
                colour = "red" if ratio > 0.2 else ("green" if ratio < -0.2 else "white")
                cprint(f"  Multi-Liq [{d['exchanges']}]: "
                       f"long=${d['long_liq_usd']:,.0f}  short=${d['short_liq_usd']:,.0f}  "
                       f"ratio={ratio:+.3f}", colour)
            cprint(f"Saved {len(data)} records → {OUTPUT_FILE}", "green")
        else:
            cprint("No multi-liq data this cycle", "yellow")

        cprint(f"Sleeping {POLL_INTERVAL_SECONDS // 60} minutes...\n", "white")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
