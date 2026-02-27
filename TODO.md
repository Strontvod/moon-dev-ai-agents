# 🌙 Moon Dev — Algotrading System Enhancement Plan
## Phase 1–7: Live Gate + New Signal Sources + AI Chat API

---

## ✅ Completed (Previous Session)

- [x] 1. Create `src/agents/oi_collector.py` — Free OI via Hyperliquid `metaAndAssetCtxs`
- [x] 2. Create `src/agents/liquidation_collector.py` — Free liquidations via HL native + OI-change proxy
- [x] 3. Update `src/agents/orderflow_collector.py` — Primary: HL `recentTrades`; Fallback: MoonDev API
- [x] 4. Update `src/agents/hlp_collector.py` — Primary: HL `vaultDetails`; Fallback: MoonDev API
- [x] 5. Update `src/agents/smart_money_collector.py` — Primary: HL leaderboard; Fallback: MoonDev API
- [x] 6. Update `src/main.py` — Import oi_collector + liquidation_collector; added to signal fusion refresh loop
- [x] 7. Fix `src/agents/signal_fusion_agent.py` — UTC timezone comparison bug fixed

---

## ✅ Completed (Current Session)

### Phase 1 — Live Trading Gate
- [x] 1.1 Add `LIVE_TRADING = False` flag to `src/config.py`
- [x] 1.2 Update `src/main.py` — gate background collectors on `LIVE_TRADING` flag
- [x] 1.3 Print clear status banner (LIVE vs ANALYSIS-ONLY mode)

### Phase 2 — Position Snapshot Collector (Squeeze Signals)
- [x] 2.1 Create `src/agents/position_snapshot_collector.py`
       — MoonDev `/api/position_snapshots/symbol/{symbol}` primary
       — Free HL fallback (funding rate + OI as squeeze proxy)
       — Writes `src/data/position_snapshot_history.csv`
       — TEST: PASS — 3 records (BTC/ETH/SOL via HL fallback)

### Phase 3 — Multi-Exchange Liquidation Collector
- [x] 3.1 Create `src/agents/multi_liq_collector.py`
       — MoonDev `/api/all_liquidations/` (HL + Binance + Bybit + OKX)
       — Fallback to existing `liquidation_collector.py` (HL-only)
       — Writes `src/data/multi_liq_history.csv`
       — TEST: WARN — requires MoonDev API key for full data

### Phase 4 — Buyer Tracker Collector (Accumulation Signals)
- [x] 4.1 Create `src/agents/buyer_tracker_collector.py`
       — MoonDev `/buyers/` endpoint ($5k+ buyers on BTC/ETH/SOL)
       — Free HL fallback (recentTrades filtered for large buys)
       — Writes `src/data/buyer_history.csv`
       — TEST: PASS — data collected via HL fallback

### Phase 5 — Signal Fusion Enhancement
- [x] 5.1 Update `src/agents/signal_fusion_agent.py`
       — Added 3 new sources: position_snapshot (10%), multi_liq (5%), buyer_tracker (5%)
       — Rebalanced all weights to sum to 1.0 (10 sources total)
       — Added reader functions for new CSVs
       — TEST: PASS — 8/10 sources active (up from 6/7)

### Phase 6 — MoonDev AI Chat API Model
- [x] 6.1 Create `src/models/moondev_model.py`
       — OpenAI-compatible drop-in using MOONDEV_API_KEY
       — Graceful fallback to groq if no key
- [x] 6.2 Update `src/models/model_factory.py` — added 'moondev' model type
- [x] 6.3 Update `src/config.py` — added moondev model option comment

### Phase 7 — Documentation Update
- [x] 7.1 Update `docs/signal_fusion_integration.md` — new sources + weights table
- [x] 7.2 Final integration test run — 6/6 PASS, 8/10 sources active

---

## ✅ Completed (Session 3)

### Live Trading Readiness Check
- [x] 8.1 Create `src/scripts/check_live_trading.py`
       — 6-section readiness check: env vars, HL connection, signal fusion, AI model, config limits, exchange dry-run
       — TEST: 26/26 checks PASS on live system
       — Account: 0x4B23...66b2  |  Balance: $42.96  |  BTC: $67,354
       — Claude AI live-tested ✅  |  8/10 signal sources active ✅
- [x] 8.2 Update `ENV_SETUP.md` — added check_live_trading.py to First Run Order

### Market Entry Timing Analysis
- [x] 9.1 Create `src/scripts/market_snapshot.py`
       — Live market snapshot: prices, funding, OI, OHLCV technicals (EMA, RSI, ATR, volume)
       — Per-symbol entry scoring (0–100) with factor breakdown
       — Signal fusion integration for directional bias
       — TEST: Live run 2026-02-27 02:23 UTC
         BTC: 83/100 🟢 GOOD ENTRY (RSI 41.9, Funding +0.0006%, Vol 1.4x)
         SOL: 78/100 🟢 GOOD ENTRY
         ETH: 70/100 🟢 GOOD ENTRY (weak volume 0.3x)
       — Verdict: BTC best opportunity, conditions aligned for entry

---

## 📊 Final Signal Fusion Weight Table

| Source             | Weight | Status                                         |
|--------------------|--------|------------------------------------------------|
| Funding            | 20%    | ✅ Free (HL fundingHistory)                    |
| OI                 | 12%    | ✅ Free (HL metaAndAssetCtxs)                  |
| Smart Money        | 12%    | ✅ Free (HL leaderboard)                       |
| Sentiment          | 13%    | ❌ Twitter (unchanged)                         |
| Liquidation        | 10%    | ✅ Free (HL native + OI proxy)                 |
| Order Flow         | 8%     | ✅ Free (HL recentTrades)                      |
| Position Snapshot  | 10%    | ✅ Free fallback / 🔑 MoonDev full data        |
| HLP                | 5%     | ✅ Free (HL vaultDetails)                      |
| Multi-Liq          | 5%     | 🔑 MoonDev API (4-exchange combined)           |
| Buyer Tracker      | 5%     | ✅ Free fallback / 🔑 MoonDev full data        |

**Without MoonDev key : 8/10 sources active (82% signal weight)**
**With MoonDev key    : 10/10 sources active (100% signal weight)**

---

## 🚦 Live Trading Gate

Set in `src/config.py`:
```python
LIVE_TRADING = False   # ANALYSIS-ONLY: strategy runs, no orders, no background collectors
LIVE_TRADING = True    # LIVE: all 8 background collectors run, real orders placed
```

## 🤖 AI Model Options (config.py)

```python
AI_MODEL = "claude-haiku-4-5-20251001"  # Fast Claude (default)
AI_MODEL = "moondev"                     # MoonDev AI Chat API (same key, no extra cost)
AI_MODEL = "deepseek"                    # DeepSeek R1 (cheap reasoning)
AI_MODEL = "groq"                        # Groq (free & fast)
```

---

## 🚀 Quick Reference Commands

```bash
# ── Pre-flight ────────────────────────────────────────────────
# Full readiness check (run BEFORE going live)
python -X utf8 src/scripts/check_live_trading.py

# Find best entry moment (run anytime — live market analysis)
python -X utf8 src/scripts/market_snapshot.py

# ── Signal Fusion ─────────────────────────────────────────────
# Run signal fusion standalone (shows all 10 sources)
python src/agents/signal_fusion_agent.py

# ── Testing ───────────────────────────────────────────────────
# Full integration test (6/6 gate tests)
python -X utf8 src/scripts/test_integration.py

# Test original 6 free collectors (OI, liq, orderflow, HLP, smart money, funding)
python -X utf8 src/scripts/test_free_collectors.py

# Test new collectors (position snapshot, multi-liq, buyer tracker)
python -X utf8 src/scripts/test_new_collectors.py

# ── Individual Collectors (run standalone) ────────────────────
python src/agents/oi_collector.py
python src/agents/liquidation_collector.py
python src/agents/orderflow_collector.py
python src/agents/hlp_collector.py
python src/agents/smart_money_collector.py
python src/agents/position_snapshot_collector.py
python src/agents/multi_liq_collector.py
python src/agents/buyer_tracker_collector.py
python src/agents/funding_collector.py

# ── Main Bot ──────────────────────────────────────────────────
# Start full orchestrator (set LIVE_TRADING=True in config.py first)
python src/main.py

# Run individual agents standalone
python src/agents/strategy_agent.py
python src/agents/risk_agent.py
python src/agents/trading_agent.py
python src/agents/whale_agent.py
python src/agents/liquidation_agent.py

# ── Backtesting ───────────────────────────────────────────────
python src/agents/rbi_agent.py          # AI strategy generation + backtest
python src/agents/rbi_agent_v3.py       # Latest RBI version

# ── Environment ───────────────────────────────────────────────
conda activate tflow
pip install -r requirements.txt
```

---

## 📁 Key File Locations

| Purpose | File |
|---|---|
| Global config + LIVE_TRADING flag | `src/config.py` |
| API keys | `src/.env` |
| Signal fusion output | `src/data/signal_fusion/latest_signal.json` |
| Signal fusion history | `src/data/signal_fusion/signal_history.csv` |
| OI history | `src/data/oi_history.csv` |
| Liquidation history | `src/data/liquidation_history.csv` |
| Smart money history | `src/data/smart_money_history.csv` |
| Order flow history | `src/data/orderflow_history.csv` |
| HLP history | `src/data/hlp_history.csv` |
| Position snapshot history | `src/data/position_snapshot_history.csv` |
| Buyer tracker history | `src/data/buyer_history.csv` |
| Multi-liq history | `src/data/multi_liq_history.csv` |
| Funding history | `src/data/funding_history.csv` |
