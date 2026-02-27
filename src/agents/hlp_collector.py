"""
Moon Dev's HLP (Hyperliquidity Provider) Sentiment Collector
Primary: Hyperliquid public vault API (FREE, no key required)
Fallback: Moon Dev API v2 (requires MOONDEV_API_KEY)

HLP is the house liquidity pool on Hyperliquid (~$210M AUM).
Its positioning is a strong contrarian indicator:
  - HLP heavily long  → market may reverse down (contrarian SHORT signal)
  - HLP heavily short → market may reverse up   (contrarian LONG signal)

Writes to: src/data/hlp_history.csv
Format expected by signal_fusion_agent.py:
  timestamp, net_delta, sentiment_score, is_contrarian_long

Run standalone: python src/agents/hlp_collector.py
Or import:      from src.agents.hlp_collector import collect
"""

import os
import csv
import time
import requests
import numpy as np
from datetime import datetime, timezone
from termcolor import cprint

OUTPUT_FILE = "src/data/hlp_history.csv"
POLL_INTERVAL_SECONDS = 15 * 60   # Every 15 minutes

# Hyperliquid public API (no key required)
HL_INFO_URL = "https://api.hyperliquid.xyz/info"

# HLP vault address on Hyperliquid mainnet (publicly known)
# This is the Hyperliquidity Provider vault — the "house" market maker
HLP_VAULT_ADDRESS = "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"

# Symbols to sum for net delta calculation
WATCHLIST = ["BTC", "ETH", "SOL"]


def _collect_free_hl() -> list[dict]:
    """
    Fetch HLP vault positions from Hyperliquid public API (FREE).
    Uses vault_details endpoint to get HLP's net position across BTC/ETH/SOL.
    Contrarian signal: HLP net long → we lean short, HLP net short → we lean long.
    """
    try:
        resp = requests.post(
            HL_INFO_URL,
            headers={"Content-Type": "application/json"},
            json={"type": "vaultDetails", "vaultAddress": HLP_VAULT_ADDRESS},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        if not data:
            cprint("⚠️  No HLP vault data returned", "yellow")
            return []

        # vaultDetails returns portfolio positions
        # Structure: {"portfolio": [...], "name": "HLP", ...}
        portfolio = data.get("portfolio", [])
        if not portfolio:
            # Try alternative structure
            portfolio = data.get("positions", [])

        if not portfolio:
            cprint(f"⚠️  HLP vault data has no portfolio. Keys: {list(data.keys())}", "yellow")
            return _compute_from_funding_proxy()

        # Sum net position value across all assets
        # Positive = HLP is net long, Negative = HLP is net short
        net_delta = 0.0
        for pos in portfolio:
            # Handle both list and dict formats
            if isinstance(pos, list) and len(pos) >= 2:
                # [coin, {szi, entryPx, ...}]
                coin = pos[0]
                pos_data = pos[1] if isinstance(pos[1], dict) else {}
                szi = float(pos_data.get("szi", 0))
                mark_px = float(pos_data.get("entryPx", 0))
                net_delta += szi * mark_px
            elif isinstance(pos, dict):
                coin = pos.get("coin", pos.get("symbol", ""))
                szi = float(pos.get("szi", pos.get("size", 0)))
                mark_px = float(pos.get("entryPx", pos.get("markPx", 1)))
                net_delta += szi * mark_px

        return _build_result(net_delta)

    except Exception as e:
        cprint(f"⚠️  HLP vault API error: {e}", "yellow")
        return _compute_from_funding_proxy()


def _compute_from_funding_proxy() -> list[dict]:
    """
    Proxy: derive HLP sentiment from funding rates.
    HLP earns funding when it's on the opposite side of the market.
    High positive funding → market is long → HLP is likely short → contrarian LONG signal.
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

        universe  = data[0].get("universe", [])
        asset_ctxs = data[1]
        name_to_idx = {coin["name"]: i for i, coin in enumerate(universe)}

        total_funding = 0.0
        count = 0
        for sym in WATCHLIST:
            idx = name_to_idx.get(sym)
            if idx is None or idx >= len(asset_ctxs):
                continue
            ctx = asset_ctxs[idx]
            hourly_rate = float(ctx.get("funding", 0))
            annual_rate = hourly_rate * 24 * 365 * 100
            total_funding += annual_rate
            count += 1

        if count == 0:
            return []

        avg_funding = total_funding / count
        # High positive funding → market is long → HLP is short → contrarian LONG
        # Use funding as a proxy for HLP net delta (inverted)
        # Scale: 50% APR → net_delta proxy of -1 (HLP short)
        net_delta_proxy = -avg_funding / 50.0 * 1e6   # Scaled proxy value

        cprint(f"  [HLP] Using funding proxy (avg annual={avg_funding:.1f}%)", "yellow")
        return _build_result(net_delta_proxy)

    except Exception as e:
        cprint(f"⚠️  HLP funding proxy error: {e}", "yellow")
        return []


def _build_result(net_delta: float) -> list[dict]:
    """Convert net_delta to contrarian signal dict."""
    # Normalize: $100M net long/short → ±1.0 signal
    SCALE = 100_000_000   # $100M
    if SCALE > 0:
        signal = -np.clip(net_delta / SCALE, -1.0, 1.0)   # inverted = contrarian
    else:
        signal = 0.0

    is_contrarian_long = float(signal) > 0.1

    return [{
        "timestamp":          datetime.now(timezone.utc).isoformat(),
        "net_delta":          round(net_delta, 2),
        "sentiment_score":    round(float(signal), 4),
        "is_contrarian_long": is_contrarian_long,
    }]


def _collect_moondev_api() -> list[dict]:
    """Fallback: fetch HLP sentiment from Moon Dev API v2 (requires MOONDEV_API_KEY)."""
    try:
        from src.agents.api import MoonDevAPI
        api = MoonDevAPI()

        sentiment = api.get_hlp_sentiment()
        if not sentiment:
            return []

        net_delta = 0.0
        z_score   = 0.0

        for key in ['net_delta', 'netDelta', 'delta', 'net_position']:
            if key in sentiment:
                net_delta = float(sentiment[key])
                break

        for key in ['z_score', 'zScore', 'zscore']:
            if key in sentiment:
                z_score = float(sentiment[key])
                break

        if z_score != 0:
            signal = -np.clip(z_score / 3.0, -1.0, 1.0)
        elif net_delta != 0:
            signal = -np.clip(net_delta / abs(net_delta) * 0.5, -1.0, 1.0)
        else:
            signal = 0.0

        return [{
            "timestamp":          datetime.now(timezone.utc).isoformat(),
            "net_delta":          round(net_delta, 2),
            "sentiment_score":    round(float(signal), 4),
            "is_contrarian_long": float(signal) > 0.1,
        }]

    except Exception as e:
        cprint(f"⚠️  MoonDev API HLP error: {e}", "yellow")
        return []


def collect() -> list[dict]:
    """
    Collect HLP sentiment data.
    Tries free Hyperliquid vault API first; falls back to MoonDev API if available.
    """
    # Primary: free Hyperliquid public API
    data = _collect_free_hl()
    if data:
        cprint("  [HLP] source: Hyperliquid vault API (free)", "cyan")
        return data

    # Fallback: MoonDev API (requires key)
    cprint("  [HLP] vault API failed, trying MoonDev API...", "yellow")
    data = _collect_moondev_api()
    if data:
        cprint("  [HLP] source: MoonDev API", "cyan")
        return data

    cprint("⚠️  No HLP data available from any source", "yellow")
    return []


def save_to_csv(data: list[dict]):
    """Append HLP data to CSV history file."""
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
    """Main loop — polls HLP sentiment every 15 minutes."""
    cprint("HLP Sentiment Collector starting...", "cyan")
    cprint(f"   Output: {OUTPUT_FILE}", "white")

    while True:
        data = collect()
        if data:
            save_to_csv(data)
            for d in data:
                s = d["sentiment_score"]
                colour = "green" if s > 0.1 else ("red" if s < -0.1 else "white")
                label = "CONTRARIAN LONG" if d["is_contrarian_long"] else (
                    "CONTRARIAN SHORT" if s < -0.1 else "NEUTRAL")
                cprint(f"  HLP: {label} (score={s:+.3f}, delta=${d['net_delta']:,.0f})", colour)
            cprint(f"Saved {len(data)} records -> {OUTPUT_FILE}", "green")
        else:
            cprint("No HLP data this cycle", "yellow")

        cprint(f"Sleeping {POLL_INTERVAL_SECONDS // 60} minutes...\n", "white")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
