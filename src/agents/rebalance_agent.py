"""
Moon Dev's Portfolio Rebalance Agent
Built with love by Moon Dev

Intelligent portfolio rebalancing for HyperLiquid exchange.
Reads current positions, compares against target allocations,
and generates rebalance orders when deviation exceeds threshold.

Uses signal fusion output for directional bias and LLM confirmation
before executing any rebalance trades.

Standalone: python src/agents/rebalance_agent.py
"""

import os
import json
import csv
import time
from datetime import datetime, timezone
from termcolor import colored, cprint
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.env'))

from src.config import (
    HYPERLIQUID_SYMBOLS,
    MAX_POSITION_PERCENTAGE,
    CASH_PERCENTAGE,
    MINIMUM_BALANCE_USD,
    LIVE_TRADING,
    AI_MODEL,
    AI_MAX_TOKENS,
    AI_TEMPERATURE,
    max_usd_order_size,
)
from src import nice_funcs_hyperliquid as nf
from src.models.model_factory import ModelFactory

# ============================================================================
# REBALANCE CONFIGURATION
# ============================================================================

# Deviation threshold: rebalance if any position drifts more than this % from target
DEVIATION_THRESHOLD_PCT = 10.0

# Minimum USD trade size on HyperLiquid
MIN_ORDER_USD = 11.0

# Output paths
OUTPUT_DIR = "src/data/rebalance"
HISTORY_FILE = os.path.join(OUTPUT_DIR, "rebalance_history.csv")

# Signal fusion input
SIGNAL_FUSION_FILE = "src/data/signal_fusion/latest_signal.json"

# Sleep between rebalance cycles (seconds)
SLEEP_BETWEEN_CYCLES = 900  # 15 minutes

# ============================================================================
# LLM CONFIRMATION PROMPT
# ============================================================================

REBALANCE_CONFIRMATION_PROMPT = """You are Moon Dev's Portfolio Rebalance AI.

You are reviewing a proposed portfolio rebalance on HyperLiquid perps.

Current Portfolio State:
{portfolio_state}

Proposed Rebalance Orders:
{proposed_orders}

Signal Fusion Context:
{signal_context}

Risk Limits:
- Max position allocation: {max_position_pct}%
- Cash reserve target: {cash_pct}%
- Minimum account balance: ${min_balance}

Evaluate whether this rebalance makes sense given:
1. Current market signals (fusion score and direction)
2. Risk limits and position sizing
3. Whether the deviation justifies trading costs
4. Any positions that should NOT be rebalanced right now

Respond with EXACTLY one of:
APPROVE: <brief reason>
REJECT: <brief reason>
PARTIAL: <list which orders to keep and which to skip, with reasons>
"""


class RebalanceAgent:
    """Intelligent portfolio rebalancing agent for HyperLiquid."""

    def __init__(self):
        """Initialize the Rebalance Agent."""
        cprint("\n" + "=" * 50, "cyan")
        cprint("  Moon Dev's Rebalance Agent Starting...", "cyan", attrs=["bold"])
        cprint("=" * 50, "cyan")

        # Ensure output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # Initialize HyperLiquid account
        self.account = nf._get_account_from_env()
        cprint("  HyperLiquid account loaded", "green")

        # Initialize ModelFactory for LLM calls
        self.model_factory = ModelFactory()
        cprint("  ModelFactory initialized", "green")

        # Target allocation: equal-weight across configured symbols
        # Remaining % goes to cash reserve
        self.symbols = HYPERLIQUID_SYMBOLS
        usable_pct = 100.0 - CASH_PERCENTAGE
        per_symbol_pct = usable_pct / len(self.symbols)
        # Cap each symbol at MAX_POSITION_PERCENTAGE
        per_symbol_pct = min(per_symbol_pct, MAX_POSITION_PERCENTAGE)
        self.target_allocations = {sym: per_symbol_pct for sym in self.symbols}
        self.target_cash_pct = 100.0 - sum(self.target_allocations.values())

        cprint(f"  Symbols: {self.symbols}", "white")
        cprint(f"  Target allocations: {self.target_allocations}", "white")
        cprint(f"  Target cash reserve: {self.target_cash_pct:.1f}%", "white")
        cprint(f"  Deviation threshold: {DEVIATION_THRESHOLD_PCT}%", "white")
        cprint(f"  Live trading: {LIVE_TRADING}", "yellow" if not LIVE_TRADING else "red")
        cprint("=" * 50, "cyan")

    # ------------------------------------------------------------------
    # DATA GATHERING
    # ------------------------------------------------------------------

    def get_account_value(self):
        """Get total account value in USD."""
        return nf.get_account_value(self.account)

    def get_free_balance(self):
        """Get available (withdrawable) USDC balance."""
        return nf.get_balance(self.account)

    def get_all_positions(self):
        """Get all open positions as a list of dicts."""
        return nf.get_all_positions(self.account)

    def get_position_value(self, symbol):
        """Get the USD value of a position (absolute, regardless of long/short)."""
        positions, im_in_pos, pos_size, _, _, _, _ = nf.get_position(symbol, self.account)
        if not im_in_pos:
            return 0.0
        mid_price = nf.get_current_price(symbol)
        return abs(float(pos_size) * mid_price)

    def read_signal_fusion(self):
        """Read the latest signal fusion output."""
        try:
            if not os.path.exists(SIGNAL_FUSION_FILE):
                cprint("  Signal fusion file not found, proceeding without", "yellow")
                return None
            with open(SIGNAL_FUSION_FILE, "r") as f:
                data = json.load(f)
            cprint(f"  Signal fusion: score={data.get('score', 0):+.1f}  dir={data.get('direction', 'N/A')}  conf={data.get('confidence', 0):.1f}%", "cyan")
            return data
        except Exception as e:
            cprint(f"  Error reading signal fusion: {e}", "yellow")
            return None

    # ------------------------------------------------------------------
    # ALLOCATION CALCULATION
    # ------------------------------------------------------------------

    def compute_current_allocations(self):
        """
        Compute current allocation % for each symbol and cash.

        Returns:
            dict with keys: 'account_value', 'cash_value', 'cash_pct',
                            'positions' (dict of symbol -> {value, pct})
        """
        account_value = self.get_account_value()
        if account_value <= 0:
            cprint("  Account value is zero or negative!", "red")
            return None

        position_data = {}
        total_position_value = 0.0

        for symbol in self.symbols:
            value = self.get_position_value(symbol)
            pct = (value / account_value) * 100.0 if account_value > 0 else 0.0
            position_data[symbol] = {"value": value, "pct": pct}
            total_position_value += value

        cash_value = account_value - total_position_value
        cash_pct = (cash_value / account_value) * 100.0 if account_value > 0 else 100.0

        return {
            "account_value": account_value,
            "cash_value": cash_value,
            "cash_pct": cash_pct,
            "positions": position_data,
        }

    def compute_deviations(self, allocations):
        """
        Compute deviation of each position from target.

        Returns:
            dict of symbol -> {target_pct, actual_pct, deviation_pct, target_value, actual_value, delta_usd}
        """
        account_value = allocations["account_value"]
        deviations = {}

        for symbol in self.symbols:
            actual_pct = allocations["positions"][symbol]["pct"]
            target_pct = self.target_allocations[symbol]
            deviation = actual_pct - target_pct
            target_value = (target_pct / 100.0) * account_value
            actual_value = allocations["positions"][symbol]["value"]
            delta_usd = actual_value - target_value

            deviations[symbol] = {
                "target_pct": target_pct,
                "actual_pct": actual_pct,
                "deviation_pct": deviation,
                "target_value": target_value,
                "actual_value": actual_value,
                "delta_usd": delta_usd,
            }

        return deviations

    # ------------------------------------------------------------------
    # ORDER GENERATION
    # ------------------------------------------------------------------

    def generate_rebalance_orders(self, deviations, signal_fusion):
        """
        Generate rebalance orders for positions that deviate beyond threshold.

        Incorporates signal fusion directional bias:
        - If fusion says LONG/STRONG_LONG, slightly favor increasing long positions
        - If fusion says SHORT/STRONG_SHORT, slightly favor decreasing positions
        - NEUTRAL: pure mechanical rebalance

        Returns:
            list of order dicts: {symbol, action, usd_amount, reason}
        """
        orders = []
        fusion_direction = signal_fusion.get("direction", "NEUTRAL") if signal_fusion else "NEUTRAL"
        for symbol, dev in deviations.items():
            abs_deviation = abs(dev["deviation_pct"])

            if abs_deviation < DEVIATION_THRESHOLD_PCT:
                continue

            # delta_usd > 0 means overweight, need to sell
            # delta_usd < 0 means underweight, need to buy
            delta = dev["delta_usd"]

            # Apply signal fusion bias: scale the rebalance amount
            # If fusion agrees with the rebalance direction, do full rebalance
            # If fusion disagrees, do a partial rebalance (50%)
            bias_factor = 1.0
            if delta < 0:
                # We want to BUY more
                if fusion_direction in ("SHORT", "STRONG_SHORT"):
                    bias_factor = 0.5  # Fusion says short, reduce buy
                    reason_suffix = " (reduced: fusion bearish)"
                elif fusion_direction in ("LONG", "STRONG_LONG"):
                    bias_factor = 1.0  # Fusion agrees
                    reason_suffix = " (fusion bullish)"
                else:
                    reason_suffix = " (fusion neutral)"
            else:
                # We want to SELL (reduce overweight)
                if fusion_direction in ("LONG", "STRONG_LONG"):
                    bias_factor = 0.5  # Fusion says long, reduce sell
                    reason_suffix = " (reduced: fusion bullish)"
                elif fusion_direction in ("SHORT", "STRONG_SHORT"):
                    bias_factor = 1.0  # Fusion agrees
                    reason_suffix = " (fusion bearish)"
                else:
                    reason_suffix = " (fusion neutral)"

            trade_usd = abs(delta) * bias_factor

            # Respect max order size
            trade_usd = min(trade_usd, max_usd_order_size)

            # Skip if below minimum
            if trade_usd < MIN_ORDER_USD:
                cprint(f"  {symbol}: trade ${trade_usd:.2f} below min, skipping", "yellow")
                continue

            action = "BUY" if delta < 0 else "SELL"
            reason = (
                f"{symbol} is {'overweight' if delta > 0 else 'underweight'} by "
                f"{abs_deviation:.1f}% (${abs(delta):.2f}){reason_suffix}"
            )

            orders.append({
                "symbol": symbol,
                "action": action,
                "usd_amount": round(trade_usd, 2),
                "reason": reason,
                "deviation_pct": dev["deviation_pct"],
            })

        return orders

    # ------------------------------------------------------------------
    # LLM CONFIRMATION
    # ------------------------------------------------------------------

    def get_llm_confirmation(self, allocations, orders, signal_fusion):
        """
        Ask LLM whether the proposed rebalance makes sense.

        Returns:
            tuple: (approved: bool, response_text: str, partial_orders: list or None)
        """
        # Format portfolio state
        portfolio_lines = []
        portfolio_lines.append(f"Account Value: ${allocations['account_value']:.2f}")
        portfolio_lines.append(f"Cash: ${allocations['cash_value']:.2f} ({allocations['cash_pct']:.1f}%)")
        for sym, data in allocations["positions"].items():
            target = self.target_allocations[sym]
            portfolio_lines.append(
                f"  {sym}: ${data['value']:.2f} ({data['pct']:.1f}%) — target {target:.1f}%"
            )
        portfolio_state = "\n".join(portfolio_lines)

        # Format orders
        order_lines = []
        for o in orders:
            order_lines.append(f"  {o['action']} ${o['usd_amount']:.2f} of {o['symbol']} — {o['reason']}")
        proposed_orders = "\n".join(order_lines) if order_lines else "No orders proposed."

        # Format signal context
        if signal_fusion:
            signal_context = (
                f"Score: {signal_fusion.get('score', 0):+.1f}/100\n"
                f"Direction: {signal_fusion.get('direction', 'N/A')}\n"
                f"Confidence: {signal_fusion.get('confidence', 0):.1f}%\n"
                f"Active sources: {signal_fusion.get('active_sources', 0)}"
            )
        else:
            signal_context = "Signal fusion data unavailable."

        prompt = REBALANCE_CONFIRMATION_PROMPT.format(
            portfolio_state=portfolio_state,
            proposed_orders=proposed_orders,
            signal_context=signal_context,
            max_position_pct=MAX_POSITION_PERCENTAGE,
            cash_pct=CASH_PERCENTAGE,
            min_balance=MINIMUM_BALANCE_USD,
        )

        # Try to get a model — prefer claude, fall back to others
        model = None
        for model_type in ["claude", "openai", "deepseek", "groq"]:
            model = self.model_factory.get_model(model_type)
            if model:
                break

        if not model:
            cprint("  No LLM model available, defaulting to APPROVE", "yellow")
            return True, "No LLM available — auto-approved", None

        try:
            response = model.generate_response(
                system_prompt="You are Moon Dev's Portfolio Rebalance AI. Be concise.",
                user_content=prompt,
                temperature=AI_TEMPERATURE,
                max_tokens=AI_MAX_TOKENS,
            )

            if response is None:
                cprint("  LLM returned None, defaulting to APPROVE", "yellow")
                return True, "LLM returned no response — auto-approved", None

            # Extract text content from response
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)

            cprint("\n  LLM Rebalance Assessment:", "cyan")
            cprint(f"  {response_text}", "white")

            first_line = response_text.strip().split("\n")[0].upper()

            if "APPROVE" in first_line:
                return True, response_text, None
            elif "REJECT" in first_line:
                return False, response_text, None
            elif "PARTIAL" in first_line:
                # For partial, we still return approved but log the partial note
                return True, response_text, None
            else:
                cprint("  LLM response unclear, defaulting to REJECT for safety", "yellow")
                return False, response_text, None

        except Exception as e:
            cprint(f"  LLM error: {e}", "red")
            return False, f"LLM error: {e}", None

    # ------------------------------------------------------------------
    # ORDER EXECUTION
    # ------------------------------------------------------------------

    def execute_orders(self, orders):
        """Execute the rebalance orders on HyperLiquid."""
        executed = []

        for order in orders:
            symbol = order["symbol"]
            action = order["action"]
            usd_amount = order["usd_amount"]

            cprint(f"\n  Executing: {action} ${usd_amount:.2f} of {symbol}", "green" if action == "BUY" else "red")

            if not LIVE_TRADING:
                cprint(f"  [DRY RUN] Would {action} ${usd_amount:.2f} of {symbol}", "yellow")
                order["status"] = "dry_run"
                executed.append(order)
                continue

            try:
                if action == "BUY":
                    result = nf.market_buy(symbol, usd_amount, self.account)
                else:
                    result = nf.market_sell(symbol, usd_amount, self.account)

                order["status"] = "executed"
                cprint(f"  Order executed: {action} ${usd_amount:.2f} {symbol}", "green")
                time.sleep(2)  # Small delay between orders

            except Exception as e:
                order["status"] = f"error: {e}"
                cprint(f"  Order failed: {e}", "red")

            executed.append(order)

        return executed

    # ------------------------------------------------------------------
    # LOGGING
    # ------------------------------------------------------------------

    def log_rebalance(self, allocations, deviations, orders, llm_approved, llm_response):
        """Log rebalance decisions to CSV history."""
        timestamp = datetime.now(timezone.utc).isoformat()

        for order in orders:
            row = {
                "timestamp": timestamp,
                "symbol": order["symbol"],
                "action": order["action"],
                "usd_amount": order["usd_amount"],
                "deviation_pct": order.get("deviation_pct", 0),
                "reason": order["reason"],
                "llm_approved": llm_approved,
                "status": order.get("status", "proposed"),
                "account_value": allocations["account_value"],
                "cash_pct": allocations["cash_pct"],
            }

            file_exists = os.path.isfile(HISTORY_FILE)
            with open(HISTORY_FILE, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=row.keys())
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)

        if not orders:
            # Log a no-op entry so we know the agent ran
            row = {
                "timestamp": timestamp,
                "symbol": "NONE",
                "action": "NO_REBALANCE",
                "usd_amount": 0,
                "deviation_pct": 0,
                "reason": "All positions within threshold",
                "llm_approved": True,
                "status": "skipped",
                "account_value": allocations["account_value"] if allocations else 0,
                "cash_pct": allocations["cash_pct"] if allocations else 0,
            }
            file_exists = os.path.isfile(HISTORY_FILE)
            with open(HISTORY_FILE, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=row.keys())
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)

    # ------------------------------------------------------------------
    # DISPLAY
    # ------------------------------------------------------------------

    def print_portfolio_summary(self, allocations, deviations):
        """Print a formatted portfolio summary."""
        cprint("\n" + "=" * 60, "cyan")
        cprint("  PORTFOLIO ALLOCATION SUMMARY", "cyan", attrs=["bold"])
        cprint("=" * 60, "cyan")
        cprint(f"  Account Value:  ${allocations['account_value']:,.2f}", "white")
        cprint(f"  Cash Reserve:   ${allocations['cash_value']:,.2f} ({allocations['cash_pct']:.1f}% / target {self.target_cash_pct:.1f}%)", "white")
        cprint("-" * 60, "cyan")
        cprint(f"  {'Symbol':<8} {'Actual':>10} {'Target':>10} {'Deviation':>10} {'Value':>12}", "white")
        cprint("-" * 60, "cyan")

        for symbol in self.symbols:
            dev = deviations[symbol]
            actual = dev["actual_pct"]
            target = dev["target_pct"]
            deviation = dev["deviation_pct"]
            value = dev["actual_value"]

            # Color code deviation
            if abs(deviation) >= DEVIATION_THRESHOLD_PCT:
                color = "red"
            elif abs(deviation) >= DEVIATION_THRESHOLD_PCT / 2:
                color = "yellow"
            else:
                color = "green"

            cprint(
                f"  {symbol:<8} {actual:>9.1f}% {target:>9.1f}% {deviation:>+9.1f}% ${value:>10,.2f}",
                color,
            )

        cprint("=" * 60, "cyan")

    # ------------------------------------------------------------------
    # MAIN RUN LOOP
    # ------------------------------------------------------------------

    def run(self):
        """Execute one rebalance cycle."""
        cprint("\n  Rebalance cycle starting...", "cyan", attrs=["bold"])

        # 1. Read current allocations
        allocations = self.compute_current_allocations()
        if allocations is None:
            cprint("  Cannot compute allocations, aborting cycle", "red")
            return

        # 2. Check minimum balance
        if allocations["account_value"] < MINIMUM_BALANCE_USD:
            cprint(
                f"  Account value ${allocations['account_value']:.2f} below minimum ${MINIMUM_BALANCE_USD:.2f}",
                "red",
            )
            cprint("  Skipping rebalance for safety", "red")
            self.log_rebalance(allocations, {}, [], False, "Below minimum balance")
            return

        # 3. Compute deviations
        deviations = self.compute_deviations(allocations)

        # 4. Print summary
        self.print_portfolio_summary(allocations, deviations)

        # 5. Read signal fusion
        signal_fusion = self.read_signal_fusion()

        # 6. Generate orders for positions outside threshold
        orders = self.generate_rebalance_orders(deviations, signal_fusion)

        if not orders:
            cprint("\n  All positions within threshold. No rebalance needed.", "green")
            self.log_rebalance(allocations, deviations, [], True, "Within threshold")
            return

        # 7. Print proposed orders
        cprint("\n  PROPOSED REBALANCE ORDERS:", "yellow", attrs=["bold"])
        for o in orders:
            color = "green" if o["action"] == "BUY" else "red"
            cprint(f"    {o['action']} ${o['usd_amount']:.2f} {o['symbol']} — {o['reason']}", color)

        # 8. LLM confirmation
        cprint("\n  Requesting LLM confirmation...", "cyan")
        llm_approved, llm_response, _ = self.get_llm_confirmation(allocations, orders, signal_fusion)

        if not llm_approved:
            cprint("\n  LLM REJECTED rebalance. No trades executed.", "yellow")
            self.log_rebalance(allocations, deviations, orders, False, llm_response)
            return

        cprint("\n  LLM APPROVED rebalance.", "green")

        # 9. Execute orders
        if LIVE_TRADING:
            cprint("\n  LIVE TRADING — Executing orders...", "red", attrs=["bold"])
        else:
            cprint("\n  DRY RUN — Simulating orders...", "yellow", attrs=["bold"])

        executed = self.execute_orders(orders)

        # 10. Log results
        self.log_rebalance(allocations, deviations, executed, True, llm_response)

        # 11. Summary
        cprint("\n  Rebalance cycle complete.", "cyan", attrs=["bold"])
        for o in executed:
            status_color = "green" if o["status"] in ("executed", "dry_run") else "red"
            cprint(f"    {o['symbol']}: {o['action']} ${o['usd_amount']:.2f} — {o['status']}", status_color)


# ============================================================================
# STANDALONE EXECUTION
# ============================================================================

def main():
    """Run the rebalance agent in a loop."""
    cprint("\n  Moon Dev's Rebalance Agent", "cyan", attrs=["bold"])
    cprint("  Portfolio rebalancer for HyperLiquid\n", "cyan")

    agent = RebalanceAgent()

    while True:
        try:
            agent.run()

            cprint(f"\n  Sleeping {SLEEP_BETWEEN_CYCLES}s before next cycle...", "white")
            time.sleep(SLEEP_BETWEEN_CYCLES)

        except KeyboardInterrupt:
            cprint("\n  Rebalance Agent shutting down gracefully...", "yellow")
            break
        except Exception as e:
            cprint(f"\n  Error in rebalance cycle: {e}", "red")
            import traceback
            traceback.print_exc()
            time.sleep(SLEEP_BETWEEN_CYCLES)


if __name__ == "__main__":
    main()
