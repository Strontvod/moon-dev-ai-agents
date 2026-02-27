# 🔄 Rebalance Agent Documentation

## Overview
Moon Dev's Portfolio Rebalance Agent intelligently rebalances your HyperLiquid portfolio based on target allocations, market signals, and risk limits.

## Features

### 1. **Intelligent Position Monitoring**
- Reads current positions via `nice_funcs_hyperliquid.py`
- Calculates real-time USD values for all positions
- Tracks allocation percentages across BTC, ETH, SOL

### 2. **Signal-Driven Allocation**
- Reads signal fusion output from `src/data/signal_fusion/latest_signal.json`
- Adjusts target allocations based on market direction:
  - **BULLISH**: Overweight BTC/ETH (20% increase)
  - **BEARISH**: Reduce all allocations (50% reduction)
  - **NEUTRAL**: Equal weight distribution

### 3. **Risk Management**
- Respects `MAX_POSITION_PERCENTAGE` from config.py
- Maintains `CASH_PERCENTAGE` reserve
- Checks `MINIMUM_BALANCE_USD` before rebalancing
- 10% deviation threshold before triggering rebalance

### 4. **AI Confirmation**
- Uses ModelFactory for LLM confirmation
- Analyzes portfolio state, signals, and proposed actions
- Requires AI approval before executing trades
- Supports all configured AI models (Claude, GPT, DeepSeek, etc.)

### 5. **Comprehensive Logging**
- Logs all decisions to `src/data/rebalance/rebalance_history.csv`
- Tracks: timestamp, symbol, action, allocations, deviations, AI decision, status
- Distinguishes between simulated and executed trades

### 6. **Live Trading Gate**
- Respects `LIVE_TRADING` flag from config.py
- **False**: Simulation mode - prints what it WOULD do
- **True**: Executes real market orders

## Usage

### Standalone Execution
```bash
python src/agents/rebalance_agent.py
```

### Integration with Other Agents
```python
from src.agents.rebalance_agent import RebalanceAgent

agent = RebalanceAgent()
agent.run()
```

## Configuration

### Required Config Variables (config.py)
```python
EXCHANGE = 'hyperliquid'              # Must be hyperliquid
LIVE_TRADING = False                  # Set True to execute real trades
HYPERLIQUID_SYMBOLS = ['BTC', 'ETH', 'SOL']  # Symbols to rebalance
MAX_POSITION_PERCENTAGE = 30          # Max allocation per position
CASH_PERCENTAGE = 20                  # Minimum cash reserve
MINIMUM_BALANCE_USD = 30              # Minimum account balance
AI_MODEL = 'claude-haiku-4-5-20251001'  # AI model for confirmation
```

### Environment Variables (.env)
```bash
HYPER_LIQUID_ETH_PRIVATE_KEY=your_private_key_here
ANTHROPIC_KEY=your_anthropic_key_here  # Or other AI provider keys
```

## How It Works

### 1. **Portfolio Analysis**
```
Current Portfolio:
  • BTC: $500 (50%)
  • ETH: $300 (30%)
  • SOL: $100 (10%)
  • Cash: $100 (10%)
Total: $1,000
```

### 2. **Target Calculation**
Based on signal fusion (e.g., BULLISH with 60% confidence):
```
Target Allocations:
  • BTC: 32% ($320) - overweight major asset
  • ETH: 32% ($320) - overweight major asset
  • SOL: 16% ($160) - underweight alt
  • Cash: 20% ($200) - maintain reserve
```

### 3. **Deviation Analysis**
```
Deviations:
  • BTC: 50% → 32% (Δ 18%) 🔴 REBALANCE
  • ETH: 30% → 32% (Δ 2%) ✅ OK
  • SOL: 10% → 16% (Δ 6%) ✅ OK
```

### 4. **Order Generation**
```
Rebalance Orders:
  • SELL BTC: $180 (reduce from 50% to 32%)
```

### 5. **AI Confirmation**
```
🤖 AI Analysis:
Portfolio State: {...}
Signal Fusion: BULLISH (60% confidence)
Proposed Actions: SELL BTC $180

AI Decision: APPROVE
Reasoning: "Rebalancing from overweight BTC position makes sense 
given the portfolio is too concentrated. The 32% target aligns 
with risk limits and maintains diversification."
```

### 6. **Execution**
- **LIVE_TRADING = False**: Prints simulation
- **LIVE_TRADING = True**: Executes market orders via `market_buy`/`market_sell`

## Output Example

### Simulation Mode (LIVE_TRADING = False)
```
============================================================
🔄 MOON DEV'S REBALANCE AGENT STARTING 🔄
============================================================

💰 Account Value: $1,000.00
💵 Available Balance: $100.00

📊 Fetching current positions...
  • BTC: $500.00 (+0.0050 @ $100,000.00)
  • ETH: $300.00 (+0.1000 @ $3,000.00)
  • SOL: $100.00 (+0.5000 @ $200.00)

🔀 Signal Fusion: BULLISH (score: +15.50, confidence: 60.0%)

🎯 Calculating target allocations...
  • BTC: 32.0% ($320.00)
  • ETH: 32.0% ($320.00)
  • SOL: 16.0% ($160.00)

📐 Calculating allocation deviations...
  • BTC: 50.0% → 32.0% (Δ 18.0%) 🔴 REBALANCE
  • ETH: 30.0% → 32.0% (Δ 2.0%) ✅ OK
  • SOL: 10.0% → 16.0% (Δ 6.0%) ✅ OK

📋 Generating rebalance orders...
  • SELL BTC: $180.00

🤖 Requesting AI confirmation...

🧠 AI Response:
APPROVE: Rebalancing from overweight BTC position makes sense...

✅ AI APPROVED rebalance

⚠️ LIVE TRADING DISABLED - Simulation mode
📋 Would execute the following orders:
  • SELL BTC: $180.00

📝 Logged 1 rebalance actions to src/data/rebalance/rebalance_history.csv

✨ Rebalance agent completed!
```

## Rebalance History CSV

### Columns
- `timestamp`: When the rebalance was analyzed
- `symbol`: Asset symbol (BTC, ETH, SOL)
- `action`: BUY or SELL
- `current_allocation_pct`: Current allocation percentage
- `target_allocation_pct`: Target allocation percentage
- `deviation_pct`: Absolute deviation percentage
- `usd_amount`: USD amount to trade
- `ai_decision`: APPROVED or REJECTED
- `live_trading`: True/False flag
- `status`: EXECUTED or SIMULATED

### Example
```csv
timestamp,symbol,action,current_allocation_pct,target_allocation_pct,deviation_pct,usd_amount,ai_decision,live_trading,status
2026-02-27 10:30:00,BTC,SELL,50.0,32.0,18.0,180.0,APPROVED,False,SIMULATED
2026-02-27 11:45:00,SOL,BUY,10.0,16.0,6.0,60.0,APPROVED,True,EXECUTED
```

## Safety Features

### 1. **Exchange Validation**
- Only works with HyperLiquid exchange
- Raises error if EXCHANGE != 'hyperliquid'

### 2. **Balance Checks**
- Verifies account value > MINIMUM_BALANCE_USD
- Skips rebalance if balance too low

### 3. **Deviation Threshold**
- Only rebalances if deviation > 10%
- Prevents excessive trading on small fluctuations

### 4. **AI Confirmation**
- Requires AI approval before execution
- AI analyzes market conditions and risk/reward

### 5. **Live Trading Gate**
- Simulation mode by default
- Requires explicit LIVE_TRADING = True

### 6. **Comprehensive Logging**
- All decisions logged to CSV
- Tracks both simulated and executed trades

## Integration with Existing Agents

### Risk Agent
The rebalance agent complements the risk agent:
- **Risk Agent**: Monitors PnL limits, closes positions on breach
- **Rebalance Agent**: Maintains optimal allocations, adjusts positions

### Strategy Agent
Works with strategy signals:
- **Strategy Agent**: Generates entry/exit signals
- **Rebalance Agent**: Ensures portfolio stays balanced

### Signal Fusion
Uses signal fusion for directional bias:
- **Signal Fusion**: Aggregates funding, OI, sentiment, liquidations
- **Rebalance Agent**: Adjusts allocations based on market direction

## Best Practices

### 1. **Run Periodically**
```bash
# Run every 6 hours via cron
0 */6 * * * cd /path/to/project && python src/agents/rebalance_agent.py
```

### 2. **Monitor Logs**
```bash
# Check rebalance history
tail -f src/data/rebalance/rebalance_history.csv
```

### 3. **Test in Simulation First**
```python
# config.py
LIVE_TRADING = False  # Test thoroughly before enabling
```

### 4. **Adjust Thresholds**
```python
# In rebalance_agent.py
REBALANCE_THRESHOLD = 10.0  # Increase to reduce trading frequency
```

### 5. **Review AI Decisions**
- Check AI reasoning in logs
- Adjust AI_MODEL if needed for better decisions

## Troubleshooting

### "HYPER_LIQUID_ETH_PRIVATE_KEY not found"
- Add private key to .env file
- Ensure .env is in project root

### "No AI models available"
- Check API keys in .env (ANTHROPIC_KEY, OPENAI_KEY, etc.)
- Verify ModelFactory initialization

### "Account value below minimum"
- Increase account balance
- Lower MINIMUM_BALANCE_USD in config.py

### "No positions to rebalance"
- All positions within 10% of target
- This is normal - no action needed

## Code Structure

### Main Components
1. **`__init__`**: Initialize agent, connect to HyperLiquid, setup ModelFactory
2. **`get_current_positions`**: Fetch current positions and USD values
3. **`get_account_balance`**: Get total account value and available balance
4. **`read_signal_fusion`**: Read latest signal fusion output
5. **`calculate_target_allocations`**: Calculate target allocation percentages
6. **`calculate_deviations`**: Compare current vs target allocations
7. **`generate_rebalance_orders`**: Create buy/sell orders for rebalancing
8. **`get_ai_confirmation`**: Get AI approval for rebalance
9. **`execute_rebalance_orders`**: Execute market orders (if LIVE_TRADING)
10. **`log_rebalance`**: Log all decisions to CSV
11. **`run`**: Main execution flow

### File Size
- **530 lines** (well under 800 line requirement)
- Clean, readable code with comprehensive error handling
- Follows existing agent patterns (risk_agent, strategy_agent)

## Future Enhancements

### Potential Improvements
1. **Dynamic Thresholds**: Adjust rebalance threshold based on volatility
2. **Gas Optimization**: Batch orders to reduce fees
3. **Advanced Allocation**: ML-based allocation strategies
4. **Multi-Exchange**: Support for other exchanges
5. **Backtesting**: Historical rebalance simulation
6. **Alerts**: Telegram/Discord notifications on rebalance

## License
Built with love by Moon Dev 🌙🚀
