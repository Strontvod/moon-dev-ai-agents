# 🌙 Signal Fusion Agent — Integration Guide

How to wire `signal_fusion_agent.py` into the existing trading pipeline.

---

## What It Does

Combines **10 data streams** into one pre-trade gate:

| Source | File Read | Weight | Edge | API |
|---|---|---|---|---|
| **Funding** | `funding_history.csv` | 20% | Contrarian: extreme funding = reversal | Free (HL) |
| **OI** | `oi_history.csv` | 12% | Position size momentum | Free (HL) |
| **Smart Money** | `smart_money_history.csv` | 12% | Top 100 profitable traders | Free (HL) |
| **Sentiment** | `sentiment_history.csv` | 13% | Social momentum | Twitter |
| **Liquidation** | `liquidation_history.csv` | 10% | Forced-exit pressure | Free (HL) |
| **Order Flow** | `orderflow_history.csv` | 8% | Buy/sell imbalance | Free (HL) |
| **Position Snapshot** | `position_snapshot_history.csv` | 10% | Squeeze signals (positions near liq) | Free fallback / MoonDev |
| **HLP** | `hlp_history.csv` | 5% | Contrarian HLP positioning | Free (HL) |
| **Multi-Liq** | `multi_liq_history.csv` | 5% | 4-exchange combined liquidations | MoonDev API |
| **Buyer Tracker** | `buyer_history.csv` | 5% | $5k+ buyer accumulation | Free fallback / MoonDev |

Output: score from -100 (strong short) → +100 (strong long), plus a `direction` label and `confidence` %.

**Without MoonDev key: 8/10 sources active (82% signal weight)**
**With MoonDev key: 10/10 sources active (100% signal weight)**

---

## Live Trading Gate

The system has a `LIVE_TRADING` flag in `src/config.py`:

```python
# src/config.py
LIVE_TRADING = False   # ANALYSIS-ONLY: strategy runs, no orders, no background collectors
LIVE_TRADING = True    # LIVE: all 8 background collectors run, real orders placed
```

**When `LIVE_TRADING = False` (default):**
- Strategy analysis runs (reads existing CSV data)
- NO background data collectors run (saves API calls)
- NO real orders placed
- Safe for development and backtesting

**When `LIVE_TRADING = True`:**
- All 8 background collectors refresh every cycle
- Risk agent checks position limits
- Trading/CopyBot agents can place real orders

---

## Option A — Pre-trade gate in `main.py`

Add this block just before trading agents run in `src/main.py`:

```python
# ─── Signal Fusion Gate ───────────────────────────────────────────────────────
from src.agents.signal_fusion_agent import should_trade

ok, reason, sig = should_trade(
    min_score=25.0,       # Must be outside neutral band ±25
    min_confidence=40.0,  # At least 40% source agreement
    min_sources=3,        # At least 3 data sources must be fresh
)

if not ok:
    cprint(f"⛔ Signal Fusion: {reason}", "yellow")
    cprint(f"   Score: {sig['score']:+.1f} | Direction: {sig['direction']}", "yellow")
    # Skip trading this cycle — go to sleep
    time.sleep(60 * SLEEP_BETWEEN_RUNS_MINUTES)
    continue

cprint(f"✅ Signal Fusion: {sig['direction']} ({sig['score']:+.1f}) — trading allowed", "green")
# ... rest of agent execution
```

---

## Option B — Signal-biased trading in `trading_agent.py`

Add to the top of the agent file, after imports:

```python
# Optional: signal fusion bias
try:
    from src.agents.signal_fusion_agent import get_fused_signal
    _fusion = get_fused_signal(verbose=False)
    FUSION_SCORE     = _fusion.get("score", 0)
    FUSION_DIRECTION = _fusion.get("direction", "NEUTRAL")
    FUSION_ACTIVE    = True
except Exception:
    FUSION_SCORE     = 0
    FUSION_DIRECTION = "NEUTRAL"
    FUSION_ACTIVE    = False
```

Then inside the prompt you pass to the LLM, inject the fusion context:

```python
fusion_context = f"""
Current Multi-Source Signal Fusion (10 sources):
  Score: {FUSION_SCORE:+.1f} / 100
  Direction: {FUSION_DIRECTION}
  (Combines: funding + OI + smart money + liquidation + order flow +
             position snapshots + HLP + multi-exchange liqs + buyer tracker)

Weight this as additional macro context when forming your trading view.
"""
```

---

## Option C — Standalone run before bot starts

```bash
python src/agents/signal_fusion_agent.py
```

Output example:
```
══════════════════════════════════════════════════════
🌙  SIGNAL FUSION RESULT
══════════════════════════════════════════════════════
  Score:       -0.7 / 100
  Direction:   NEUTRAL
  Confidence:  20.0%
  Sources:     8/10 active
──────────────────────────────────────────────────────
  sentiment          N/A (stale)
  funding            +0.000
  oi                 +0.001
  liquidation        +0.000
  smart_money        +0.185
  orderflow          -0.978
  hlp                -0.000
  position_snapshot  -0.001
  multi_liq          N/A (stale)
  buyer_tracker      +1.000
══════════════════════════════════════════════════════
```

---

## Data Format Reference

### `src/data/position_snapshot_history.csv`
```csv
timestamp,symbol,at_risk_long_usd,at_risk_short_usd,squeeze_score,direction,source
2026-02-18T14:00:00+00:00,BTC,0.0,0.0,+0.000,NEUTRAL,hl_fallback
```

### `src/data/multi_liq_history.csv`
```csv
timestamp,long_liq_usd,short_liq_usd,total_liq_usd,liq_ratio,exchanges,source
2026-02-18T14:00:00+00:00,15000000,4000000,19000000,+0.580,HL+Binance+Bybit+OKX,moondev
```

### `src/data/buyer_history.csv`
```csv
timestamp,symbol,large_buy_count,large_buy_usd,accumulation_score,direction,source
2026-02-18T14:00:00+00:00,BTC,12,85000.0,+1.000,ACCUMULATING,hl_fallback
```

---

## Adjusting Weights

Edit `WEIGHTS` at the top of `signal_fusion_agent.py`:

```python
WEIGHTS = {
    "sentiment":          0.13,  # Reduce if Twitter data is noisy
    "funding":            0.20,  # Keep high — funding is a proven edge
    "oi":                 0.12,
    "liquidation":        0.10,
    "smart_money":        0.12,
    "orderflow":          0.08,
    "hlp":                0.05,
    "position_snapshot":  0.10,  # Squeeze signals — high value
    "multi_liq":          0.05,  # Needs MoonDev key for full data
    "buyer_tracker":      0.05,
}
# Must always sum to 1.0
```

**Tip:** Weights auto-renormalize for available sources — if `multi_liq` is stale,
its 5% weight is redistributed proportionally across active sources.

---

## Running Tests

```bash
# Test all free collectors (original 6)
python -X utf8 src/scripts/test_free_collectors.py

# Test new collectors (Phase 2-4)
python -X utf8 src/scripts/test_new_collectors.py

# Full integration test (gate + strategy_agent)
python -X utf8 src/scripts/test_integration.py

# Run signal fusion standalone
python src/agents/signal_fusion_agent.py
```

---

## Backtest Tip

Check `src/data/signal_fusion/signal_history.csv` after a few days of running.
Plot `score` vs next-bar price change to validate the signal is actually predictive before trusting it with real money.

---

*Built with 🌙 by Moon Dev*
