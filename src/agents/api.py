"""
Moon Dev's API Handler — v2 (JSON REST)
Built with love by Moon Dev

Base URL: https://api.moondev.com
Auth: X-API-Key header (get key at https://moondev.com)
Rate limits: 60 req/s sustained, 200 burst

Quick Start:
    from agents.api import MoonDevAPI

    api = MoonDevAPI()  # reads MOONDEV_API_KEY from .env

    # Liquidations (Hyperliquid native)
    liqs = api.get_liquidation_data('1h')

    # All exchanges combined
    all_liqs = api.get_all_liquidations('1h')

    # Smart money signals
    signals = api.get_smart_money_signals('1h')

    # Order flow & imbalance
    flow = api.get_orderflow()
    imb  = api.get_imbalance('1h')

    # HLP sentiment
    sent = api.get_hlp_sentiment()

    # Whale data
    whales = api.get_whale_data()

    # Market prices (228 coins)
    prices = api.get_prices()

    # Position snapshots (liquidation risk)
    snaps = api.get_position_snapshots('BTC', hours=24)

Available timeframes for liquidation/imbalance endpoints:
    10m, 1h, 4h, 12h, 24h, 2d, 7d, 14d, 30d

disclaimer: not financial advice. use at your own risk.
"""

import os
import pandas as pd
import requests
import traceback
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


class MoonDevAPI:
    BASE_URL = "https://api.moondev.com"

    def __init__(self, api_key=None, base_url=None):
        """Initialize the API handler.

        Args:
            api_key: Moon Dev API key (defaults to MOONDEV_API_KEY env var)
            base_url: Ignored — kept for backward compatibility with old callers
        """
        self.api_key = api_key or os.getenv('MOONDEV_API_KEY')
        self.base_url = self.BASE_URL
        self.session = requests.Session()
        if self.api_key:
            self.session.headers['X-API-Key'] = self.api_key

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _fetch_json(self, path: str, params: dict = None, timeout: int = 30):
        """GET a JSON endpoint, return parsed dict/list or None on error."""
        url = f"{self.base_url}{path}"
        try:
            resp = self.session.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"MoonDevAPI error on {path}: {e}")
            return None

    def _json_to_df(self, data) -> pd.DataFrame:
        """Convert JSON response (list or dict) to DataFrame."""
        if data is None:
            return pd.DataFrame()
        if isinstance(data, list):
            return pd.DataFrame(data)
        if isinstance(data, dict):
            # Some endpoints wrap data in a key
            for key in ('data', 'records', 'results', 'liquidations', 'positions'):
                if key in data and isinstance(data[key], list):
                    return pd.DataFrame(data[key])
            return pd.DataFrame([data])
        return pd.DataFrame()

    # ── Market Data ──────────────────────────────────────────────────────────

    def get_prices(self) -> pd.DataFrame:
        """GET /api/prices — all 228 coins with funding rates and OI."""
        return self._json_to_df(self._fetch_json("/api/prices"))

    def get_price(self, coin: str) -> dict:
        """GET /api/price/{coin} — single coin bid/ask/spread."""
        return self._fetch_json(f"/api/price/{coin.lower()}") or {}

    def get_orderbook(self, coin: str) -> dict:
        """GET /api/orderbook/{coin} — L2 orderbook (~20 levels each side)."""
        return self._fetch_json(f"/api/orderbook/{coin.lower()}") or {}

    def get_candles(self, coin: str, interval: str = '1h') -> pd.DataFrame:
        """GET /api/candles/{coin}?interval={1m,5m,15m,1h,4h,1d}."""
        return self._json_to_df(
            self._fetch_json(f"/api/candles/{coin.lower()}", params={"interval": interval})
        )

    # ── Liquidations ─────────────────────────────────────────────────────────

    def get_liquidation_data(self, timeframe: str = '1h', limit=None) -> pd.DataFrame:
        """GET /api/liquidations/{timeframe}.json — Hyperliquid native.
        Timeframes: 10m, 1h, 4h, 12h, 24h, 2d, 7d, 14d, 30d.
        The 'limit' param is kept for backward compat but unused (API pre-aggregates).
        """
        return self._json_to_df(self._fetch_json(f"/api/liquidations/{timeframe}.json"))

    def get_liquidation_stats(self) -> dict:
        """GET /api/liquidations/stats.json — aggregate stats."""
        return self._fetch_json("/api/liquidations/stats.json") or {}

    def get_all_liquidations(self, timeframe: str = '1h') -> pd.DataFrame:
        """GET /api/all_liquidations/{timeframe}.json — Binance+Bybit+OKX+HL combined."""
        return self._json_to_df(self._fetch_json(f"/api/all_liquidations/{timeframe}.json"))

    def get_binance_liquidations(self, timeframe: str = '1h') -> pd.DataFrame:
        """GET /api/binance_liquidations/{timeframe}.json."""
        return self._json_to_df(self._fetch_json(f"/api/binance_liquidations/{timeframe}.json"))

    def get_bybit_liquidations(self, timeframe: str = '1h') -> pd.DataFrame:
        """GET /api/bybit_liquidations/{timeframe}.json."""
        return self._json_to_df(self._fetch_json(f"/api/bybit_liquidations/{timeframe}.json"))

    def get_okx_liquidations(self, timeframe: str = '1h') -> pd.DataFrame:
        """GET /api/okx_liquidations/{timeframe}.json."""
        return self._json_to_df(self._fetch_json(f"/api/okx_liquidations/{timeframe}.json"))

    # ── Core Data & Whale Tracking ───────────────────────────────────────────

    def get_positions(self) -> pd.DataFrame:
        """GET /api/positions.json — top 50 positions across all symbols."""
        return self._json_to_df(self._fetch_json("/api/positions.json"))

    def get_all_positions(self) -> pd.DataFrame:
        """GET /api/positions/all.json — all 148 symbols with top 50 each."""
        return self._json_to_df(self._fetch_json("/api/positions/all.json"))

    def get_whale_data(self) -> pd.DataFrame:
        """GET /api/whales.json — recent whale trades ($25k+)."""
        return self._json_to_df(self._fetch_json("/api/whales.json"))

    def get_buyers(self) -> pd.DataFrame:
        """GET /api/buyers.json — recent buyers ($5k+)."""
        return self._json_to_df(self._fetch_json("/api/buyers.json"))

    def get_depositors(self) -> pd.DataFrame:
        """GET /api/depositors.json — all Hyperliquid depositors."""
        return self._json_to_df(self._fetch_json("/api/depositors.json"))

    def get_whale_addresses(self) -> list:
        """GET /api/whale_addresses.txt — plain text whale address list."""
        try:
            resp = self.session.get(
                f"{self.base_url}/api/whale_addresses.txt", timeout=30
            )
            resp.raise_for_status()
            return [line.strip() for line in resp.text.splitlines() if line.strip()]
        except Exception as e:
            print(f"MoonDevAPI error fetching whale addresses: {e}")
            return []

    # ── Open Interest (via positions endpoint) ───────────────────────────────

    def get_oi_data(self) -> pd.DataFrame:
        """GET /api/positions.json — replaces old /files/oi.csv.
        Returns DataFrame with position data including OI.
        """
        return self.get_positions()

    def get_oi_total(self) -> pd.DataFrame:
        """Backward compat — returns same as get_positions()."""
        return self.get_positions()

    # ── Tick Data ────────────────────────────────────────────────────────────

    def get_tick_data(self, symbol: str, timeframe: str = None) -> pd.DataFrame:
        """GET /api/ticks/{symbol}.json — current/latest tick data.
        For historical: /api/ticks/{symbol}_{10m,1h,4h,24h,7d}.json
        """
        if timeframe:
            path = f"/api/ticks/{symbol.lower()}_{timeframe}.json"
        else:
            path = f"/api/ticks/{symbol.lower()}.json"
        return self._json_to_df(self._fetch_json(path))

    def get_tick_stats(self) -> dict:
        """GET /api/ticks/stats.json — collection statistics."""
        return self._fetch_json("/api/ticks/stats.json") or {}

    # ── Trades & Order Flow ──────────────────────────────────────────────────

    def get_trades(self) -> pd.DataFrame:
        """GET /api/trades.json — last 1000 trades."""
        return self._json_to_df(self._fetch_json("/api/trades.json"))

    def get_large_trades(self) -> pd.DataFrame:
        """GET /api/large_trades.json — trades > $100k."""
        return self._json_to_df(self._fetch_json("/api/large_trades.json"))

    def get_orderflow(self) -> pd.DataFrame:
        """GET /api/orderflow.json — current order flow metrics."""
        data = self._fetch_json("/api/orderflow.json")
        if data is None:
            return pd.DataFrame()
        if isinstance(data, dict):
            return pd.DataFrame([data])
        return self._json_to_df(data)

    def get_orderflow_stats(self) -> dict:
        """GET /api/orderflow/stats.json — aggregated stats."""
        return self._fetch_json("/api/orderflow/stats.json") or {}

    def get_imbalance(self, timeframe: str = '1h') -> pd.DataFrame:
        """GET /api/imbalance/{timeframe}.json — buy/sell imbalance for 130 symbols."""
        return self._json_to_df(self._fetch_json(f"/api/imbalance/{timeframe}.json"))

    # ── Smart Money ──────────────────────────────────────────────────────────

    def get_smart_money_rankings(self) -> pd.DataFrame:
        """GET /api/smart_money/rankings.json — top 100 vs bottom 100 by PnL."""
        return self._json_to_df(self._fetch_json("/api/smart_money/rankings.json"))

    def get_smart_money_leaderboard(self) -> pd.DataFrame:
        """GET /api/smart_money/leaderboard.json — top 50 with metrics."""
        return self._json_to_df(self._fetch_json("/api/smart_money/leaderboard.json"))

    def get_smart_money_signals(self, timeframe: str = '1h') -> pd.DataFrame:
        """GET /api/smart_money/signals_{timeframe}.json — trading signals."""
        return self._json_to_df(self._fetch_json(f"/api/smart_money/signals_{timeframe}.json"))

    # ── Position Snapshots (Liquidation Risk) ────────────────────────────────

    def get_position_snapshots(self, symbol: str, hours: int = 24) -> pd.DataFrame:
        """GET /api/position_snapshots/symbol/{sym}?hours=N — historical snapshots."""
        return self._json_to_df(
            self._fetch_json(f"/api/position_snapshots/symbol/{symbol.upper()}",
                             params={"hours": hours})
        )

    def get_position_snapshot_stats(self, hours: int = 24) -> dict:
        """GET /api/position_snapshots/stats?hours=N — aggregate stats."""
        return self._fetch_json("/api/position_snapshots/stats",
                                params={"hours": hours}) or {}

    # ── HLP (Hyperliquidity Provider) ────────────────────────────────────────

    def get_hlp_positions(self) -> pd.DataFrame:
        """GET /api/hlp/positions — all 7 strategy positions."""
        return self._json_to_df(self._fetch_json("/api/hlp/positions"))

    def get_hlp_trades(self, limit: int = 100) -> pd.DataFrame:
        """GET /api/hlp/trades?limit=N — historical fills."""
        return self._json_to_df(
            self._fetch_json("/api/hlp/trades", params={"limit": limit})
        )

    def get_hlp_sentiment(self) -> dict:
        """GET /api/hlp/sentiment — net delta with z-scores and signals."""
        return self._fetch_json("/api/hlp/sentiment") or {}

    def get_hlp_liquidators(self) -> dict:
        """GET /api/hlp/liquidators/status — real-time liquidator status."""
        return self._fetch_json("/api/hlp/liquidators/status") or {}

    def get_hlp_market_maker(self) -> dict:
        """GET /api/hlp/market-maker — strategy B BTC/ETH/SOL tracking."""
        return self._fetch_json("/api/hlp/market-maker") or {}

    def get_hlp_timing(self) -> dict:
        """GET /api/hlp/timing — hourly and session profitability."""
        return self._fetch_json("/api/hlp/timing") or {}

    def get_hlp_correlation(self) -> dict:
        """GET /api/hlp/correlation — delta-price correlation analysis."""
        return self._fetch_json("/api/hlp/correlation") or {}

    # ── Blockchain Events & Contracts ────────────────────────────────────────

    def get_events(self) -> pd.DataFrame:
        """GET /api/events.json — decoded Hyperliquid L1 events."""
        return self._json_to_df(self._fetch_json("/api/events.json"))

    def get_contracts(self) -> pd.DataFrame:
        """GET /api/contracts.json — complete smart contract registry."""
        return self._json_to_df(self._fetch_json("/api/contracts.json"))

    # ── User Data ────────────────────────────────────────────────────────────

    def get_user_positions(self, address: str) -> pd.DataFrame:
        """GET /api/user/{address}/positions — current positions."""
        return self._json_to_df(self._fetch_json(f"/api/user/{address}/positions"))

    def get_user_fills(self, address: str, limit: int = 100) -> pd.DataFrame:
        """GET /api/user/{address}/fills?limit=N — trade history."""
        return self._json_to_df(
            self._fetch_json(f"/api/user/{address}/fills", params={"limit": limit})
        )

    def get_account(self, address: str) -> dict:
        """GET /api/account/{address} — full wallet state."""
        return self._fetch_json(f"/api/account/{address}") or {}

    # ── Backward compat (deprecated) ─────────────────────────────────────────

    def get_funding_data(self) -> pd.DataFrame:
        """Deprecated — use funding_collector.py (free via native HL API)."""
        print("MoonDevAPI.get_funding_data() deprecated — use funding_collector.py")
        return pd.DataFrame()

    def get_token_addresses(self) -> pd.DataFrame:
        """Deprecated — old Solana token endpoint."""
        print("MoonDevAPI.get_token_addresses() deprecated")
        return pd.DataFrame()

    def get_copybot_follow_list(self) -> pd.DataFrame:
        """GET copybot follow list (path may vary)."""
        data = self._fetch_json("/copybot/data/follow_list")
        return self._json_to_df(data)

    def get_copybot_recent_transactions(self) -> pd.DataFrame:
        """GET copybot recent transactions."""
        data = self._fetch_json("/copybot/data/recent_txs")
        return self._json_to_df(data)

    def get_agg_positions_hlp(self) -> pd.DataFrame:
        """Backward compat — redirects to get_hlp_positions()."""
        return self.get_hlp_positions()

    def get_positions_hlp(self) -> pd.DataFrame:
        """Backward compat — redirects to get_hlp_positions()."""
        return self.get_hlp_positions()


if __name__ == "__main__":
    print("Moon Dev API v2 Test Suite")
    print("=" * 50)

    api = MoonDevAPI()

    # Market data
    print("\nPrices...")
    prices = api.get_prices()
    print(f"  Got {len(prices)} coins" if not prices.empty else "  No data")

    # Liquidations
    print("\nLiquidations (1h)...")
    liqs = api.get_liquidation_data('1h')
    print(f"  Got {len(liqs)} records" if not liqs.empty else "  No data")
    if not liqs.empty:
        print(f"  Columns: {liqs.columns.tolist()}")

    # Smart money
    print("\nSmart money signals (1h)...")
    sm = api.get_smart_money_signals('1h')
    print(f"  Got {len(sm)} signals" if not sm.empty else "  No data")

    # Order flow
    print("\nOrder flow...")
    of = api.get_orderflow()
    print(f"  Got {len(of)} records" if not of.empty else "  No data")

    # HLP sentiment
    print("\nHLP sentiment...")
    hlp = api.get_hlp_sentiment()
    print(f"  {hlp}" if hlp else "  No data")

    # Whale addresses
    print("\nWhale addresses...")
    addrs = api.get_whale_addresses()
    print(f"  Got {len(addrs)} addresses")

    # Positions (OI)
    print("\nPositions (OI)...")
    pos = api.get_positions()
    print(f"  Got {len(pos)} records" if not pos.empty else "  No data")
    if not pos.empty:
        print(f"  Columns: {pos.columns.tolist()}")

    print("\nMoon Dev API v2 Test Complete!")
