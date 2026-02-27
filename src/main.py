"""
🌙 Moon Dev's AI Trading System
Main entry point for running trading agents

LIVE_TRADING flag (set in src/config.py):
  False (default) — Analysis-only mode: strategy analysis runs, NO background
                    data collectors, NO real orders. Safe for development.
  True            — Live mode: background collectors run every cycle, real
                    orders can be placed by trading/risk agents.
"""

import os
import sys
from termcolor import cprint
from dotenv import load_dotenv
import time
from datetime import datetime, timedelta

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Load environment variables first
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# Import config (provides LIVE_TRADING, SLEEP_BETWEEN_RUNS_MINUTES, etc.)
from config import *

# Import core agents
from src.agents.trading_agent import TradingAgent
from src.agents.risk_agent import RiskAgent
from src.agents.strategy_agent import StrategyAgent
from src.agents.copybot_agent import CopyBotAgent

# Lazy import sentiment agent (requires torch/transformers — optional)
try:
    from src.agents.sentiment_agent import SentimentAgent
    SENTIMENT_AVAILABLE = True
except ImportError as e:
    cprint(f"⚠️  Sentiment agent unavailable (pip install torch to enable): {e}", "yellow")
    SENTIMENT_AVAILABLE = False
    SentimentAgent = None

# Background data collectors — only imported/used when LIVE_TRADING = True
# Free HL APIs as primary source; MoonDev API as fallback/enhancement when key is set
if LIVE_TRADING:
    from src.agents.smart_money_collector import collect as collect_smart_money, save_to_csv as save_smart_money
    from src.agents.orderflow_collector import collect as collect_orderflow, save_to_csv as save_orderflow
    from src.agents.hlp_collector import collect as collect_hlp, save_to_csv as save_hlp
    from src.agents.oi_collector import collect as collect_oi, save_to_csv as save_oi
    from src.agents.liquidation_collector import collect as collect_liquidations, save_to_csv as save_liquidations
    # New collectors (Phase 2–4): MoonDev API primary, free HL fallback
    from src.agents.position_snapshot_collector import collect as collect_snapshots, save_to_csv as save_snapshots
    from src.agents.multi_liq_collector import collect as collect_multi_liq, save_to_csv as save_multi_liq
    from src.agents.buyer_tracker_collector import collect as collect_buyers, save_to_csv as save_buyers

# ── Agent Configuration ────────────────────────────────────────────────────────
ACTIVE_AGENTS = {
    'risk':      True,   # Always runs first — no LLM, pure balance check
    'trading':   False,  # OFF — no raw Claude OHLCV calls every cycle
    'strategy':  True,   # ON  — only calls LLM when divergence fires
    'copybot':   False,  # CopyBot agent
    'sentiment': False,  # Run sentiment_agent.py directly instead
    # whale_agent is run standalone from whale_agent.py
}


def _print_startup_banner():
    """Print startup banner showing mode and active agents."""
    mode_colour = "green" if LIVE_TRADING else "yellow"
    mode_label  = "🟢 LIVE TRADING" if LIVE_TRADING else "🟡 ANALYSIS-ONLY (no orders, no background collectors)"

    cprint("\n" + "═" * 60, "cyan")
    cprint("  🌙 Moon Dev AI Agent Trading System", "white", attrs=["bold"])
    cprint("═" * 60, "cyan")
    cprint(f"  Mode   : {mode_label}", mode_colour, attrs=["bold"])
    cprint(f"  Exchange: {EXCHANGE.upper()}", "white")
    cprint("─" * 60, "cyan")
    cprint("  Active Agents:", "white")
    for agent, active in ACTIVE_AGENTS.items():
        status = "✅ ON " if active else "❌ OFF"
        cprint(f"    • {agent.title():<12} {status}", "white")
    if LIVE_TRADING:
        cprint("─" * 60, "cyan")
        cprint("  Background Collectors (live mode):", "white")
        for name in ["OI", "Liquidation", "Smart Money", "Order Flow", "HLP",
                     "Pos. Snapshots", "Multi-Liq", "Buyer Tracker"]:
            cprint(f"    • {name:<16} ✅ ON", "green")
    cprint("═" * 60, "cyan")
    print()


def _refresh_signal_data():
    """Refresh all signal fusion data sources. Only called in LIVE_TRADING mode."""
    cprint("\n📡 Refreshing signal fusion data (10 sources)...", "cyan")
    collectors = [
        # ── Free HL sources (always available) ──────────────────────────────
        ("OI",               collect_oi,           save_oi),
        ("Liquidation",      collect_liquidations, save_liquidations),
        ("Smart Money",      collect_smart_money,  save_smart_money),
        ("Order Flow",       collect_orderflow,    save_orderflow),
        ("HLP",              collect_hlp,          save_hlp),
        # ── Enhanced sources (MoonDev API primary, HL fallback) ──────────────
        ("Pos. Snapshots",   collect_snapshots,    save_snapshots),
        ("Multi-Liq",        collect_multi_liq,    save_multi_liq),
        ("Buyer Tracker",    collect_buyers,        save_buyers),
    ]
    for name, collector, saver in collectors:
        try:
            data = collector()
            if data:
                saver(data)
                cprint(f"  ✅ {name}: {len(data)} records", "green")
            else:
                cprint(f"  ⚠️  {name}: no data", "yellow")
        except Exception as e:
            cprint(f"  ❌ {name}: {e}", "red")


def run_agents():
    """Run all active agents in sequence."""
    try:
        # Initialize active agents
        trading_agent  = TradingAgent()  if ACTIVE_AGENTS['trading']   else None
        risk_agent     = RiskAgent()     if ACTIVE_AGENTS['risk']       else None
        strategy_agent = StrategyAgent() if ACTIVE_AGENTS['strategy']   else None
        copybot_agent  = CopyBotAgent()  if ACTIVE_AGENTS['copybot']    else None
        sentiment_agent = (
            SentimentAgent() if ACTIVE_AGENTS['sentiment'] and SENTIMENT_AVAILABLE else None
        )

        while True:
            try:
                cycle_start = datetime.now()
                cprint(f"\n⏰ Cycle start: {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}", "cyan")

                # ── Background data collection (LIVE mode only) ────────────────
                if LIVE_TRADING:
                    _refresh_signal_data()
                else:
                    cprint("\n⏭️  Skipping background collectors (ANALYSIS-ONLY mode)", "yellow")

                # ── Risk Management (LIVE mode only — no point checking limits if not trading) ──
                if risk_agent and LIVE_TRADING:
                    cprint("\n🛡️  Running Risk Management...", "cyan")
                    risk_agent.run()

                # ── Trading Analysis (LIVE mode only) ─────────────────────────
                if trading_agent and LIVE_TRADING:
                    cprint("\n🤖 Running Trading Analysis...", "cyan")
                    trading_agent.run()

                # ── Strategy Analysis (always runs — no orders, just signals) ──
                if strategy_agent:
                    cprint("\n📊 Running Strategy Analysis...", "cyan")
                    for token in get_active_tokens():
                        if token not in EXCLUDED_TOKENS:
                            cprint(f"\n🔍 Analyzing {token}...", "cyan")
                            strategy_agent.get_signals(token)

                # ── CopyBot Analysis (LIVE mode only) ─────────────────────────
                if copybot_agent and LIVE_TRADING:
                    cprint("\n🤖 Running CopyBot Portfolio Analysis...", "cyan")
                    copybot_agent.run_analysis_cycle()

                # ── Sentiment Analysis (always runs if enabled) ────────────────
                if sentiment_agent:
                    cprint("\n🎭 Running Sentiment Analysis...", "cyan")
                    sentiment_agent.run()

                # ── Sleep until next cycle ─────────────────────────────────────
                next_run = datetime.now() + timedelta(minutes=SLEEP_BETWEEN_RUNS_MINUTES)
                cprint(f"\n😴 Sleeping until {next_run.strftime('%H:%M:%S')} "
                       f"({SLEEP_BETWEEN_RUNS_MINUTES} min)", "cyan")
                time.sleep(60 * SLEEP_BETWEEN_RUNS_MINUTES)

            except Exception as e:
                cprint(f"\n❌ Error in cycle: {str(e)}", "red")
                cprint("🔄 Continuing to next cycle in 60s...", "yellow")
                time.sleep(60)

    except KeyboardInterrupt:
        cprint("\n👋 Gracefully shutting down...", "yellow")
    except Exception as e:
        cprint(f"\n❌ Fatal error in main loop: {str(e)}", "red")
        raise


if __name__ == "__main__":
    _print_startup_banner()
    run_agents()
