"""
🌙 Moon Dev's Free Solana Data Layer
Built with love by Moon Dev 🚀

Drop-in replacements for the two most expensive BirdEye calls:
  - token_price()    → Jupiter Price API  (free, no key)
  - token_overview() → DexScreener API    (free, no key)

Usage — swap this one line in any agent:
    # BEFORE (costs money):
    from src import nice_funcs as nf

    # AFTER (free):
    from src import nice_funcs_free as nf   ← same function names, no key needed

Everything else (buy, sell, wallet, OHLCV) stays in nice_funcs.py.
"""

import os
import requests
import pandas as pd
from termcolor import cprint
from dotenv import load_dotenv

load_dotenv()

# ─── Constants ────────────────────────────────────────────────────────────────
QUOTE_TOKEN   = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"   # USDC
SOL_ADDRESS   = "So11111111111111111111111111111111111111111"
MIN_TRADES_LAST_HOUR = int(os.getenv("MIN_TRADES_LAST_HOUR", 2))

DEXSCREENER_URL     = "https://api.dexscreener.com/latest/dex/tokens"
DEXSCREENER_SEARCH  = "https://api.dexscreener.com/latest/dex/search?q="


# ──────────────────────────────────────────────────────────────────────────────
# 1. token_price  — replaces BirdEye /defi/price
# ──────────────────────────────────────────────────────────────────────────────

def token_price(address: str) -> float | None:
    """
    Fetch token price in USD via DexScreener API.
    Completely free — no API key required.

    Returns float price or None on failure.
    """
    try:
        resp = requests.get(f"{DEXSCREENER_URL}/{address}", timeout=10)
        resp.raise_for_status()
        pairs = resp.json().get("pairs") or []
        if not pairs:
            cprint(f"⚠️  DexScreener: no price data for {address[:8]}...", "yellow")
            return None
        # Use highest-liquidity pair for most accurate price
        best = max(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0))
        price = best.get("priceUsd")
        return float(price) if price else None
    except Exception as e:
        cprint(f"❌ token_price error: {e}", "red")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# 2. token_overview  — replaces BirdEye /defi/token_overview
# ──────────────────────────────────────────────────────────────────────────────

def token_overview(address: str) -> dict:
    """
    Fetch token overview via DexScreener API.
    Completely free — no API key required.

    Returns dict matching the keys that Moon Dev agents actually read:
      buy1h, sell1h, trade1h, buy_percentage, sell_percentage,
      minimum_trades_met, priceChangesXhrs, rug_pull,
      uniqueWallet2hr, v24USD, liquidity, mc, price, symbol, name
    """
    result = _empty_overview()

    try:
        resp = requests.get(f"{DEXSCREENER_URL}/{address}", timeout=10)
        resp.raise_for_status()
        pairs = resp.json().get("pairs") or []

        if not pairs:
            cprint(f"⚠️  DexScreener: no pairs for {address[:8]}...", "yellow")
            return result

        # Pick the highest-liquidity pair
        pair = max(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0))

        # ── Price ─────────────────────────────────────────────────────────────
        result["price"]  = float(pair.get("priceUsd") or 0)
        result["symbol"] = pair.get("baseToken", {}).get("symbol", "")
        result["name"]   = pair.get("baseToken", {}).get("name", "")

        # ── Volume / trades (DexScreener gives volume in USD, not trade count)
        # Approximate trade counts from txns if available
        txns = pair.get("txns", {})
        buy1h  = txns.get("h1", {}).get("buys",  0)
        sell1h = txns.get("h1", {}).get("sells", 0)
        trade1h = buy1h + sell1h
        total = trade1h or 1

        result["buy1h"]              = buy1h
        result["sell1h"]             = sell1h
        result["trade1h"]            = trade1h
        result["buy_percentage"]     = round(buy1h / total * 100, 2)
        result["sell_percentage"]    = round(sell1h / total * 100, 2)
        result["minimum_trades_met"] = trade1h >= MIN_TRADES_LAST_HOUR

        # ── Price changes ──────────────────────────────────────────────────────
        pc = pair.get("priceChange", {})
        price_changes = {
            "priceChange5m":  pc.get("m5",  0) or 0,
            "priceChange1h":  pc.get("h1",  0) or 0,
            "priceChange6h":  pc.get("h6",  0) or 0,
            "priceChange24h": pc.get("h24", 0) or 0,
        }
        result["priceChangesXhrs"] = price_changes
        result["rug_pull"] = any(v < -80 for v in price_changes.values())
        if result["rug_pull"]:
            cprint(f"⚠️  Rug pull signal on {result['symbol']}!", "red")

        # ── Liquidity / volume / market cap ───────────────────────────────────
        liq = pair.get("liquidity", {})
        result["liquidity"]       = float(liq.get("usd", 0) or 0)
        result["v24USD"]          = float(pair.get("volume", {}).get("h24", 0) or 0)
        result["mc"]              = float(pair.get("marketCap", 0) or 0)

        # DexScreener doesn't give unique wallet count — set to 0
        result["uniqueWallet2hr"] = 0
        result["watch"]           = 0
        result["view24h"]         = 0

        cprint(f"✅ {result['symbol']} ${result['price']:.6f} | "
               f"Liq: ${result['liquidity']:,.0f} | "
               f"Vol24h: ${result['v24USD']:,.0f}", "green")

    except Exception as e:
        cprint(f"❌ token_overview error: {e}", "red")

    return result


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _empty_overview() -> dict:
    return {
        "price": 0, "symbol": "", "name": "",
        "buy1h": 0, "sell1h": 0, "trade1h": 0,
        "buy_percentage": 0, "sell_percentage": 0,
        "minimum_trades_met": False,
        "priceChangesXhrs": {}, "rug_pull": False,
        "uniqueWallet2hr": 0, "v24USD": 0,
        "watch": 0, "view24h": 0,
        "liquidity": 0, "mc": 0,
    }


def get_price_multi(addresses: list[str]) -> dict[str, float]:
    """
    Fetch prices for multiple tokens via DexScreener.
    Batches into one call per address (DexScreener doesn't support multi-token batching).

    Returns: { address: price_float }
    """
    results = {}
    for address in addresses:
        price = token_price(address)
        if price is not None:
            results[address] = price
    return results


# ──────────────────────────────────────────────────────────────────────────────
# Quick test
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    TEST_TOKEN = "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"  # JUP token

    cprint("\n🌙 Testing free data layer...\n", "cyan")

    price = token_price(TEST_TOKEN)
    cprint(f"SOL price (Jupiter): ${price}", "white")

    overview = token_overview(TEST_TOKEN)
    cprint(f"\nSOL overview (DexScreener):", "white")
    for k, v in overview.items():
        cprint(f"  {k}: {v}", "white")
