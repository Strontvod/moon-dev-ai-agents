"""
Moon Dev's Smart Money Signal Collector
Primary: Hyperliquid public leaderboard API (FREE, no key required)
Fallback: Moon Dev API v2 (requires MOONDEV_API_KEY)

Logic (free path):
  - Fetch Hyperliquid leaderboard (top traders by PnL)
  - Check their current positions via clearinghouse state
  - Compute net long/short bias of top-N traders
  - Positive score = top traders are net long → bullish signal

Writes to: src/data/smart_money_history.csv
Format expected by signal_fusion_agent.py:
  timestamp, signal_score, direction, top_pnl_bias

Run standalone: python src/agents/smart_money_collector.py
Or import:      from src.agents.smart_money_collector import collect
"""

import os
import csv
import time
import requests
import numpy as np
from datetime import datetime, timezone
from termcolor import cprint

OUTPUT_FILE = "src/data/smart_money_history.csv"
POLL_INTERVAL_SECONDS = 15 * 60   # Every 15 minutes

# Hyperliquid public API (no key required)
HL_INFO_URL = "https://api.hyperliquid.xyz/info"

# How many top traders to sample from the leaderboard
TOP_N_TRADERS = 20

# Symbols to check for long/short bias
WATCHLIST = ["BTC", "ETH", "SOL"]


# Hyperliquid stats API (separate from info API)
HL_STATS_URL = "https://stats-data.hyperliquid.xyz/Mainnet"


def _get_leaderboard() -> list[dict]:
    """
    Fetch Hyperliquid leaderboard (top traders by PnL).
    Tries multiple endpoints/windows to find working one.
    Returns list of {ethAddress, accountValue, pnl, ...} dicts.
    """
    # Try stats-data API first (separate endpoint)
    for window in ("day", "week", "allTime"):
        try:
            resp = requests.get(
                f"{HL_STATS_URL}/leaderboard",
                params={"window": window},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    return data[:TOP_N_TRADERS]
                if isinstance(data, dict):
                    for key in ("leaderboardRows", "rows", "data", "traders"):
                        if key in data and isinstance(data[key], list) and data[key]:
                            return data[key][:TOP_N_TRADERS]
        except Exception:
            pass

    # Try info API with window parameter
    for window in ("day", "week", "allTime"):
        try:
            resp = requests.post(
                HL_INFO_URL,
                headers={"Content-Type": "application/json"},
                json={"type": "leaderboard", "window": window},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    return data[:TOP_N_TRADERS]
                if isinstance(data, dict):
                    for key in ("leaderboardRows", "rows", "data"):
                        if key in data and isinstance(data[key], list) and data[key]:
                            return data[key][:TOP_N_TRADERS]
        except Exception:
            pass

    cprint("⚠️  All leaderboard endpoints failed", "yellow")
    return []


def _get_user_positions(address: str) -> list[dict]:
    """
    Fetch current open positions for a single trader address.
    Returns list of position dicts with coin, szi (size), entryPx.
    """
    try:
        resp = requests.post(
            HL_INFO_URL,
            headers={"Content-Type": "application/json"},
            json={"type": "clearinghouseState", "user": address},
            timeout=10,
        )
        resp.raise_for_status()
        state = resp.json()

        asset_positions = state.get("assetPositions", [])
        positions = []
        for ap in asset_positions:
            pos = ap.get("position", ap)
            coin = pos.get("coin", "")
            szi  = float(pos.get("szi", 0))
            if szi != 0 and coin in WATCHLIST:
                positions.append({"coin": coin, "szi": szi})
        return positions

    except Exception:
        return []


def _collect_free_hl() -> list[dict]:
    """
    Compute smart money signal from Hyperliquid leaderboard (FREE).
    Samples top-N traders and checks if they are net long or short.
    """
    leaders = _get_leaderboard()
    if not leaders:
        cprint("⚠️  No leaderboard data from Hyperliquid", "yellow")
        return []

    # Extract addresses — field name varies
    addresses = []
    for row in leaders:
        addr = (row.get("ethAddress") or row.get("address") or
                row.get("user") or row.get("account") or "")
        if addr and addr.startswith("0x"):
            addresses.append(addr)

    if not addresses:
        cprint("⚠️  Could not extract addresses from leaderboard", "yellow")
        return []

    cprint(f"  [smart money] Sampling {len(addresses)} top traders...", "cyan")

    long_count  = 0
    short_count = 0
    sampled     = 0

    # Sample up to TOP_N_TRADERS addresses (rate-limit friendly)
    for addr in addresses[:TOP_N_TRADERS]:
        positions = _get_user_positions(addr)
        for pos in positions:
            if pos["szi"] > 0:
                long_count  += 1
            elif pos["szi"] < 0:
                short_count += 1
        if positions:
            sampled += 1

    if long_count + short_count == 0:
        cprint("⚠️  No positions found for sampled traders", "yellow")
        return []

    total = long_count + short_count
    score = (long_count - short_count) / total   # [-1, +1]
    direction = "LONG" if score > 0.1 else ("SHORT" if score < -0.1 else "NEUTRAL")

    cprint(
        f"  [smart money] {sampled} traders sampled | "
        f"longs={long_count} shorts={short_count} | score={score:+.3f}",
        "green" if score > 0.1 else ("red" if score < -0.1 else "white"),
    )

    return [{
        "timestamp":    datetime.now(timezone.utc).isoformat(),
        "signal_score": round(float(np.clip(score, -1.0, 1.0)), 4),
        "direction":    direction,
        "top_pnl_bias": round(score, 4),
    }]


def _collect_moondev_api() -> list[dict]:
    """Fallback: fetch smart money signals from Moon Dev API v2 (requires MOONDEV_API_KEY)."""
    try:
        from src.agents.api import MoonDevAPI
        api = MoonDevAPI()
        df = api.get_smart_money_signals('1h')

        if df.empty:
            return []

        df.columns = [c.lower() for c in df.columns]

        long_col  = next((c for c in ['long_count', 'longs', 'buy_count', 'buyers']  if c in df.columns), None)
        short_col = next((c for c in ['short_count', 'shorts', 'sell_count', 'sellers'] if c in df.columns), None)

        if long_col and short_col:
            total_long  = float(df[long_col].sum())
            total_short = float(df[short_col].sum())
            total = total_long + total_short
            score = (total_long - total_short) / total if total > 0 else 0.0
        else:
            score_col = next((c for c in ['signal', 'score', 'bias', 'direction_score'] if c in df.columns), None)
            if score_col:
                score = float(np.clip(float(df[score_col].mean()), -1.0, 1.0))
            else:
                return []

        direction = "LONG" if score > 0.1 else ("SHORT" if score < -0.1 else "NEUTRAL")
        return [{
            "timestamp":    datetime.now(timezone.utc).isoformat(),
            "signal_score": round(float(np.clip(score, -1.0, 1.0)), 4),
            "direction":    direction,
            "top_pnl_bias": round(score, 4),
        }]

    except Exception as e:
        cprint(f"⚠️  MoonDev API smart money error: {e}", "yellow")
        return []


def collect() -> list[dict]:
    """
    Collect smart money signal.
    Tries free Hyperliquid leaderboard first; falls back to MoonDev API if available.
    """
    # Primary: free Hyperliquid leaderboard
    data = _collect_free_hl()
    if data:
        cprint("  [smart money] source: Hyperliquid leaderboard (free)", "cyan")
        return data

    # Fallback: MoonDev API (requires key)
    cprint("  [smart money] leaderboard failed, trying MoonDev API...", "yellow")
    data = _collect_moondev_api()
    if data:
        cprint("  [smart money] source: MoonDev API", "cyan")
        return data

    cprint("⚠️  No smart money data available from any source", "yellow")
    return []


def save_to_csv(data: list[dict]):
    """Append smart money signals to CSV history file."""
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
    """Main loop — polls smart money signals every 15 minutes."""
    cprint("Smart Money Collector starting...", "cyan")
    cprint(f"   Output: {OUTPUT_FILE}", "white")

    while True:
        data = collect()
        if data:
            save_to_csv(data)
            for d in data:
                colour = "green" if d["direction"] == "LONG" else ("red" if d["direction"] == "SHORT" else "white")
                cprint(f"  Smart Money: {d['direction']} (score={d['signal_score']:+.3f})", colour)
            cprint(f"Saved {len(data)} records -> {OUTPUT_FILE}", "green")
        else:
            cprint("No smart money data this cycle", "yellow")

        cprint(f"Sleeping {POLL_INTERVAL_SECONDS // 60} minutes...\n", "white")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
