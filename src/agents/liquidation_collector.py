"""
🌙 Moon Dev's Free Liquidation Collector
Sources (tried in order, all FREE — no API key required):
  1. Hyperliquid public API  — native liquidation data
  2. OI-change proxy         — infers liq pressure from OI drops + price direction

Replaces liquidation_agent.py's data collection for signal fusion purposes.

Writes to: src/data/liquidation_history.csv
Format expected by signal_fusion_agent.py:
  timestamp, long_liq_usd, short_liq_usd

Run standalone: python src/agents/liquidation_collector.py
Or import:      from src.agents.liquidation_collector import collect, save_to_csv
"""

import os
import csv
import time
import requests
import pandas as pd
from datetime import datetime, timezone
from termcolor import cprint

OUTPUT_FILE = "src/data/liquidation_history.csv"
POLL_INTERVAL_SECONDS = 15 * 60   # Every 15 minutes

HL_INFO_URL = "https://api.hyperliquid.xyz/info"
WATCHLIST   = ["BTC", "ETH", "SOL"]

# OI proxy scale: treat each 1% OI drop as this many USD in liquidations
OI_PROXY_SCALE_USD = 5_000_000   # $5M per 1% OI drop


def _fetch_hl_liquidations() -> list[dict]:
    """
    Try Hyperliquid's native liquidation endpoint.
    Returns list of raw liquidation dicts, or [] if unavailable.
    """
    try:
        resp = requests.post(
            HL_INFO_URL,
            headers={"Content-Type": "application/json"},
            json={"type": "liquidations"},
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("liquidations", "data", "records"):
                if key in data and isinstance(data[key], list):
                    return data[key]
        return []
    except Exception:
        return []


def _collect_from_hl_liquidations() -> list[dict]:
    """
    Parse Hyperliquid native liquidation data into long/short USD totals.
    HL liquidation side: 'A' = long being liquidated, 'B' = short being liquidated
    """
    raw = _fetch_hl_liquidations()
    if not raw:
        return []

    long_liq_usd  = 0.0
    short_liq_usd = 0.0

    for item in raw:
        # Normalize field names
        coin = item.get("coin", item.get("symbol", ""))
        if coin not in WATCHLIST:
            continue

        side = str(item.get("side", item.get("dir", ""))).upper()
        sz   = float(item.get("sz",  item.get("size",  item.get("qty", 0))))
        px   = float(item.get("px",  item.get("price", item.get("markPx", 0))))
        usd  = sz * px

        # 'A' = ask side = long liquidated; 'B' = bid side = short liquidated
        if side in ("A", "SELL", "LONG"):
            long_liq_usd  += usd
        elif side in ("B", "BUY", "SHORT"):
            short_liq_usd += usd

    if long_liq_usd == 0 and short_liq_usd == 0:
        return []

    cprint(f"  [liq] HL native: long=${long_liq_usd:,.0f}  short=${short_liq_usd:,.0f}", "cyan")
    return [{
        "timestamp":     datetime.now(timezone.utc).isoformat(),
        "long_liq_usd":  round(long_liq_usd,  2),
        "short_liq_usd": round(short_liq_usd, 2),
        "total_liq_usd": round(long_liq_usd + short_liq_usd, 2),
    }]


def _collect_from_oi_proxy() -> list[dict]:
    """
    OI-change proxy: infer liquidation pressure from OI drops + price direction.

    Logic:
      - Fetch current OI and mark prices for BTC, ETH, SOL
      - Compare to last saved OI in oi_history.csv
      - If OI dropped → liquidations occurred
      - Price falling + OI drop → long liquidations
      - Price rising  + OI drop → short liquidations
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
            return []

        universe    = data[0].get("universe", [])
        asset_ctxs  = data[1]
        name_to_idx = {coin["name"]: i for i, coin in enumerate(universe)}

        # Load previous OI from oi_history.csv
        prev_oi = {}
        oi_file = "src/data/oi_history.csv"
        if os.path.isfile(oi_file):
            try:
                df_oi = pd.read_csv(oi_file)
                if not df_oi.empty:
                    last = df_oi.iloc[-1]
                    prev_oi = {
                        "BTC": float(last.get("btc_oi", 0) or 0),
                        "ETH": float(last.get("eth_oi", 0) or 0),
                        "SOL": float(last.get("sol_oi", 0) or 0),
                    }
            except Exception:
                pass

        long_liq_usd  = 0.0
        short_liq_usd = 0.0

        for sym in WATCHLIST:
            idx = name_to_idx.get(sym)
            if idx is None or idx >= len(asset_ctxs):
                continue

            ctx      = asset_ctxs[idx]
            oi_coins = float(ctx.get("openInterest", 0))
            mark_px  = float(ctx.get("markPx", 0))
            oi_usd   = oi_coins * mark_px

            prev = prev_oi.get(sym, 0)
            if prev <= 0 or oi_usd <= 0:
                continue

            oi_change_pct = ((oi_usd - prev) / prev) * 100

            # Only count OI drops as liquidation pressure
            if oi_change_pct >= 0:
                continue

            liq_usd = abs(oi_change_pct) * OI_PROXY_SCALE_USD

            # Use funding rate sign to infer direction:
            # Positive funding → market was long → OI drop = long liquidations
            # Negative funding → market was short → OI drop = short liquidations
            funding = float(ctx.get("funding", 0))
            if funding >= 0:
                long_liq_usd  += liq_usd
            else:
                short_liq_usd += liq_usd

        if long_liq_usd == 0 and short_liq_usd == 0:
            # No OI drop detected — return neutral (zero) liquidation reading
            long_liq_usd  = 0.0
            short_liq_usd = 0.0

        cprint(
            f"  [liq] OI proxy: long=${long_liq_usd:,.0f}  short=${short_liq_usd:,.0f}",
            "cyan",
        )
        return [{
            "timestamp":     datetime.now(timezone.utc).isoformat(),
            "long_liq_usd":  round(long_liq_usd,  2),
            "short_liq_usd": round(short_liq_usd, 2),
            "total_liq_usd": round(long_liq_usd + short_liq_usd, 2),
        }]

    except Exception as e:
        cprint(f"⚠️  OI proxy liquidation error: {e}", "yellow")
        return []


def collect() -> list[dict]:
    """
    Collect liquidation data.
    1. Try Hyperliquid native liquidation endpoint (free)
    2. Fall back to OI-change proxy (always available)
    """
    # Try HL native liquidation data first
    data = _collect_from_hl_liquidations()
    if data:
        cprint("  [liquidation] source: Hyperliquid native API (free)", "cyan")
        return data

    # Fall back to OI-based proxy
    cprint("  [liquidation] HL native unavailable, using OI proxy...", "yellow")
    data = _collect_from_oi_proxy()
    if data:
        cprint("  [liquidation] source: OI-change proxy (free)", "cyan")
        return data

    cprint("⚠️  No liquidation data available from any source", "yellow")
    return []


def save_to_csv(data: list[dict]):
    """Append liquidation data to CSV history file."""
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
    """Main loop — polls liquidation data every 15 minutes."""
    cprint("🌙 Free Liquidation Collector starting (HL native + OI proxy)...", "cyan")
    cprint(f"   Symbols: {', '.join(WATCHLIST)}", "white")
    cprint(f"   Output:  {OUTPUT_FILE}", "white")

    while True:
        cprint("🔍 Fetching liquidation data...", "cyan")
        data = collect()
        if data:
            save_to_csv(data)
            d = data[0]
            long_usd  = d["long_liq_usd"]
            short_usd = d["short_liq_usd"]
            total_usd = d["total_liq_usd"]
            dominant  = "LONG LIQD" if long_usd > short_usd else "SHORT LIQD"
            colour    = "red" if long_usd > short_usd else "green"
            cprint(
                f"  {dominant}: long=${long_usd:,.0f}  short=${short_usd:,.0f}  "
                f"total=${total_usd:,.0f}",
                colour,
            )
            cprint(f"💾 Saved → {OUTPUT_FILE}", "green")
        else:
            cprint("⚠️  No liquidation data this cycle", "yellow")

        cprint(f"\n💤 Sleeping {POLL_INTERVAL_SECONDS // 60} minutes...\n", "white")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
