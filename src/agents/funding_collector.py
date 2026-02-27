"""
🌙 Moon Dev's Hyperliquid Funding Rate Collector
Free alternative to funding_agent.py — reads directly from Hyperliquid public API.
No MOONDEV_API_KEY required.

Writes to: src/data/funding_history.csv
Format expected by signal_fusion_agent.py:
  timestamp, symbol, annual_rate, hourly_rate

Run standalone: python src/agents/funding_collector.py
Or import:      from src.agents.funding_collector import get_latest_funding_rate
"""

import os
import csv
import time
from datetime import datetime, timezone
from termcolor import cprint

OUTPUT_FILE = "src/data/funding_history.csv"
POLL_INTERVAL_SECONDS = 15 * 60   # Every 15 minutes
ALERT_HIGH = 20.0    # % annual rate — funding is elevated
ALERT_LOW  = -5.0    # % annual rate — negative funding (longs being paid)

WATCHLIST = ["BTC", "ETH", "SOL"]


def get_funding_rates() -> list[dict]:
    """Fetch current funding rates from Hyperliquid public API."""
    try:
        from hyperliquid.info import Info
        import hyperliquid.utils.constants as constants

        info = Info(constants.MAINNET_API_URL, skip_ws=True)
        meta, asset_ctxs = info.meta_and_asset_ctxs()

        universe = meta.get("universe", [])
        results = []

        for i, asset in enumerate(universe):
            name = asset.get("name", "")
            if name not in WATCHLIST:
                continue
            if i >= len(asset_ctxs):
                continue

            ctx = asset_ctxs[i]
            hourly_rate = float(ctx.get("funding", 0))
            annual_rate = hourly_rate * 24 * 365 * 100   # Convert to % APR

            results.append({
                "timestamp":    datetime.now(timezone.utc).isoformat(),
                "symbol":       name,
                "annual_rate":  round(annual_rate, 4),
                "hourly_rate":  round(hourly_rate * 100, 6),
                "open_interest": ctx.get("openInterest", 0),
                "mark_price":   ctx.get("markPx", 0),
            })

        return results

    except Exception as e:
        cprint(f"❌ Error fetching funding rates: {e}", "red")
        return []


def save_to_csv(rates: list[dict]):
    """Append funding rates to CSV history file."""
    if not rates:
        return
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    file_exists = os.path.isfile(OUTPUT_FILE)
    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rates[0].keys())
        if not file_exists:
            writer.writeheader()
        writer.writerows(rates)


def print_table(rates: list[dict]):
    """Print funding rate summary."""
    cprint("\n🌙 Moon Dev's Funding Rate Monitor", "cyan", attrs=["bold"])
    cprint(f"{'Symbol':<8} {'Annual %':>10} {'Hourly %':>10} {'OI':>15}", "white")
    cprint("─" * 46, "cyan")
    for r in rates:
        rate = r["annual_rate"]
        colour = "green" if rate < -5 else ("red" if rate > 20 else "white")
        alert = " ⚠️" if rate > ALERT_HIGH or rate < ALERT_LOW else ""
        cprint(
            f"{r['symbol']:<8} {rate:>9.2f}% {r['hourly_rate']:>9.4f}%{alert}",
            colour
        )


def get_latest_funding_rate(symbol: str = "BTC") -> float | None:
    """
    Import-friendly: returns latest annual funding rate for a symbol.
    Returns None if unavailable.
    """
    rates = get_funding_rates()
    for r in rates:
        if r["symbol"] == symbol:
            return r["annual_rate"]
    return None


def run():
    """Main loop — polls funding rates every 15 minutes."""
    cprint("🚀 Hyperliquid Funding Collector starting...", "cyan")
    cprint(f"   Watching: {', '.join(WATCHLIST)}", "white")
    cprint(f"   Output:   {OUTPUT_FILE}", "white")
    cprint(f"   Alerts:   below {ALERT_LOW}% or above {ALERT_HIGH}% (annual)\n", "white")

    while True:
        rates = get_funding_rates()
        if rates:
            print_table(rates)
            save_to_csv(rates)
            cprint(f"💾 Saved {len(rates)} rates → {OUTPUT_FILE}", "green")
        else:
            cprint("⚠️  No rates fetched this cycle", "yellow")

        cprint(f"\n💤 Sleeping {POLL_INTERVAL_SECONDS // 60} minutes...\n", "white")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
