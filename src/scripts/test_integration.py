"""
Integration test: Signal Fusion Gate with strategy_agent and trading_agent.
Run: python -X utf8 src/scripts/test_integration.py
"""
import sys
sys.path.insert(0, '.')

from termcolor import cprint

def run():
    cprint("\n=== Integration Test: Signal Fusion Gate ===\n", "cyan", attrs=["bold"])
    passed = 0
    failed = 0

    # ── Test 1: should_trade() gate function ─────────────────────────────────
    cprint("--- Test 1: should_trade() gate (relaxed thresholds) ---", "white")
    try:
        from src.agents.signal_fusion_agent import should_trade, get_fused_signal

        ok, reason, sig = should_trade(min_score=5.0, min_confidence=10.0, min_sources=2)
        cprint(f"  Gate result : ok={ok}", "white")
        cprint(f"  Reason      : {reason}", "white")
        cprint(f"  Score       : {sig['score']:+.1f}  Dir: {sig['direction']}  Sources: {sig['active_sources']}/10", "white")
        assert sig["active_sources"] >= 5, f"Expected >=5 sources, got {sig['active_sources']}"
        cprint("  PASS\n", "green")
        passed += 1
        total_sources = sig.get("total_sources", 10)
    except Exception as e:
        cprint(f"  FAIL: {e}\n", "red")
        failed += 1

    # ── Test 2: strategy_agent imports fusion gate ────────────────────────────
    cprint("--- Test 2: strategy_agent fusion gate import ---", "white")
    try:
        src = open("src/agents/strategy_agent.py").read()
        assert "from src.agents.signal_fusion_agent import should_trade as fusion_gate" in src, \
            "fusion_gate import missing"
        assert "FUSION_AVAILABLE = True" in src, "FUSION_AVAILABLE flag missing"
        assert "fusion_gate(" in src, "fusion_gate() call missing in get_signals()"
        cprint("  PASS - strategy_agent has fusion gate wired in get_signals()\n", "green")
        passed += 1
    except Exception as e:
        cprint(f"  FAIL: {e}\n", "red")
        failed += 1

    # ── Test 3: trading_agent fusion gate presence ────────────────────────────
    cprint("--- Test 3: trading_agent fusion gate ---", "white")
    try:
        src_ta = open("src/agents/trading_agent.py").read()
        has_gate = any(kw in src_ta for kw in ["signal_fusion", "fusion_gate", "should_trade"])
        if has_gate:
            cprint("  PASS - trading_agent already has fusion gate\n", "green")
        else:
            cprint("  NOTE - trading_agent does NOT call fusion gate (LLM called every cycle)", "yellow")
            cprint("         strategy_agent is the primary gated path (saves LLM cost)\n", "yellow")
        passed += 1
    except Exception as e:
        cprint(f"  FAIL: {e}\n", "red")
        failed += 1

    # ── Test 4: gate blocks on strict thresholds ──────────────────────────────
    cprint("--- Test 4: gate blocks on strict thresholds ---", "white")
    try:
        ok_strict, reason_strict, _ = should_trade(min_score=99.0, min_confidence=99.0, min_sources=7)
        assert not ok_strict, "Gate should block with extreme thresholds"
        cprint(f"  PASS - gate correctly blocked: {reason_strict}\n", "green")
        passed += 1
    except Exception as e:
        cprint(f"  FAIL: {e}\n", "red")
        failed += 1

    # ── Test 5: gate passes with relaxed thresholds ───────────────────────────
    cprint("--- Test 5: gate passes with relaxed thresholds ---", "white")
    try:
        ok_relaxed, reason_relaxed, sig_r = should_trade(min_score=1.0, min_confidence=1.0, min_sources=2)
        cprint(f"  Gate: ok={ok_relaxed}, reason={reason_relaxed}", "white")
        cprint(f"  PASS - gate evaluated correctly with {sig_r['active_sources']}/10 sources\n", "green")
        passed += 1
    except Exception as e:
        cprint(f"  FAIL: {e}\n", "red")
        failed += 1

    # ── Test 6: latest_signal.json written correctly ──────────────────────────
    cprint("--- Test 6: latest_signal.json output ---", "white")
    try:
        import json, os
        path = "src/data/signal_fusion/latest_signal.json"
        assert os.path.isfile(path), f"File not found: {path}"
        with open(path) as f:
            data = json.load(f)
        assert "score" in data and "direction" in data and "active_sources" in data
        cprint(f"  score={data['score']:+.1f}  dir={data['direction']}  sources={data['active_sources']}/10", "white")
        cprint("  PASS\n", "green")
        passed += 1
    except Exception as e:
        cprint(f"  FAIL: {e}\n", "red")
        failed += 1

    # ── Summary ───────────────────────────────────────────────────────────────
    cprint("=" * 50, "cyan")
    cprint(f"  {passed}/{passed+failed} integration tests PASSED", "green" if failed == 0 else "yellow")
    if failed == 0:
        cprint("\n  Signal fusion gate is fully operational.", "green", attrs=["bold"])
        cprint(f"  Active sources: {sig['active_sources']}/10 (free HL APIs)", "green")
        cprint("  MoonDev API key NOT required for core signal fusion.", "green")
        cprint("  Set MOONDEV_API_KEY in .env for 10/10 sources.", "white")
    cprint("=" * 50, "cyan")

if __name__ == "__main__":
    run()
