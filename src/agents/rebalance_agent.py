"""
🌙 Moon Dev's Portfolio Rebalance Agent
Intelligent portfolio rebalancing for HyperLiquid exchange
Built with love by Moon Dev 🚀
"""

import os
import json
import pandas as pd
import time
from datetime import datetime
from termcolor import colored, cprint
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))

# Import config
from src import config
from src.config import (
    EXCHANGE,
    LIVE_TRADING,
    HYPERLIQUID_SYMBOLS,
    MAX_POSITION_PERCENTAGE,
    CASH_PERCENTAGE,
    MINIMUM_BALANCE_USD,
    AI_MODEL,
    AI_TEMPERATURE,
    AI_MAX_TOKENS
)

# Import HyperLiquid functions
from src import nice_funcs_hyperliquid as n

# Import ModelFactory for AI confirmation
from src.models.model_factory import ModelFactory

# Rebalance threshold (%)
REBALANCE_THRESHOLD = 10.0  # If position deviates more than 10% from target, rebalance

# AI Confirmation Prompt
REBALANCE_CONFIRMATION_PROMPT = """
🌙 Moon Dev's Portfolio Rebalance Decision 🚀

You are Moon Dev's Portfolio Rebalancing AI. Analyze the proposed rebalance and decide if it makes sense.

Current Portfolio State:
{portfolio_state}

Signal Fusion Data:
{signal_fusion}

Proposed Rebalance Actions:
{rebalance_actions}

Consider:
1. Does the rebalance align with current market signals?
2. Are the position adjustments reasonable given the directional bias?
3. Is the risk/reward favorable?
4. Should we proceed with this rebalance?

Respond with either:
APPROVE: <brief reasoning>
or
REJECT: <brief reasoning>
"""


class RebalanceAgent:
    def __init__(self):
        """Initialize Moon Dev's Rebalance Agent 🛡️"""
        cprint("🔄 Initializing Rebalance Agent...", "cyan", attrs=['bold'])
        
        # Verify we're on HyperLiquid
        if EXCHANGE != 'hyperliquid':
            raise ValueError("⚠️ Rebalance Agent only works with HyperLiquid exchange!")
        
        # Get HyperLiquid account
        self.account = n._get_account_from_env()
        cprint(f"✅ Connected to HyperLiquid: {self.account.address}", "green")
        
        # Initialize ModelFactory for AI confirmation
        self.model_factory = ModelFactory()
        
        # Parse AI_MODEL to get model type and name
        self.ai_model_type, self.ai_model_name = self._parse_ai_model(AI_MODEL)
        
        # Create rebalance history directory
        self.history_dir = Path('src/data/rebalance')
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.history_dir / 'rebalance_history.csv'
        
        # Initialize history file if it doesn't exist
        if not self.history_file.exists():
            df = pd.DataFrame(columns=[
                'timestamp', 'symbol', 'action', 'current_allocation_pct', 
                'target_allocation_pct', 'deviation_pct', 'usd_amount', 
                'ai_decision', 'live_trading', 'status'
            ])
            df.to_csv(self.history_file, index=False)
            cprint(f"📝 Created rebalance history file: {self.history_file}", "green")
        
        cprint("✨ Rebalance Agent initialized!", "green", attrs=['bold'])
    
    def _parse_ai_model(self, model_string):
        """Parse AI_MODEL string to extract model type and name"""
        # Common model mappings
        model_map = {
            'claude-haiku-4-5-20251001': ('claude', 'claude-3-5-haiku-latest'),
            'claude-sonnet-4-6': ('claude', 'claude-3-5-sonnet-latest'),
            'claude-opus-4-6': ('claude', 'claude-opus-4-latest'),
            'moondev': ('moondev', 'gpt-4o-mini'),
            'deepseek': ('deepseek', 'deepseek-reasoner'),
            'groq': ('groq', 'mixtral-8x7b-32768'),
            'openrouter': ('openrouter', 'google/gemini-2.5-flash'),
        }
        
        # Check if it's a known model
        if model_string in model_map:
            return model_map[model_string]
        
        # Default to claude
        return ('claude', 'claude-3-5-haiku-latest')
    
    def get_current_positions(self):
        """Get current positions and their USD values"""
        cprint("\n📊 Fetching current positions...", "cyan")
        
        positions = {}
        all_positions = n.get_all_positions(self.account)
        
        for pos in all_positions:
            symbol = pos['symbol']
            size = pos['size']
            entry_price = pos['entry_price']
            
            # Get current price
            ask, bid, _ = n.ask_bid(symbol)
            current_price = (ask + bid) / 2
            
            # Calculate USD value
            usd_value = abs(size) * current_price
            
            positions[symbol] = {
                'size': size,
                'entry_price': entry_price,
                'current_price': current_price,
                'usd_value': usd_value,
                'is_long': size > 0
            }
            
            cprint(f"  • {symbol}: ${usd_value:,.2f} ({size:+.4f} @ ${current_price:,.2f})", "white")
        
        return positions
    
    def get_account_balance(self):
        """Get total account value and available balance"""
        account_value = n.get_account_value(self.account)
        available_balance = n.get_balance(self.account)
        
        cprint(f"\n💰 Account Value: ${account_value:,.2f}", "green")
        cprint(f"💵 Available Balance: ${available_balance:,.2f}", "green")
        
        return account_value, available_balance
    
    def read_signal_fusion(self):
        """Read latest signal fusion output"""
        signal_file = Path('src/data/signal_fusion/latest_signal.json')
        
        if not signal_file.exists():
            cprint("⚠️ Signal fusion file not found, using neutral bias", "yellow")
            return {
                'score': 0,
                'direction': 'NEUTRAL',
                'confidence': 0,
                'active_sources': 0
            }
        
        try:
            with open(signal_file, 'r') as f:
                signal_data = json.load(f)
            
            cprint(f"\n🔀 Signal Fusion: {signal_data['direction']} (score: {signal_data['score']:+.2f}, confidence: {signal_data['confidence']:.1f}%)", "cyan")
            return signal_data
        except Exception as e:
            cprint(f"⚠️ Error reading signal fusion: {e}", "yellow")
            return {
                'score': 0,
                'direction': 'NEUTRAL',
                'confidence': 0,
                'active_sources': 0
            }
    
    def calculate_target_allocations(self, account_value, signal_fusion):
        """Calculate target allocation percentages for each symbol"""
        cprint("\n🎯 Calculating target allocations...", "cyan")
        
        # Reserve cash percentage
        investable_value = account_value * (1 - CASH_PERCENTAGE / 100)
        
        # Get directional bias from signal fusion
        direction = signal_fusion.get('direction', 'NEUTRAL')
        confidence = signal_fusion.get('confidence', 0)
        
        # Base allocation: equal weight across symbols
        num_symbols = len(HYPERLIQUID_SYMBOLS)
        base_allocation_pct = (100 - CASH_PERCENTAGE) / num_symbols
        
        # Adjust based on signal fusion (simple strategy for now)
        # If bullish, slightly overweight BTC/ETH
        # If bearish, reduce allocations
        allocations = {}
        
        for symbol in HYPERLIQUID_SYMBOLS:
            target_pct = base_allocation_pct
            
            # Apply directional bias
            if direction == 'BULLISH' and confidence > 50:
                # Overweight major assets in bull market
                if symbol in ['BTC', 'ETH']:
                    target_pct *= 1.2  # 20% overweight
                else:
                    target_pct *= 0.8  # 20% underweight
            elif direction == 'BEARISH' and confidence > 50:
                # Reduce all allocations in bear market
                target_pct *= 0.5
            
            # Cap at MAX_POSITION_PERCENTAGE
            target_pct = min(target_pct, MAX_POSITION_PERCENTAGE)
            
            allocations[symbol] = {
                'target_pct': target_pct,
                'target_usd': account_value * (target_pct / 100)
            }
            
            cprint(f"  • {symbol}: {target_pct:.1f}% (${allocations[symbol]['target_usd']:,.2f})", "white")
        
        return allocations
    
    def calculate_deviations(self, positions, target_allocations, account_value):
        """Calculate deviations between current and target allocations"""
        cprint("\n📐 Calculating allocation deviations...", "cyan")
        
        deviations = {}
        
        for symbol in HYPERLIQUID_SYMBOLS:
            # Current allocation
            current_usd = positions.get(symbol, {}).get('usd_value', 0)
            current_pct = (current_usd / account_value * 100) if account_value > 0 else 0
            
            # Target allocation
            target_pct = target_allocations[symbol]['target_pct']
            target_usd = target_allocations[symbol]['target_usd']
            
            # Deviation
            deviation_pct = abs(current_pct - target_pct)
            deviation_usd = current_usd - target_usd
            
            deviations[symbol] = {
                'current_pct': current_pct,
                'current_usd': current_usd,
                'target_pct': target_pct,
                'target_usd': target_usd,
                'deviation_pct': deviation_pct,
                'deviation_usd': deviation_usd,
                'needs_rebalance': deviation_pct > REBALANCE_THRESHOLD
            }
            
            status = "🔴 REBALANCE" if deviation_pct > REBALANCE_THRESHOLD else "✅ OK"
            cprint(f"  • {symbol}: {current_pct:.1f}% → {target_pct:.1f}% (Δ {deviation_pct:.1f}%) {status}", 
                   "yellow" if deviation_pct > REBALANCE_THRESHOLD else "green")
        
        return deviations
    
    def generate_rebalance_orders(self, deviations):
        """Generate rebalance orders for positions that need adjustment"""
        cprint("\n📋 Generating rebalance orders...", "cyan")
        
        orders = []
        
        for symbol, dev in deviations.items():
            if not dev['needs_rebalance']:
                continue
            
            # Determine action
            if dev['deviation_usd'] > 0:
                # Current > Target: SELL
                action = 'SELL'
                usd_amount = abs(dev['deviation_usd'])
            else:
                # Current < Target: BUY
                action = 'BUY'
                usd_amount = abs(dev['deviation_usd'])
            
            orders.append({
                'symbol': symbol,
                'action': action,
                'usd_amount': usd_amount,
                'current_pct': dev['current_pct'],
                'target_pct': dev['target_pct'],
                'deviation_pct': dev['deviation_pct']
            })
            
            cprint(f"  • {action} {symbol}: ${usd_amount:,.2f}", "yellow")
        
        return orders
    
    def get_ai_confirmation(self, portfolio_state, signal_fusion, rebalance_orders):
        """Get AI confirmation before executing rebalance"""
        cprint("\n🤖 Requesting AI confirmation...", "cyan")
        
        try:
            # Format data for prompt
            portfolio_str = json.dumps(portfolio_state, indent=2)
            signal_str = json.dumps(signal_fusion, indent=2)
            orders_str = json.dumps(rebalance_orders, indent=2)
            
            prompt = REBALANCE_CONFIRMATION_PROMPT.format(
                portfolio_state=portfolio_str,
                signal_fusion=signal_str,
                rebalance_actions=orders_str
            )
            
            # Get model
            model = self.model_factory.get_model(self.ai_model_type, self.ai_model_name)
            
            if not model:
                cprint(f"⚠️ Could not get AI model {self.ai_model_type}, proceeding without confirmation", "yellow")
                return True, "AI model unavailable"
            
            # Generate response
            response = model.generate(
                system_prompt="You are Moon Dev's Portfolio Rebalancing AI. Analyze rebalance proposals and approve or reject them.",
                user_content=prompt,
                temperature=AI_TEMPERATURE,
                max_tokens=AI_MAX_TOKENS
            )
            
            # Parse response
            response_text = response.strip()
            cprint(f"\n🧠 AI Response:\n{response_text}", "cyan")
            
            # Check for approval
            approved = "APPROVE" in response_text.upper()
            
            if approved:
                cprint("✅ AI APPROVED rebalance", "green", attrs=['bold'])
            else:
                cprint("❌ AI REJECTED rebalance", "red", attrs=['bold'])
            
            return approved, response_text
            
        except Exception as e:
            cprint(f"⚠️ Error getting AI confirmation: {e}", "yellow")
            return False, f"Error: {str(e)}"
    
    def execute_rebalance_orders(self, orders):
        """Execute rebalance orders"""
        cprint("\n🚀 Executing rebalance orders...", "cyan", attrs=['bold'])
        
        results = []
        
        for order in orders:
            symbol = order['symbol']
            action = order['action']
            usd_amount = order['usd_amount']
            
            try:
                if action == 'BUY':
                    cprint(f"\n🛒 Buying {symbol} for ${usd_amount:,.2f}...", "green")
                    result = n.market_buy(symbol, usd_amount, self.account)
                    status = 'SUCCESS'
                    cprint(f"✅ Buy order executed for {symbol}", "green")
                    
                elif action == 'SELL':
                    cprint(f"\n💸 Selling {symbol} for ${usd_amount:,.2f}...", "red")
                    result = n.market_sell(symbol, usd_amount, self.account)
                    status = 'SUCCESS'
                    cprint(f"✅ Sell order executed for {symbol}", "red")
                
                results.append({
                    'symbol': symbol,
                    'action': action,
                    'usd_amount': usd_amount,
                    'status': status,
                    'result': result
                })
                
                # Small delay between orders
                time.sleep(2)
                
            except Exception as e:
                cprint(f"❌ Error executing {action} for {symbol}: {e}", "red")
                results.append({
                    'symbol': symbol,
                    'action': action,
                    'usd_amount': usd_amount,
                    'status': 'FAILED',
                    'error': str(e)
                })
        
        return results
    
    def log_rebalance(self, orders, ai_decision, ai_reasoning, executed=False):
        """Log rebalance decisions to CSV"""
        try:
            # Read existing history
            df = pd.read_csv(self.history_file)
            
            # Create new rows
            new_rows = []
            for order in orders:
                new_rows.append({
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'symbol': order['symbol'],
                    'action': order['action'],
                    'current_allocation_pct': order['current_pct'],
                    'target_allocation_pct': order['target_pct'],
                    'deviation_pct': order['deviation_pct'],
                    'usd_amount': order['usd_amount'],
                    'ai_decision': 'APPROVED' if ai_decision else 'REJECTED',
                    'live_trading': LIVE_TRADING,
                    'status': 'EXECUTED' if executed else 'SIMULATED'
                })
            
            # Append new rows
            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
            
            # Save
            df.to_csv(self.history_file, index=False)
            cprint(f"\n📝 Logged {len(new_rows)} rebalance actions to {self.history_file}", "green")
            
        except Exception as e:
            cprint(f"⚠️ Error logging rebalance: {e}", "yellow")
    
    def run(self):
        """Run the rebalance agent"""
        try:
            cprint("\n" + "="*60, "cyan")
            cprint("🔄 MOON DEV'S REBALANCE AGENT STARTING 🔄", "cyan", attrs=['bold'])
            cprint("="*60 + "\n", "cyan")
            
            # Check minimum balance
            account_value, available_balance = self.get_account_balance()
            
            if account_value < MINIMUM_BALANCE_USD:
                cprint(f"⚠️ Account value ${account_value:,.2f} below minimum ${MINIMUM_BALANCE_USD:,.2f}", "red")
                cprint("❌ Skipping rebalance due to low balance", "red")
                return
            
            # Get current positions
            positions = self.get_current_positions()
            
            # Read signal fusion
            signal_fusion = self.read_signal_fusion()
            
            # Calculate target allocations
            target_allocations = self.calculate_target_allocations(account_value, signal_fusion)
            
            # Calculate deviations
            deviations = self.calculate_deviations(positions, target_allocations, account_value)
            
            # Generate rebalance orders
            orders = self.generate_rebalance_orders(deviations)
            
            if not orders:
                cprint("\n✅ Portfolio is balanced! No rebalance needed.", "green", attrs=['bold'])
                return
            
            cprint(f"\n📊 Found {len(orders)} positions that need rebalancing", "yellow")
            
            # Get AI confirmation
            portfolio_state = {
                'account_value': account_value,
                'available_balance': available_balance,
                'positions': positions,
                'deviations': deviations
            }
            
            ai_approved, ai_reasoning = self.get_ai_confirmation(portfolio_state, signal_fusion, orders)
            
            # Execute if approved and live trading is enabled
            if ai_approved:
                if LIVE_TRADING:
                    cprint("\n🚀 LIVE TRADING ENABLED - Executing rebalance orders...", "green", attrs=['bold'])
                    results = self.execute_rebalance_orders(orders)
                    self.log_rebalance(orders, ai_approved, ai_reasoning, executed=True)
                    
                    # Print summary
                    cprint("\n" + "="*60, "cyan")
                    cprint("📊 REBALANCE SUMMARY", "cyan", attrs=['bold'])
                    cprint("="*60, "cyan")
                    for result in results:
                        status_color = "green" if result['status'] == 'SUCCESS' else "red"
                        cprint(f"  • {result['symbol']} {result['action']}: {result['status']}", status_color)
                    cprint("="*60 + "\n", "cyan")
                else:
                    cprint("\n⚠️ LIVE TRADING DISABLED - Simulation mode", "yellow", attrs=['bold'])
                    cprint("📋 Would execute the following orders:", "yellow")
                    for order in orders:
                        cprint(f"  • {order['action']} {order['symbol']}: ${order['usd_amount']:,.2f}", "yellow")
                    self.log_rebalance(orders, ai_approved, ai_reasoning, executed=False)
            else:
                cprint("\n❌ Rebalance rejected by AI - no action taken", "red", attrs=['bold'])
                self.log_rebalance(orders, ai_approved, ai_reasoning, executed=False)
            
            cprint("\n✨ Rebalance agent completed!", "green", attrs=['bold'])
            
        except Exception as e:
            cprint(f"\n❌ Error in rebalance agent: {e}", "red")
            import traceback
            traceback.print_exc()


def main():
    """Main function to run the rebalance agent"""
    try:
        agent = RebalanceAgent()
        agent.run()
    except KeyboardInterrupt:
        cprint("\n👋 Rebalance agent interrupted by user", "yellow")
    except Exception as e:
        cprint(f"\n❌ Fatal error: {e}", "red")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
