# 🌙 Moon Dev Bot — Environment Setup Guide

Complete `.env` configuration reference. Copy `src/.env_example` to `src/.env` and fill in the keys below.

---

## 🤖 AI / LLM Keys

| Variable | Where to Get It | Notes |
|---|---|---|
| `ANTHROPIC_KEY` | https://console.anthropic.com → API Keys | Claude (default model) |
| `OPENAI_KEY` | https://platform.openai.com/api-keys | GPT-4 / GPT-5, used in rbi_agent |
| `DEEPSEEK_KEY` | https://platform.deepseek.com | Cheapest for backtests (~$0.03/run) |
| `GROQ_API_KEY` | https://console.groq.com/keys | Fastest inference, free tier available |
| `GEMINI_KEY` | https://aistudio.google.com/app/apikey | Google Gemini |
| `XAI_API_KEY` | https://console.x.ai | Grok (optional) |
| `OPENROUTER_KEY` | https://openrouter.ai/keys | Multi-model router (optional) |

**Start with:** `ANTHROPIC_KEY` + `DEEPSEEK_KEY` — covers 95% of agents.

---

## 📊 Market Data Keys

| Variable | Where to Get It | Notes |
|---|---|---|
| `BIRDEYE_API_KEY` | https://birdeye.so/developer | Solana token data (15k+ tokens) |
| `COINGECKO_API_KEY` | https://www.coingecko.com/en/api | Token metadata, gainers/losers |
| `MOONDEV_API_KEY` | https://algotradecamp.com | Liquidation data, OI, copybot list (Bootcamp/Quant Elite) |

---

## 💱 Exchange Keys

### Hyperliquid (Perps — Recommended First Exchange)
```env
HYPER_LIQUID_ETH_PRIVATE_KEY=0x...    # Your ETH private key (not MetaMask seed phrase!)
```
- Fund at: https://app.hyperliquid.xyz
- Generate key: MetaMask → Account Details → Export Private Key
- ⚠️  Use a DEDICATED wallet, never your main wallet

### Extended Exchange / X10 (StarkNet Perps)
```env
X10_API_KEY=...
X10_PRIVATE_KEY=0x...
X10_PUBLIC_KEY=0x...
X10_VAULT_ID=...
```
- Docs: https://docs.extended.exchange

### Solana (Spot + On-Chain)
```env
SOLANA_PRIVATE_KEY=...          # Base58 encoded private key
RPC_ENDPOINT=https://...        # Helius, QuickNode, or Alchemy
```
- Get Helius RPC: https://www.helius.dev (free tier available)
- Export Phantom key: Settings → Security & Privacy → Export Private Key

---

## 🐦 Twitter/Social (for Sentiment Agent)
```env
TWITTER_USERNAME=your_username
TWITTER_EMAIL=your_email
TWITTER_PASSWORD=your_password
```
Run `python src/scripts/twitter_login.py` first to generate `cookies.json`.

---

## 📡 Streaming (Optional — for Clips/Stream Agents)
```env
RESTREAM_CLIENT_ID=...
RESTREAM_CLIENT_SECRET=...
```

---

## ✅ Minimal Config to Get Started

For a first run (backtesting + risk + trading on Hyperliquid), you only need:

```env
# src/.env — MINIMAL SETUP

# AI (required)
ANTHROPIC_KEY=sk-ant-...
DEEPSEEK_KEY=sk-...

# Market data (required for analysis agents)
BIRDEYE_API_KEY=...

# Exchange (pick one)
HYPER_LIQUID_ETH_PRIVATE_KEY=0x...

# Moon Dev API (optional but unlocks liquidation + OI data)
MOONDEV_API_KEY=...
```

---

## 🛡️ Security Checklist

- [ ] `src/.env` is in `.gitignore` (check: `git check-ignore src/.env` should return the path)
- [ ] Using dedicated trading wallets — NOT your main crypto wallet
- [ ] Starting with small position sizes (`usd_size = 10` in config.py)
- [ ] `MINIMUM_BALANCE_USD` set to an amount you're comfortable losing
- [ ] Tested with paper trading or testnet before going live

---

## ⚙️ config.py Quick Tuning Guide

Open `src/config.py` and set these before first run:

```python
# Exchange
EXCHANGE = 'hyperliquid'          # 'solana' | 'hyperliquid' | 'extended'

# Position sizing — START SMALL
usd_size = 10                     # Dollar size per position
max_usd_order_size = 5            # Max single order

# Risk limits — NEVER SKIP THESE
MAX_LOSS_USD = 20                 # Stop ALL trading if daily loss hits this
MAX_GAIN_USD = 50                 # Take profit + stop if daily gain hits this
MINIMUM_BALANCE_USD = 50          # Emergency stop if balance drops below this

# AI model (haiku = fast + cheap, good for most agents)
AI_MODEL = "claude-3-haiku-20240307"

# How often the main loop runs
SLEEP_BETWEEN_RUNS_MINUTES = 15
```

---

## 🚀 First Run Order

1. Fill `src/.env`
2. `pip install -r requirements.txt`
3. `python src/agents/risk_agent.py`      ← verify risk agent connects
4. `python src/agents/signal_fusion_agent.py` ← check signal sources
5. `python src/agents/rbi_agent.py`       ← test backtest pipeline
6. `python src/main.py`                   ← full orchestrator

---

*Built with 🌙 by Moon Dev — Never risk more than you can afford to lose.*
