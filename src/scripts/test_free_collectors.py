"""
🌙 Moon Dev — Free Collectors Integration Test
Verifies all 5 free collectors work and signal fusion sees them.
Run: python src/scripts/test_free_collectors.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from termcolor import cprint

results = {}

# ── 1. OI Collector ──────────────────────────────────────────────────────────
cprint("\n=== Test 1: OI Collector (Hyperliquid metaAndAssetCtxs) ===", "cyan")
from src.agents.oi_collector import collect as collect_oi, save_to_csv as save_oi
data = collect_oi()
if data:
    save_oi(data)
    d = data[0]
    cprint(f"  PASS — BTC ${d['btc_oi']/1e9:.2f}B  ETH ${d['eth_oi']/1e9:.2f}B  "
           f"SOL ${d['sol_oi']/1e9:.2f}B  Δ={d['total_change_pct']:+.3f}%", "green")
    results["OI"] = "PASS"
else:
    cprint("  FAIL — no data", "red")
    results["OI"] = "FAIL"

# ── 2. Liquidation Collector ──────────────────────────────────────────────────
cprint("\n=== Test 2: Liquidation Collector (HL native + OI proxy) ===", "cyan")
from src.agents.liquidation_collector import collect as collect_liq, save_to_csv as save_liq
data = collect_liq()
if data:
    save_liq(data)
    d = data[0]
    cprint(f"  PASS — long=${d['long_liq_usd']:,.0f}  short=${d['short_liq_usd']:,.0f}  "
           f"total=${d['total_liq_usd']:,.0f}", "green")
    results["Liquidation"] = "PASS"
else:
    cprint("  FAIL — no data", "red")
    results["Liquidation"] = "FAIL"

# ── 3. Order Flow Collector ───────────────────────────────────────────────────
cprint("\n=== Test 3: Order Flow Collector (Hyperliquid recent_trades) ===", "cyan")
from src.agents.orderflow_collector import collect as collect_of, save_to_csv as save_of
data = collect_of()
if data:
    save_of(data)
    d = data[0]
    cprint(f"  PASS — buy=${d['buy_volume']:,.0f}  sell=${d['sell_volume']:,.0f}  "
           f"imbalance={d['imbalance_ratio']:+.4f}", "green")
    results["OrderFlow"] = "PASS"
else:
    cprint("  FAIL — no data", "red")
    results["OrderFlow"] = "FAIL"

# ── 4. HLP Collector ─────────────────────────────────────────────────────────
cprint("\n=== Test 4: HLP Collector (Hyperliquid vault API) ===", "cyan")
from src.agents.hlp_collector import collect as collect_hlp, save_to_csv as save_hlp
data = collect_hlp()
if data:
    save_hlp(data)
    d = data[0]
    cprint(f"  PASS — net_delta=${d['net_delta']:,.0f}  sentiment={d['sentiment_score']:+.4f}  "
           f"contrarian_long={d['is_contrarian_long']}", "green")
    results["HLP"] = "PASS"
else:
    cprint("  FAIL — no data", "red")
    results["HLP"] = "FAIL"

# ── 5. Smart Money Collector ──────────────────────────────────────────────────
cprint("\n=== Test 5: Smart Money Collector (Hyperliquid leaderboard) ===", "cyan")
from src.agents.smart_money_collector import collect as collect_sm, save_to_csv as save_sm
data = collect_sm()
if data:
    save_sm(data)
    d = data[0]
    cprint(f"  PASS — direction={d['direction']}  score={d['signal_score']:+.4f}", "green")
    results["SmartMoney"] = "PASS"
else:
    cprint("  FAIL — no data (leaderboard unavailable)", "yellow")
    results["SmartMoney"] = "FAIL"

# ── 6. Signal Fusion ─────────────────────────────────────────────────────────
cprint("\n=== Test 6: Signal Fusion (end-to-end) ===", "cyan")
from src.agents.signal_fusion_agent import get_fused_signal
sig = get_fused_signal(verbose=True)

active = sig["active_sources"]
score  = sig["score"]
direction = sig["direction"]
confidence = sig["confidence"]

if active >= 3:
    cprint(f"\n  PASS — {active}/7 sources active | score={score:+.1f} | "
           f"dir={direction} | conf={confidence:.1f}%", "green")
    results["SignalFusion"] = f"PASS ({active}/7 sources)"
else:
    cprint(f"\n  WARN — only {active}/7 sources active", "yellow")
    results["SignalFusion"] = f"WARN ({active}/7 sources)"

# ── Summary ───────────────────────────────────────────────────────────────────
cprint("\n" + "═" * 55, "cyan")
cprint("🌙  FREE COLLECTORS TEST SUMMARY", "cyan")
cprint("═" * 55, "cyan")
for name, status in results.items():
    colour = "green" if "PASS" in status else ("yellow" if "WARN" in status else "red")
    cprint(f"  {name:<15} {status}", colour)

passed = sum(1 for v in results.values() if "PASS" in v)
cprint(f"\n  {passed}/{len(results)} tests passed", "white")
cprint("═" * 55, "cyan")
cprint("\n✅ MoonDev API key no longer required for signal fusion!", "green")
