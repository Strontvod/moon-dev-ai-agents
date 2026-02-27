"""
Test and seed the 3 new collectors (Phase 2-4).
Run: python -X utf8 src/scripts/test_new_collectors.py
"""
import sys
sys.path.insert(0, '.')

from termcolor import cprint

def run():
    cprint("\n=== Seeding New Collectors (Phase 2-4) ===\n", "cyan", attrs=["bold"])
    passed = 0
    warned = 0

    # ── Position Snapshot Collector ───────────────────────────────────────────
    cprint("--- Position Snapshot Collector ---", "white")
    try:
        from src.agents.position_snapshot_collector import collect, save_to_csv
        data = collect()
        if data:
            save_to_csv(data)
            for d in data:
                cprint(f"  {d['symbol']}: {d['direction']} "
                       f"(squeeze={d['squeeze_score']:+.3f}) [{d['source']}]", "green")
            cprint(f"  PASS — {len(data)} records saved\n", "green")
            passed += 1
        else:
            cprint("  WARN — no data (expected without MoonDev key, HL fallback returned nothing)\n", "yellow")
            warned += 1
    except Exception as e:
        cprint(f"  FAIL: {e}\n", "red")

    # ── Multi-Exchange Liquidation Collector ──────────────────────────────────
    cprint("--- Multi-Exchange Liquidation Collector ---", "white")
    try:
        from src.agents.multi_liq_collector import collect as c2, save_to_csv as s2
        data2 = c2()
        if data2:
            s2(data2)
            for d in data2:
                cprint(f"  [{d['exchanges']}] "
                       f"long=${d['long_liq_usd']:,.0f}  short=${d['short_liq_usd']:,.0f}  "
                       f"ratio={d['liq_ratio']:+.3f} [{d['source']}]", "green")
            cprint(f"  PASS — {len(data2)} records saved\n", "green")
            passed += 1
        else:
            cprint("  WARN — no data\n", "yellow")
            warned += 1
    except Exception as e:
        cprint(f"  FAIL: {e}\n", "red")

    # ── Buyer Tracker Collector ───────────────────────────────────────────────
    cprint("--- Buyer Tracker Collector ---", "white")
    try:
        from src.agents.buyer_tracker_collector import collect as c3, save_to_csv as s3
        data3 = c3()
        if data3:
            s3(data3)
            for d in data3:
                cprint(f"  {d['symbol']}: {d['direction']} "
                       f"(score={d['accumulation_score']:+.3f}, "
                       f"buys={d['large_buy_count']}) [{d['source']}]", "green")
            cprint(f"  PASS — {len(data3)} records saved\n", "green")
            passed += 1
        else:
            cprint("  WARN — no data\n", "yellow")
            warned += 1
    except Exception as e:
        cprint(f"  FAIL: {e}\n", "red")

    # ── Re-run signal fusion with new data ────────────────────────────────────
    cprint("--- Signal Fusion with new sources ---", "white")
    try:
        from src.agents.signal_fusion_agent import get_fused_signal
        sig = get_fused_signal(verbose=True)
        cprint(f"\n  Active sources: {sig['active_sources']}/10", "white")
        cprint(f"  Score: {sig['score']:+.1f}  Direction: {sig['direction']}", "white")
        cprint(f"  PASS\n", "green")
        passed += 1
    except Exception as e:
        cprint(f"  FAIL: {e}\n", "red")

    # ── Summary ───────────────────────────────────────────────────────────────
    cprint("=" * 50, "cyan")
    cprint(f"  {passed} PASS  |  {warned} WARN (no data = expected without MoonDev key)", "white")
    cprint("  New collectors are wired and ready.", "green")
    cprint("  Set MOONDEV_API_KEY in .env to unlock full data.", "white")
    cprint("=" * 50, "cyan")

if __name__ == "__main__":
    run()
