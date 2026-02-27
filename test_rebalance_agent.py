#!/usr/bin/env python3
"""
🌙 Moon Dev's Rebalance Agent Test Script
Quick test to verify the rebalance agent can be imported and initialized
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_import():
    """Test that the rebalance agent can be imported"""
    print("🔍 Testing rebalance agent import...")
    try:
        from src.agents.rebalance_agent import RebalanceAgent
        print("✅ Import successful!")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_config():
    """Test that config values are accessible"""
    print("\n🔍 Testing config access...")
    try:
        from src.config import (
            EXCHANGE,
            LIVE_TRADING,
            HYPERLIQUID_SYMBOLS,
            MAX_POSITION_PERCENTAGE,
            CASH_PERCENTAGE,
            MINIMUM_BALANCE_USD
        )
        
        print(f"  • EXCHANGE: {EXCHANGE}")
        print(f"  • LIVE_TRADING: {LIVE_TRADING}")
        print(f"  • HYPERLIQUID_SYMBOLS: {HYPERLIQUID_SYMBOLS}")
        print(f"  • MAX_POSITION_PERCENTAGE: {MAX_POSITION_PERCENTAGE}%")
        print(f"  • CASH_PERCENTAGE: {CASH_PERCENTAGE}%")
        print(f"  • MINIMUM_BALANCE_USD: ${MINIMUM_BALANCE_USD}")
        print("✅ Config access successful!")
        return True
    except Exception as e:
        print(f"❌ Config access failed: {e}")
        return False

def test_nice_funcs():
    """Test that nice_funcs_hyperliquid can be imported"""
    print("\n🔍 Testing nice_funcs_hyperliquid import...")
    try:
        from src import nice_funcs_hyperliquid as n
        
        # Check that required functions exist
        required_funcs = [
            'get_position',
            'get_balance',
            'get_account_value',
            'market_buy',
            'market_sell',
            '_get_account_from_env',
            'get_all_positions',
            'ask_bid'
        ]
        
        for func_name in required_funcs:
            if hasattr(n, func_name):
                print(f"  ✅ {func_name} found")
            else:
                print(f"  ❌ {func_name} NOT found")
                return False
        
        print("✅ All required functions found!")
        return True
    except Exception as e:
        print(f"❌ nice_funcs_hyperliquid import failed: {e}")
        return False

def test_model_factory():
    """Test that ModelFactory can be imported"""
    print("\n🔍 Testing ModelFactory import...")
    try:
        from src.models.model_factory import ModelFactory
        print("✅ ModelFactory import successful!")
        return True
    except Exception as e:
        print(f"❌ ModelFactory import failed: {e}")
        return False

def test_signal_fusion_file():
    """Test that signal fusion file exists"""
    print("\n🔍 Testing signal fusion file...")
    signal_file = "src/data/signal_fusion/latest_signal.json"
    
    if os.path.exists(signal_file):
        print(f"✅ Signal fusion file found: {signal_file}")
        try:
            import json
            with open(signal_file, 'r') as f:
                data = json.load(f)
            print(f"  • Direction: {data.get('direction', 'N/A')}")
            print(f"  • Score: {data.get('score', 'N/A')}")
            print(f"  • Confidence: {data.get('confidence', 'N/A')}%")
            return True
        except Exception as e:
            print(f"⚠️ Could not read signal fusion file: {e}")
            return True  # File exists, just can't read it
    else:
        print(f"⚠️ Signal fusion file not found (will use neutral bias)")
        return True  # Not critical

def main():
    """Run all tests"""
    print("="*60)
    print("🌙 MOON DEV'S REBALANCE AGENT TEST SUITE 🌙")
    print("="*60)
    
    tests = [
        ("Import Test", test_import),
        ("Config Test", test_config),
        ("Nice Funcs Test", test_nice_funcs),
        ("ModelFactory Test", test_model_factory),
        ("Signal Fusion Test", test_signal_fusion_file),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("="*60)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✨ All tests passed! Rebalance agent is ready to use.")
        print("\nTo run the agent:")
        print("  python src/agents/rebalance_agent.py")
    else:
        print("⚠️ Some tests failed. Check dependencies and configuration.")
    
    print("="*60)

if __name__ == "__main__":
    main()
