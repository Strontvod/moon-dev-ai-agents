"""
🌙 Moon Dev's Free OI (Open Interest) Collector
Uses Hyperliquid public API — NO API KEY REQUIRED.

Replaces whale_agent.py's OI collection for signal fusion purposes.
Writes to: src/data/oi_history.csv
Format expected by signal_fusion_agent.py:
  timestamp, btc_oi, eth_oi, sol_oi, total_oi,
  btc_change_pct, eth_change_pct, total_change_pct

Run standalone: python src/agents/oi_collector.py
Or import:      from src.agents.oi_collector import collect, save_to_csv
"""

import os
import csv
import time
import requests
import pandas as pd
from datetime import datetime, timezone
from termcolor import cprint

OUTPUT_FILE = "src/data/oi_history.csv"
POLL_INTERVAL_SECONDS = 15 * 60   # Every 15 minutes
WATCHLIST = ["BTC", "ETH", "SOL"]
HL_INFO_URL = "https://api.hyperliquid.xyz/info"


def get_oi_data() -> dict | None:
    """
    Fetch current OI for BTC, ETH, SOL from Hyperliquid public API.
    Returns dict with oi_usd values, or None on error.
    """
    try:
        resp = requests.post(
            HL_INFO_URL,
            headers={"Content-Type": "application/json"},
            json={"type": "metaAndAssetCtxs"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        if not (isinstance(data, list) and len(data) >= 2):
            cprint("⚠️  Unexpected metaAndAssetCtxs format", "yellow")
            return None

        universe = data[0].get("universe", [])
        asset_ctxs = data[1]

        # Build name → index map
        name_to_idx = {coin["name"]: i for i, coin in enumerate(universe)}

        result = {}
        for sym in WATCHLIST:
            idx = name_to_idx.get(sym)
            if idx is None or idx >= len(asset_ctxs):
                cprint(f"⚠️  {sym} not found in HL universe", "yellow")
                result[sym] = 0.0
                continue

            ctx = asset_ctxs[idx]
            oi_coins = float(ctx.get("openInterest", 0))
            mark_px  = float(ctx.get("markPx", 0))
            oi_usd   = oi_coins * mark_px
            result[sym] = oi_usd

        return result

    except Exception as e:
        cprint(f"❌ Error fetching OI data: {e}", "red")
        return None


def _load_last_row() -> dict | None:
    """Load the most recent row from oi_history.csv for change calculation."""
    if not os.path.isfile(OUTPUT_FILE):
        return None
    try:
        df = pd.read_csv(OUTPUT_FILE)
        if df.empty:
            return None
        return df.iloc[-1].to_dict()
    except Exception:
        return None


def collect() -> list[dict]:
    """
    Fetch OI, compute change percentages vs last reading.
    Returns list with one dict (or empty list on failure).
    """
    oi = get_oi_data()
    if oi is None:
        return []

    btc_oi  = oi.get("BTC", 0.0)
    eth_oi  = oi.get("ETH", 0.0)
    sol_oi  = oi.get("SOL", 0.0)
    total_oi = btc_oi + eth_oi + sol_oi

    # Compute change percentages vs previous reading
    btc_change_pct   = 0.0
    eth_change_pct   = 0.0
    total_change_pct = 0.0

    prev = _load_last_row()
    if prev:
        prev_btc   = float(prev.get("btc_oi",   0) or 0)
        prev_eth   = float(prev.get("eth_oi",   0) or 0)
        prev_total = float(prev.get("total_oi", 0) or 0)

        if prev_btc > 0:
            btc_change_pct = ((btc_oi - prev_btc) / prev_btc) * 100
        if prev_eth > 0:
            eth_change_pct = ((eth_oi - prev_eth) / prev_eth) * 100
        if prev_total > 0:
            total_change_pct = ((total_oi - prev_total) / prev_total) * 100

    row = {
        "timestamp":        datetime.now(timezone.utc).isoformat(),
        "btc_oi":           round(btc_oi,   2),
        "eth_oi":           round(eth_oi,   2),
        "sol_oi":           round(sol_oi,   2),
        "total_oi":         round(total_oi, 2),
        "btc_change_pct":   round(btc_change_pct,   4),
        "eth_change_pct":   round(eth_change_pct,   4),
        "total_change_pct": round(total_change_pct, 4),
    }
    return [row]


def save_to_csv(data: list[dict]):
    """Append OI data to CSV history file."""
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
    """Main loop — polls OI every 15 minutes."""
    cprint("🌙 Free OI Collector starting (Hyperliquid public API)...", "cyan")
    cprint(f"   Watching: {', '.join(WATCHLIST)}", "white")
    cprint(f"   Output:   {OUTPUT_FILE}", "white")

    while True:
        data = collect()
        if data:
            save_to_csv(data)
            d = data[0]
            chg = d["total_change_pct"]
            colour = "green" if chg > 0 else ("red" if chg < 0 else "white")
            cprint(
                f"  OI → BTC ${d['btc_oi']/1e9:.2f}B  "
                f"ETH ${d['eth_oi']/1e9:.2f}B  "
                f"SOL ${d['sol_oi']/1e9:.2f}B  "
                f"Total ${d['total_oi']/1e9:.2f}B  "
                f"Δ {chg:+.3f}%",
                colour,
            )
            cprint(f"💾 Saved → {OUTPUT_FILE}", "green")
        else:
            cprint("⚠️  No OI data this cycle", "yellow")

        cprint(f"\n💤 Sleeping {POLL_INTERVAL_SECONDS // 60} minutes...\n", "white")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
