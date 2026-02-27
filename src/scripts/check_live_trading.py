"""
🌙 Moon Dev — Live Trading Readiness Check
Run this BEFORE setting LIVE_TRADING = True.

Checks every layer of the stack:
  1. Environment variables (.env)
  2. Hyperliquid connection + account balance
  3. Signal fusion (8–10 sources)
  4. AI model connectivity
  5. Config safety limits
  6. Risk agent dry-run

Usage:
    python -X utf8 src/scripts/check_live_trading.py

Green = ready  |  Yellow = optional/warning  |  Red = MUST FIX before going live
"""

import sys
import os
sys.path.insert(0, '.')

from termcolor import cprint
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join("src", ".env"))

PASS  = "✅"
WARN  = "⚠️ "
FAIL  = "❌"
INFO  = "ℹ️ "

results = []

def check(label, status, detail="", critical=True):
    icon = PASS if status == "pass" else (WARN if status == "warn" else FAIL)
    colour = "green" if status == "pass" else ("yellow" if status == "warn" else "red")
    cprint(f"  {icon}  {label:<40} {detail}", colour)
    results.append((label, status, critical))

def section(title):
    cprint(f"\n{'─'*60}", "cyan")
    cprint(f"  {title}", "cyan", attrs=["bold"])
    cprint(f"{'─'*60}", "cyan")


# ══════════════════════════════════════════════════════════════
# 1. ENVIRONMENT VARIABLES
# ══════════════════════════════════════════════════════════════
section("1 / 6  —  Environment Variables (.env)")

# Critical: at least one AI key
anthropic = os.getenv("ANTHROPIC_KEY", "")
deepseek  = os.getenv("DEEPSEEK_KEY", "")
groq      = os.getenv("GROQ_API_KEY", "")
openai_k  = os.getenv("OPENAI_KEY", "")

ai_keys = [k for k in [anthropic, deepseek, groq, openai_k] if k and not k.startswith("your_")]
if ai_keys:
    check("AI model key", "pass", f"{len(ai_keys)} key(s) found")
else:
    check("AI model key", "fail", "Need at least one: ANTHROPIC_KEY / DEEPSEEK_KEY / GROQ_API_KEY", critical=True)

# Critical: Hyperliquid private key
hl_key = os.getenv("HYPER_LIQUID_ETH_PRIVATE_KEY", "")
if hl_key and not hl_key.startswith("your_") and len(hl_key) > 10:
    check("HYPER_LIQUID_ETH_PRIVATE_KEY", "pass", f"0x...{hl_key[-4:]}")
else:
    check("HYPER_LIQUID_ETH_PRIVATE_KEY", "fail",
          "Required for live trading — see ENV_SETUP.md", critical=True)

# Optional: MoonDev API key
moondev = os.getenv("MOONDEV_API_KEY", "")
if moondev and not moondev.startswith("your_") and len(moondev) > 5:
    check("MOONDEV_API_KEY", "pass", "10/10 signal sources unlocked")
else:
    check("MOONDEV_API_KEY", "warn", "Optional — 8/10 sources still active (free HL APIs)", critical=False)

# Optional: BirdEye
birdeye = os.getenv("BIRDEYE_API_KEY", "")
if birdeye and not birdeye.startswith("your_"):
    check("BIRDEYE_API_KEY", "pass", "Solana token data available")
else:
    check("BIRDEYE_API_KEY", "warn", "Optional — only needed for Solana agents", critical=False)


# ══════════════════════════════════════════════════════════════
# 2. HYPERLIQUID CONNECTION
# ══════════════════════════════════════════════════════════════
section("2 / 6  —  Hyperliquid Connection")

try:
    import requests
    r = requests.post("https://api.hyperliquid.xyz/info",
                      json={"type": "meta"}, timeout=10)
    r.raise_for_status()
    meta = r.json()
    n_assets = len(meta.get("universe", []))
    check("HL API reachable", "pass", f"{n_assets} assets in universe")
except Exception as e:
    check("HL API reachable", "fail", str(e)[:60])

# Account balance check (only if key present)
if hl_key and not hl_key.startswith("your_") and len(hl_key) > 10:
    try:
        import eth_account
        acct = eth_account.Account.from_key(hl_key)
        addr = acct.address

        r2 = requests.post("https://api.hyperliquid.xyz/info",
                           json={"type": "clearinghouseState", "user": addr},
                           timeout=10)
        r2.raise_for_status()
        state = r2.json()
        margin = state.get("marginSummary", {})
        account_value = float(margin.get("accountValue", 0))
        withdrawable  = float(margin.get("withdrawable", 0))

        if account_value >= 10:
            check("Account balance", "pass",
                  f"${account_value:,.2f} total  |  ${withdrawable:,.2f} withdrawable")
        elif account_value > 0:
            check("Account balance", "warn",
                  f"${account_value:,.2f} — low balance, consider depositing more")
        else:
            check("Account balance", "fail",
                  "Balance is $0 — deposit USDC at app.hyperliquid.xyz")

        # Open positions
        positions = state.get("assetPositions", [])
        open_pos = [p for p in positions if float(p.get("position", {}).get("szi", 0)) != 0]
        if open_pos:
            syms = [p["position"]["coin"] for p in open_pos]
            check("Open positions", "warn",
                  f"{len(open_pos)} open: {', '.join(syms)} — review before going live", critical=False)
        else:
            check("Open positions", "pass", "No open positions (clean slate)")

        cprint(f"\n  {INFO}  Wallet: {addr}", "white")

    except Exception as e:
        check("Account state", "fail", str(e)[:80])
else:
    check("Account balance", "warn", "Skipped — no HYPER_LIQUID_ETH_PRIVATE_KEY set", critical=False)


# ══════════════════════════════════════════════════════════════
# 3. SIGNAL FUSION
# ══════════════════════════════════════════════════════════════
section("3 / 6  —  Signal Fusion (10 sources)")

try:
    from src.agents.signal_fusion_agent import get_fused_signal
    sig = get_fused_signal(verbose=False)
    active = sig["active_sources"]
    score  = sig["score"]
    direction = sig["direction"]

    if active >= 6:
        check("Signal fusion sources", "pass",
              f"{active}/10 active  |  score={score:+.1f}  dir={direction}")
    elif active >= 3:
        check("Signal fusion sources", "warn",
              f"Only {active}/10 active — run collectors first")
    else:
        check("Signal fusion sources", "fail",
              f"Only {active}/10 active — check collector errors")

    # Check individual sources
    for src_name, val in sig.get("sources", {}).items():
        if val is None:
            check(f"  source: {src_name}", "warn", "stale/missing", critical=False)
        else:
            check(f"  source: {src_name}", "pass", f"{val:+.3f}", critical=False)

except Exception as e:
    check("Signal fusion", "fail", str(e)[:80])


# ══════════════════════════════════════════════════════════════
# 4. AI MODEL
# ══════════════════════════════════════════════════════════════
section("4 / 6  —  AI Model Connectivity")

try:
    from src import config as cfg
    ai_model_cfg = getattr(cfg, "AI_MODEL", "claude-haiku-4-5-20251001")
    cprint(f"  {INFO}  Configured model: {ai_model_cfg}", "white")

    # Quick connectivity test using cheapest available model
    tested = False

    if groq and not groq.startswith("your_"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=groq, base_url="https://api.groq.com/openai/v1")
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": "Reply with just: OK"}],
                max_tokens=5, timeout=10
            )
            check("Groq AI (fast/free)", "pass", f"Response: {resp.choices[0].message.content.strip()}")
            tested = True
        except Exception as e:
            check("Groq AI", "warn", str(e)[:60], critical=False)

    if deepseek and not deepseek.startswith("your_") and not tested:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=deepseek, base_url="https://api.deepseek.com")
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": "Reply with just: OK"}],
                max_tokens=5, timeout=15
            )
            check("DeepSeek AI", "pass", f"Response: {resp.choices[0].message.content.strip()}")
            tested = True
        except Exception as e:
            check("DeepSeek AI", "warn", str(e)[:60], critical=False)

    if anthropic and not anthropic.startswith("your_") and not tested:
        try:
            import anthropic as ant
            client = ant.Anthropic(api_key=anthropic)
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=5,
                messages=[{"role": "user", "content": "Reply with just: OK"}]
            )
            check("Claude AI", "pass", f"Response: {resp.content[0].text.strip()}")
            tested = True
        except Exception as e:
            check("Claude AI", "warn", str(e)[:60], critical=False)

    if not tested:
        check("AI model", "fail", "No working AI key found — agents cannot analyze", critical=True)

except Exception as e:
    check("AI model check", "fail", str(e)[:80])


# ══════════════════════════════════════════════════════════════
# 5. CONFIG SAFETY LIMITS
# ══════════════════════════════════════════════════════════════
section("5 / 6  —  Config Safety Limits (src/config.py)")

try:
    from src import config as cfg

    live_trading = getattr(cfg, "LIVE_TRADING", False)
    usd_size     = getattr(cfg, "usd_size", 999)
    max_order    = getattr(cfg, "max_usd_order_size", 999)
    max_loss_pct = getattr(cfg, "MAX_LOSS_PERCENT", 999)
    max_gain_pct = getattr(cfg, "MAX_GAIN_PERCENT", 999)
    sleep_mins   = getattr(cfg, "SLEEP_BETWEEN_RUNS_MINUTES", 0)
    leverage     = getattr(cfg, "HYPERLIQUID_LEVERAGE", 999)
    symbols      = getattr(cfg, "HYPERLIQUID_SYMBOLS", [])

    check("LIVE_TRADING flag",
          "pass" if live_trading else "warn",
          f"{'True — LIVE MODE' if live_trading else 'False — analysis-only (set True to go live)'}")

    check("usd_size (per position)",
          "pass" if usd_size <= 50 else "warn",
          f"${usd_size}  {'✓ conservative' if usd_size <= 50 else '⚠ consider starting smaller'}")

    check("max_usd_order_size",
          "pass" if max_order <= 25 else "warn",
          f"${max_order}")

    check("MAX_LOSS_PERCENT",
          "pass" if max_loss_pct <= 10 else "warn",
          f"{max_loss_pct}%  {'✓' if max_loss_pct <= 10 else '⚠ high — consider tightening'}")

    check("MAX_GAIN_PERCENT",
          "pass" if max_gain_pct <= 20 else "warn",
          f"{max_gain_pct}%")

    check("SLEEP_BETWEEN_RUNS_MINUTES",
          "pass" if sleep_mins >= 15 else "warn",
          f"{sleep_mins} min  {'✓' if sleep_mins >= 15 else '⚠ very frequent — watch API costs'}")

    check("HYPERLIQUID_LEVERAGE",
          "pass" if leverage <= 5 else "warn",
          f"{leverage}x  {'✓ safe' if leverage <= 5 else '⚠ high leverage — significant risk'}")

    check("HYPERLIQUID_SYMBOLS",
          "pass" if symbols else "fail",
          f"{symbols}")

except Exception as e:
    check("Config load", "fail", str(e)[:80])


# ══════════════════════════════════════════════════════════════
# 6. EXCHANGE MANAGER DRY-RUN
# ══════════════════════════════════════════════════════════════
section("6 / 6  —  Exchange Manager Dry-Run")

if hl_key and not hl_key.startswith("your_") and len(hl_key) > 10:
    try:
        from src.exchange_manager import ExchangeManager
        em = ExchangeManager('hyperliquid')
        val = em.get_account_value()
        bal = em.get_balance()
        check("ExchangeManager init", "pass", f"account=${val:,.2f}  available=${bal:,.2f}")

        # Check BTC price fetch
        btc_price = em.get_current_price("BTC")
        check("Price feed (BTC)", "pass", f"${btc_price:,.2f}")

        # Check OHLCV data
        df = em.get_data("BTC", days_back=1, timeframe="15m")
        if df is not None and not df.empty:
            check("OHLCV data (BTC 15m)", "pass", f"{len(df)} bars fetched")
        else:
            check("OHLCV data", "warn", "No data returned", critical=False)

    except Exception as e:
        check("ExchangeManager", "fail", str(e)[:80])
else:
    check("ExchangeManager dry-run", "warn",
          "Skipped — set HYPER_LIQUID_ETH_PRIVATE_KEY first", critical=False)


# ══════════════════════════════════════════════════════════════
# FINAL VERDICT
# ══════════════════════════════════════════════════════════════
cprint(f"\n{'═'*60}", "cyan")
cprint("  LIVE TRADING READINESS VERDICT", "cyan", attrs=["bold"])
cprint(f"{'═'*60}", "cyan")

critical_fails  = [r for r in results if r[1] == "fail"  and r[2]]
critical_warns  = [r for r in results if r[1] == "warn"  and r[2]]
optional_warns  = [r for r in results if r[1] == "warn"  and not r[2]]
passes          = [r for r in results if r[1] == "pass"]

cprint(f"  {PASS}  {len(passes)} checks passed", "green")
if optional_warns:
    cprint(f"  {WARN}  {len(optional_warns)} optional warnings (non-blocking)", "yellow")
if critical_warns:
    cprint(f"  {WARN}  {len(critical_warns)} warnings (review before going live)", "yellow")
if critical_fails:
    cprint(f"  {FAIL}  {len(critical_fails)} critical failures (MUST FIX)", "red")

cprint(f"{'─'*60}", "cyan")

if not critical_fails:
    cprint("\n  🚀  READY TO GO LIVE!", "green", attrs=["bold"])
    cprint("\n  Next steps:", "white")
    cprint("    1. Set LIVE_TRADING = True  in src/config.py", "white")
    cprint("    2. Set usd_size = 10        in src/config.py  (start small!)", "white")
    cprint("    3. python src/main.py", "white")
else:
    cprint("\n  🛑  NOT READY — fix the red items above first.", "red", attrs=["bold"])
    cprint("\n  Fix checklist:", "white")
    for label, _, _ in critical_fails:
        cprint(f"    • {label}", "red")
    cprint("\n  See ENV_SETUP.md for setup instructions.", "white")

cprint(f"\n{'═'*60}\n", "cyan")

if __name__ == "__main__":
    pass  # all checks run at import time above
