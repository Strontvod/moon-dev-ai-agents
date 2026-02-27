"""
Moon Dev's Order Flow & Imbalance Collector
Primary: Hyperliquid public API recent_trades (FREE, no key required)
Fallback: Moon Dev API v2 (requires MOONDEV_API_KEY)

Writes to: src/data/orderflow_history.csv
Format expected by signal_fusion_agent.py:
  timestamp, buy_volume, sell_volume, imbalance_ratio

Run standalone: python src/agents/orderflow_collector.py
Or import:      from src.agents.orderflow_collector import collect
"""

import os
import csv
import time
import requests
import numpy as np
from datetime import datetime, timezone
from termcolor import cprint

OUTPUT_FILE = "src/data/orderflow_history.csv"
POLL_INTERVAL_SECONDS = 15 * 60   # Every 15 minutes

# Hyperliquid public API (no key required)
HL_INFO_URL = "https://api.hyperliquid.xyz/info"
WATCHLIST = ["BTC", "ETH", "SOL"]


def _collect_free_hl() -> list[dict]:
    """
    Fetch order flow from Hyperliquid recent_trades endpoint (FREE).
    Aggregates buy/sell volume across BTC, ETH, SOL.
    Trade side: "A" = ask-side fill (buyer-initiated = BUY)
                "B" = bid-side fill (seller-initiated = SELL)
    """
    total_buy_usd  = 0.0
    total_sell_usd = 0.0
    any_data = False

    for sym in WATCHLIST:
        try:
            resp = requests.post(
                HL_INFO_URL,
                headers={"Content-Type": "application/json"},
                json={"type": "recentTrades", "coin": sym},
                timeout=15,
            )
            resp.raise_for_status()
            trades = resp.json()

            if not trades:
                continue

            any_data = True
            for t in trades:
                px  = float(t.get("px",  0))
                sz  = float(t.get("sz",  0))
                usd = px * sz
                # "A" = aggressor was buyer (buy-initiated)
                # "B" = aggressor was seller (sell-initiated)
                side = str(t.get("side", "")).upper()
                if side == "A":
                    total_buy_usd  += usd
                else:
                    total_sell_usd += usd

        except Exception as e:
            cprint(f"⚠️  HL recent_trades error ({sym}): {e}", "yellow")

    if not any_data:
        return []

    total = total_buy_usd + total_sell_usd
    ratio = (total_buy_usd - total_sell_usd) / total if total > 0 else 0.0

    return [{
        "timestamp":       datetime.now(timezone.utc).isoformat(),
        "buy_volume":      round(total_buy_usd,  2),
        "sell_volume":     round(total_sell_usd, 2),
        "imbalance_ratio": round(float(np.clip(ratio, -1.0, 1.0)), 4),
    }]


def _collect_moondev_api() -> list[dict]:
    """Fallback: fetch order flow from Moon Dev API v2 (requires MOONDEV_API_KEY)."""
    try:
        from src.agents.api import MoonDevAPI
        api = MoonDevAPI()

        of  = api.get_orderflow()
        imb = api.get_imbalance('1h')

        buy_vol  = 0.0
        sell_vol = 0.0

        if not of.empty:
            of.columns = [c.lower() for c in of.columns]
            buy_col  = next((c for c in ['buy_volume', 'buys', 'buy_usd', 'buy_size']  if c in of.columns), None)
            sell_col = next((c for c in ['sell_volume', 'sells', 'sell_usd', 'sell_size'] if c in of.columns), None)
            if buy_col and sell_col:
                buy_vol  = float(of[buy_col].sum())
                sell_vol = float(of[sell_col].sum())

        if buy_vol == 0 and sell_vol == 0 and not imb.empty:
            imb.columns = [c.lower() for c in imb.columns]
            buy_col  = next((c for c in ['buy_volume', 'buys', 'buy_usd', 'buy_size', 'buy']  if c in imb.columns), None)
            sell_col = next((c for c in ['sell_volume', 'sells', 'sell_usd', 'sell_size', 'sell'] if c in imb.columns), None)
            if buy_col and sell_col:
                buy_vol  = float(imb[buy_col].sum())
                sell_vol = float(imb[sell_col].sum())

            if buy_vol == 0 and sell_vol == 0:
                ratio_col = next((c for c in ['imbalance', 'ratio', 'imbalance_ratio'] if c in imb.columns), None)
                if ratio_col:
                    ratio = float(imb[ratio_col].mean())
                    return [{"timestamp": datetime.now(timezone.utc).isoformat(),
                             "buy_volume": 0.0, "sell_volume": 0.0,
                             "imbalance_ratio": round(float(np.clip(ratio, -1.0, 1.0)), 4)}]

        if buy_vol == 0 and sell_vol == 0:
            return []

        total = buy_vol + sell_vol
        ratio = (buy_vol - sell_vol) / total if total > 0 else 0.0
        return [{"timestamp": datetime.now(timezone.utc).isoformat(),
                 "buy_volume": round(buy_vol, 2), "sell_volume": round(sell_vol, 2),
                 "imbalance_ratio": round(float(np.clip(ratio, -1.0, 1.0)), 4)}]

    except Exception as e:
        cprint(f"⚠️  MoonDev API order flow error: {e}", "yellow")
        return []


def collect() -> list[dict]:
    """
    Collect order flow data.
    Tries free Hyperliquid API first; falls back to MoonDev API if available.
    """
    # Primary: free Hyperliquid public API
    data = _collect_free_hl()
    if data:
        cprint("  [order flow] source: Hyperliquid public API (free)", "cyan")
        return data

    # Fallback: MoonDev API (requires key)
    cprint("  [order flow] HL failed, trying MoonDev API...", "yellow")
    data = _collect_moondev_api()
    if data:
        cprint("  [order flow] source: MoonDev API", "cyan")
        return data

    cprint("⚠️  Could not extract buy/sell volumes from any source", "yellow")
    return []


def save_to_csv(data: list[dict]):
    """Append order flow data to CSV history file."""
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
    """Main loop — polls order flow every 15 minutes."""
    cprint("Order Flow Collector starting...", "cyan")
    cprint(f"   Output: {OUTPUT_FILE}", "white")

    while True:
        data = collect()
        if data:
            save_to_csv(data)
            for d in data:
                ratio = d["imbalance_ratio"]
                colour = "green" if ratio > 0.1 else ("red" if ratio < -0.1 else "white")
                cprint(f"  Order Flow: imbalance={ratio:+.3f} "
                       f"(buy=${d['buy_volume']:,.0f} sell=${d['sell_volume']:,.0f})", colour)
            cprint(f"Saved {len(data)} records -> {OUTPUT_FILE}", "green")
        else:
            cprint("No order flow data this cycle", "yellow")

        cprint(f"Sleeping {POLL_INTERVAL_SECONDS // 60} minutes...\n", "white")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
