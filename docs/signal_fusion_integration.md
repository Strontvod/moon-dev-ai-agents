# 🌙 Signal Fusion Agent — Integration Guide

How to wire `signal_fusion_agent.py` into the existing trading pipeline.

---

## What It Does

Combines 4 data streams into one pre-trade gate:

| Source | File Read | Weight | Edge |
|---|---|---|---|
| **Sentiment** | `src/data/sentiment_history.csv` | 25% | Social momentum |
| **Funding** | `src/data/funding_history.csv` | 30% | Contrarian: extreme funding = reversal |
| **OI / Whale** | `src/data/oi_history.csv` | 25% | Position size momentum |
| **Liquidation** | `src/data/liquidation_history.csv` | 20% | Forced-exit pressure |

Output: score from -100 (strong short) → +100 (strong long), plus a `direction` label and `confidence` %.

---

## Option A — Pre-trade gate in `main.py`

Add this block just before trading agents run in `src/main.py`:

```python
# ─── Signal Fusion Gate ───────────────────────────────────────────────────────
from src.agents.signal_fusion_agent import should_trade

ok, reason, sig = should_trade(
    min_score=25.0,       # Must be outside neutral band ±25
    min_confidence=40.0,  # At least 40% source agreement
    min_sources=2,        # At least 2 data sources must be fresh
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

Then inside the prompt you pass to the swarm/LLM, inject the fusion context:

```python
fusion_context = f"""
Current Multi-Source Signal Fusion:
  Score: {FUSION_SCORE:+.1f} / 100
  Direction: {FUSION_DIRECTION}
  (Combines: sentiment + funding rate + open interest + liquidation data)

Weight this as additional macro context when forming your trading view.
"""

# Add fusion_context to your existing system prompt
system_prompt = base_system_prompt + "\n\n" + fusion_context
```

---

## Option C — Standalone run before bot starts

Just run it manually or via cron to check conditions:

```bash
python src/agents/signal_fusion_agent.py
```

Output example:
```
══════════════════════════════════════════════════════
🌙  SIGNAL FUSION RESULT
══════════════════════════════════════════════════════
  Score:       +42.5 / 100
  Direction:   LONG
  Confidence:  75.0%
  Sources:     3/4 active
──────────────────────────────────────────────────────
  sentiment      +0.312
  funding        +0.750
  oi             +0.250
  liquidation    N/A (stale)
══════════════════════════════════════════════════════
```

---

## Data Format Reference

For each source CSV the agent reads, here's the expected column format.
If your agent outputs different column names, adjust the reader functions in `signal_fusion_agent.py`.

### `src/data/sentiment_history.csv`
```csv
timestamp,sentiment_score,token
2026-02-18T14:00:00,0.312,BTC
```

### `src/data/funding_history.csv`
```csv
timestamp,symbol,annual_rate,hourly_rate
2026-02-18T14:00:00,BTC,24.5,0.00279
```

### `src/data/oi_history.csv`
```csv
timestamp,symbol,oi_usd,oi_change_pct
2026-02-18T14:00:00,BTC,9200000000,+3.2
```

### `src/data/liquidation_history.csv`
```csv
timestamp,symbol,long_liq_usd,short_liq_usd
2026-02-18T14:00:00,BTC,15000000,4000000
```

---

## Adjusting Weights

Edit `WEIGHTS` at the top of `signal_fusion_agent.py`:

```python
WEIGHTS = {
    "sentiment":   0.25,   # Reduce if Twitter data is noisy
    "funding":     0.30,   # Keep high — funding is a proven edge
    "oi":          0.25,
    "liquidation": 0.20,
}
# Must always sum to 1.0
```

**Tip:** If you only have 2 reliable sources (e.g. funding + OI), just set the others to 0 and renormalize — the agent auto-adjusts weights for available sources.

---

## Backtest Tip

Check `src/data/signal_fusion/signal_history.csv` after a few days of running.
Plot `score` vs next-bar price change to validate the signal is actually predictive before trusting it with real money.

---

*Built with 🌙 by Moon Dev*
