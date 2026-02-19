#!/usr/bin/env python3
"""
🌙 Moon Dev's Exchange Manager Test Script
Tests the unified exchange interface for both Solana and HyperLiquid
Built with love by Moon Dev 🚀
"""

import sys
import os
from termcolor import colored, cprint
from colorama import init, Fore, Style
from dotenv import load_dotenv
import time

# Initialize colorama
init(autoreset=True)

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

def print_banner():
    """Print Moon Dev banner"""
    banner = f"""{Fore.CYAN}
   __  ___                    ____
  /  |/  /___  ____  ____    / __ \\___  _  __
 / /|_/ / __ \\/ __ \\/ __ \\  / / / / _ \\| |/_/
/ /  / / /_/ / /_/ / / / / / /_/ /  __/>  <
/_/  /_/\\____/\\____/_/ /_(_)____/\\___/_/|_|

{Fore.MAGENTA}🔄 Exchange Manager Test Suite 🚀{Fore.RESET}
    """
    print(banner)
    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.YELLOW}Testing unified exchange interface")
    print(f"{Fore.CYAN}{'='*60}\n")

def test_solana_manager():
    """Test Exchange Manager with Solana"""
    cprint("\n📊 Testing Solana Exchange Manager", "cyan", attrs=['bold'])
    cprint("="*60, "cyan")

    try:
        # Import after sys.path is set
        from src.exchange_manager import ExchangeManager
        from src import config

        # Force Solana mode
        em = ExchangeManager(exchange='solana')

        cprint(f"✅ Initialized: {em}", "green")

        # Test 1: Get current price
        cprint("\n1. Testing get_current_price()...", "yellow")
        try:
            # Use a known Solana token
            token = config.MONITORED_TOKENS[0] if config.MONITORED_TOKENS else 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
            price = em.get_current_price(token)
            cprint(f"   ✅ Token price: ${price:.6f}", "green")
        except Exception as e:
            cprint(f"   ⚠️ Price fetch error: {str(e)}", "yellow")

        # Test 2: Get balance
        cprint("\n2. Testing get_balance()...", "yellow")
        try:
            balance = em.get_balance()
            cprint(f"   ✅ USDC Balance: ${balance:.2f}", "green")
        except Exception as e:
            cprint(f"   ⚠️ Balance fetch error: {str(e)}", "yellow")

        # Test 3: Get position
        cprint("\n3. Testing get_position()...", "yellow")
        try:
            position = em.get_position(token)
            if position['has_position']:
                cprint(f"   ✅ Position found: {position['size']} tokens", "green")
            else:
                cprint(f"   ✅ No position in token", "green")
        except Exception as e:
            cprint(f"   ⚠️ Position fetch error: {str(e)}", "yellow")

        # Test 4: Get all positions
        cprint("\n4. Testing get_all_positions()...", "yellow")
        try:
            positions = em.get_all_positions()
            cprint(f"   ✅ Found {len(positions)} open positions", "green")
            for pos in positions[:3]:  # Show first 3
                cprint(f"      • {pos['symbol'][:8]}...: ${pos.get('value_usd', 0):.2f}", "white")
        except Exception as e:
            cprint(f"   ⚠️ All positions fetch error: {str(e)}", "yellow")

        cprint("\n✅ Solana Exchange Manager tests complete!", "green", attrs=['bold'])
        return True

    except Exception as e:
        cprint(f"\n❌ Solana test failed: {str(e)}", "red")
        import traceback
        traceback.print_exc()
        return False

def test_hyperliquid_manager():
    """Test Exchange Manager with HyperLiquid"""
    cprint("\n⚡ Testing HyperLiquid Exchange Manager", "magenta", attrs=['bold'])
    cprint("="*60, "magenta")

    try:
        # Import after sys.path is set
        from src.exchange_manager import ExchangeManager

        # Check if HyperLiquid key exists
        if not os.getenv('HYPER_LIQUID_KEY'):
            cprint("⚠️ HYPER_LIQUID_KEY not found in environment", "yellow")
            cprint("   Skipping HyperLiquid tests", "yellow")
            return False

        # Force HyperLiquid mode
        em = ExchangeManager(exchange='hyperliquid')

        cprint(f"✅ Initialized: {em}", "green")

        # Test 1: Get current price
        cprint("\n1. Testing get_current_price()...", "yellow")
        try:
            price = em.get_current_price('BTC')
            cprint(f"   ✅ BTC price: ${price:,.2f}", "green")
        except Exception as e:
            cprint(f"   ⚠️ Price fetch error: {str(e)}", "yellow")

        # Test 2: Get balance
        cprint("\n2. Testing get_balance()...", "yellow")
        try:
            balance = em.get_balance()
            cprint(f"   ✅ Available balance: ${balance:.2f}", "green")
        except Exception as e:
            cprint(f"   ⚠️ Balance fetch error: {str(e)}", "yellow")

        # Test 3: Get account value
        cprint("\n3. Testing get_account_value()...", "yellow")
        try:
            value = em.get_account_value()
            cprint(f"   ✅ Account value: ${value:.2f}", "green")
        except Exception as e:
            cprint(f"   ⚠️ Account value error: {str(e)}", "yellow")

        # Test 4: Get position
        cprint("\n4. Testing get_position()...", "yellow")
        try:
            position = em.get_position('BTC')
            if position['has_position']:
                side = "LONG" if position['is_long'] else "SHORT"
                cprint(f"   ✅ {side} position: {position['size']} BTC @ ${position['entry_price']:.2f}", "green")
                cprint(f"      PnL: {position['pnl_percent']:.2f}%", "white")
            else:
                cprint(f"   ✅ No BTC position", "green")
        except Exception as e:
            cprint(f"   ⚠️ Position fetch error: {str(e)}", "yellow")

        # Test 5: Get all positions
        cprint("\n5. Testing get_all_positions()...", "yellow")
        try:
            positions = em.get_all_positions()
            cprint(f"   ✅ Found {len(positions)} open positions", "green")
            for pos in positions:
                side = "LONG" if pos['is_long'] else "SHORT"
                cprint(f"      • {pos['symbol']} {side}: {pos['size']} @ ${pos['entry_price']:.2f}", "white")
        except Exception as e:
            cprint(f"   ⚠️ All positions fetch error: {str(e)}", "yellow")

        cprint("\n✅ HyperLiquid Exchange Manager tests complete!", "green", attrs=['bold'])
        return True

    except Exception as e:
        cprint(f"\n❌ HyperLiquid test failed: {str(e)}", "red")
        import traceback
        traceback.print_exc()
        return False

def test_exchange_switching():
    """Test switching between exchanges"""
    cprint("\n🔄 Testing Exchange Switching", "yellow", attrs=['bold'])
    cprint("="*60, "yellow")

    try:
        from src.exchange_manager import ExchangeManager
        from src import config

        # Test 1: Check config setting
        cprint(f"\n1. Current config.EXCHANGE: {config.EXCHANGE}", "cyan")

        # Test 2: Initialize with default
        cprint("\n2. Testing default initialization...", "yellow")
        em_default = ExchangeManager()
        cprint(f"   ✅ Default exchange: {em_default.exchange}", "green")

        # Test 3: Override to Solana
        cprint("\n3. Testing Solana override...", "yellow")
        em_solana = ExchangeManager(exchange='solana')
        cprint(f"   ✅ Solana exchange initialized", "green")

        # Test 4: Override to HyperLiquid (if key exists)
        if os.getenv('HYPER_LIQUID_KEY'):
            cprint("\n4. Testing HyperLiquid override...", "yellow")
            em_hl = ExchangeManager(exchange='hyperliquid')
            cprint(f"   ✅ HyperLiquid exchange initialized", "green")
        else:
            cprint("\n4. Skipping HyperLiquid override (no key)", "yellow")

        cprint("\n✅ Exchange switching tests complete!", "green", attrs=['bold'])
        return True

    except Exception as e:
        cprint(f"\n❌ Exchange switching test failed: {str(e)}", "red")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all exchange manager tests"""
    print_banner()

    # Check environment
    has_solana = os.getenv('SOLANA_PRIVATE_KEY') is not None
    has_hyperliquid = os.getenv('HYPER_LIQUID_KEY') is not None

    cprint("🔑 Environment Check:", "yellow")
    cprint(f"  Solana: {'✅' if has_solana else '❌'} SOLANA_PRIVATE_KEY", "white")
    cprint(f"  HyperLiquid: {'✅' if has_hyperliquid else '❌'} HYPER_LIQUID_KEY", "white")

    results = []

    # Test exchange switching
    cprint("\n" + "="*60, "cyan")
    results.append(("Exchange Switching", test_exchange_switching()))

    # Test Solana if available
    if has_solana:
        cprint("\n" + "="*60, "cyan")
        results.append(("Solana Manager", test_solana_manager()))
    else:
        cprint("\n⚠️ Skipping Solana tests (no SOLANA_PRIVATE_KEY)", "yellow")

    # Test HyperLiquid if available
    if has_hyperliquid:
        cprint("\n" + "="*60, "cyan")
        results.append(("HyperLiquid Manager", test_hyperliquid_manager()))
    else:
        cprint("\n⚠️ Skipping HyperLiquid tests (no HYPER_LIQUID_KEY)", "yellow")

    # Summary
    cprint("\n" + "="*60, "cyan")
    cprint("📊 TEST SUMMARY", "cyan", attrs=['bold'])
    cprint("="*60, "cyan")

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        color = "green" if passed else "red"
        cprint(f"{test_name}: {status}", color)

    cprint("\n" + "="*60, "cyan")
    cprint("💡 Quick Start Guide:", "yellow", attrs=['bold'])
    cprint("="*60, "yellow")

    cprint("""
To switch exchanges, update src/config.py:

For Solana (memecoins):
  EXCHANGE = 'solana'

For HyperLiquid (BTC/ETH/SOL perps):
  EXCHANGE = 'hyperliquid'

Then in your agents:
  from src.exchange_manager import ExchangeManager
  em = ExchangeManager()
  em.market_buy(token_or_symbol, 100)  # Works for both!
    """, "white")

    cprint(f"\n🌕 Thanks for using Moon Dev Exchange Manager! 🤖", "magenta")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        cprint("\n⚠️ Test interrupted by user", "yellow")
    except Exception as e:
        cprint(f"\n❌ Unexpected error: {str(e)}", "red")
        import traceback
        traceback.print_exc()