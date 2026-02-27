"""
🌙 Moon Dev — Live Market Snapshot + Entry Timing Analysis
Pulls live data from Hyperliquid and runs signal fusion to find a good entry moment.

Usage: python -X utf8 src/scripts/market_snapshot.py
"""
import sys
sys.path.insert(0, '.')

import requests
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from termcolor import cprint

SYMBOLS = ['BTC', 'ETH', 'SOL']
HL_URL  = "https://api.hyperliquid.xyz/info"

def post(payload, timeout=15):
    r = requests.post(HL_URL, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()


def get_prices_funding_oi():
    data = post({"type": "metaAndAssetCtxs"})
    universe = data[0]["universe"]
    ctxs     = data[1]
    rows = []
    for sym in SYMBOLS:
        idx = next(i for i, u in enumerate(universe) if u["name"] == sym)
        c = ctxs[idx]
        price   = float(c["markPx"])
        funding = float(c["funding"]) * 100          # % per 8h
        oi_usd  = float(c["openInterest"]) * price
        oracle  = float(c["oraclePx"])
        spread  = (price - oracle) / oracle * 100    # mark vs oracle %
        rows.append(dict(symbol=sym, price=price, funding_8h=funding,
                         oi_usd=oi_usd, mark_oracle_spread=spread))
    return rows


def get_ohlcv(symbol, interval="15m", bars=96):
    end_ms   = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_ms = end_ms - bars * 15 * 60 * 1000
    data = post({"type": "candleSnapshot",
                 "req": {"coin": symbol, "interval": interval,
                         "startTime": start_ms, "endTime": end_ms}})
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    df = df.rename(columns={"t": "timestamp", "o": "open", "h": "high",
                             "l": "low", "c": "close", "v": "volume"})
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df[["timestamp", "open", "high", "low", "close", "volume"]].tail(bars)


def compute_technicals(df):
    """Returns dict of key technical indicators."""
    if df.empty or len(df) < 20:
        return {}
    close = df["close"]
    # EMA 20 / 50
    ema20 = close.ewm(span=20).mean().iloc[-1]
    ema50 = close.ewm(span=50).mean().iloc[-1]
    # RSI 14
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi   = (100 - 100 / (1 + rs)).iloc[-1]
    # ATR 14 (volatility)
    tr = pd.concat([df["high"] - df["low"],
                    (df["high"] - df["close"].shift()).abs(),
                    (df["low"]  - df["close"].shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().iloc[-1]
    atr_pct = atr / close.iloc[-1] * 100
    # Volume trend (last 4 bars vs prior 4)
    vol_recent = df["volume"].iloc[-4:].mean()
    vol_prior  = df["volume"].iloc[-8:-4].mean()
    vol_ratio  = vol_recent / vol_prior if vol_prior > 0 else 1.0
    # Price momentum (last bar % change)
    momentum_1bar = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100
    # 24h change (96 bars of 15m = 24h)
    change_24h = (close.iloc[-1] - close.iloc[0]) / close.iloc[0] * 100
    return dict(
        price=close.iloc[-1],
        ema20=ema20, ema50=ema50,
        trend="BULLISH" if ema20 > ema50 else "BEARISH",
        rsi=rsi,
        atr_pct=atr_pct,
        vol_ratio=vol_ratio,
        momentum_1bar=momentum_1bar,
        change_24h=change_24h,
    )


def score_entry(tech, funding_8h, oi_usd, fusion_score, fusion_dir):
    """
    Score the current moment for entry quality.
    Returns (score 0-100, reasons list, recommendation).
    """
    score = 50  # neutral baseline
    reasons = []

    # ── Trend alignment ──────────────────────────────────────
    if tech.get("trend") == "BULLISH":
        score += 8
        reasons.append("✅ EMA20 > EMA50 (uptrend)")
    else:
        score -= 8
        reasons.append("⚠️  EMA20 < EMA50 (downtrend)")

    # ── RSI — avoid overbought/oversold extremes ──────────────
    rsi = tech.get("rsi", 50)
    if 40 <= rsi <= 60:
        score += 10
        reasons.append(f"✅ RSI {rsi:.1f} — neutral zone (good entry)")
    elif 30 <= rsi < 40:
        score += 5
        reasons.append(f"✅ RSI {rsi:.1f} — slightly oversold (potential bounce)")
    elif 60 < rsi <= 70:
        score -= 5
        reasons.append(f"⚠️  RSI {rsi:.1f} — slightly overbought")
    elif rsi > 70:
        score -= 15
        reasons.append(f"❌ RSI {rsi:.1f} — overbought, wait for pullback")
    elif rsi < 30:
        score -= 15
        reasons.append(f"❌ RSI {rsi:.1f} — oversold, wait for stabilisation")

    # ── Funding rate — contrarian edge ───────────────────────
    if abs(funding_8h) < 0.01:
        score += 10
        reasons.append(f"✅ Funding {funding_8h:+.4f}% — neutral (no crowded trade)")
    elif funding_8h > 0.05:
        score -= 12
        reasons.append(f"❌ Funding {funding_8h:+.4f}% — longs paying heavily (crowded long)")
    elif funding_8h < -0.05:
        score -= 12
        reasons.append(f"❌ Funding {funding_8h:+.4f}% — shorts paying heavily (crowded short)")
    elif funding_8h > 0.02:
        score -= 5
        reasons.append(f"⚠️  Funding {funding_8h:+.4f}% — mildly elevated")
    else:
        score += 5
        reasons.append(f"✅ Funding {funding_8h:+.4f}% — low")

    # ── Volatility (ATR) — want moderate, not extreme ────────
    atr_pct = tech.get("atr_pct", 0)
    if 0.3 <= atr_pct <= 1.5:
        score += 8
        reasons.append(f"✅ ATR {atr_pct:.2f}% — healthy volatility")
    elif atr_pct > 2.5:
        score -= 10
        reasons.append(f"❌ ATR {atr_pct:.2f}% — very high volatility (risky entry)")
    elif atr_pct < 0.2:
        score -= 5
        reasons.append(f"⚠️  ATR {atr_pct:.2f}% — very low volatility (choppy)")

    # ── Volume confirmation ───────────────────────────────────
    vol_ratio = tech.get("vol_ratio", 1.0)
    if vol_ratio >= 1.3:
        score += 8
        reasons.append(f"✅ Volume surge {vol_ratio:.1f}x — strong participation")
    elif vol_ratio >= 1.0:
        score += 3
        reasons.append(f"✅ Volume {vol_ratio:.1f}x — normal")
    else:
        score -= 5
        reasons.append(f"⚠️  Volume declining {vol_ratio:.1f}x — weak participation")

    # ── Signal fusion alignment ───────────────────────────────
    if abs(fusion_score) >= 30:
        score += 12
        reasons.append(f"✅ Signal fusion strong: {fusion_dir} ({fusion_score:+.1f})")
    elif abs(fusion_score) >= 15:
        score += 6
        reasons.append(f"✅ Signal fusion moderate: {fusion_dir} ({fusion_score:+.1f})")
    else:
        score += 0
        reasons.append(f"⚠️  Signal fusion neutral ({fusion_score:+.1f}) — wait for conviction")

    # ── 24h momentum ─────────────────────────────────────────
    ch24 = tech.get("change_24h", 0)
    if -3 <= ch24 <= 3:
        score += 5
        reasons.append(f"✅ 24h change {ch24:+.2f}% — consolidating (good entry zone)")
    elif ch24 > 8:
        score -= 8
        reasons.append(f"⚠️  24h change {ch24:+.2f}% — extended move, chasing risk")
    elif ch24 < -8:
        score -= 8
        reasons.append(f"⚠️  24h change {ch24:+.2f}% — sharp drop, wait for base")

    score = max(0, min(100, score))

    if score >= 70:
        rec = "🟢 GOOD ENTRY — conditions aligned"
    elif score >= 55:
        rec = "🟡 ACCEPTABLE — proceed with caution, small size"
    elif score >= 40:
        rec = "🟠 WAIT — conditions mixed, better opportunity likely soon"
    else:
        rec = "🔴 AVOID — poor conditions, high risk of loss"

    return score, reasons, rec


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    cprint("\n" + "═"*62, "cyan")
    cprint("  🌙 Moon Dev — Live Market Snapshot + Entry Timing", "cyan", attrs=["bold"])
    cprint(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", "cyan")
    cprint("═"*62, "cyan")

    # ── Signal Fusion ─────────────────────────────────────────
    cprint("\n📡 Running Signal Fusion...", "white")
    try:
        from src.agents.signal_fusion_agent import get_fused_signal
        sig = get_fused_signal(verbose=False)
        fusion_score = sig["score"]
        fusion_dir   = sig["direction"]
        fusion_conf  = sig["confidence"]
        fusion_src   = sig["active_sources"]
        cprint(f"   Score={fusion_score:+.1f}  Dir={fusion_dir}  "
               f"Conf={fusion_conf:.1f}%  Sources={fusion_src}/10", "white")
    except Exception as e:
        cprint(f"   Signal fusion error: {e}", "yellow")
        fusion_score, fusion_dir, fusion_conf, fusion_src = 0, "NEUTRAL", 0, 0

    # ── Prices / Funding / OI ─────────────────────────────────
    cprint("\n📊 Fetching live prices, funding, OI...", "white")
    try:
        mkt = get_prices_funding_oi()
    except Exception as e:
        cprint(f"   Market data error: {e}", "red")
        mkt = []

    # ── Per-symbol analysis ───────────────────────────────────
    best_symbol = None
    best_score  = -1
    all_scores  = {}

    for row in mkt:
        sym = row["symbol"]
        cprint(f"\n{'─'*62}", "cyan")
        cprint(f"  {sym}  ${row['price']:,.2f}  |  "
               f"Funding {row['funding_8h']:+.4f}%/8h  |  "
               f"OI ${row['oi_usd']/1e9:.2f}B", "white", attrs=["bold"])

        # OHLCV + technicals
        try:
            df = get_ohlcv(sym, bars=96)
            tech = compute_technicals(df)
        except Exception as e:
            cprint(f"  OHLCV error: {e}", "yellow")
            tech = {}

        if tech:
            cprint(f"  Trend: {tech['trend']}  RSI: {tech['rsi']:.1f}  "
                   f"ATR: {tech['atr_pct']:.2f}%  24h: {tech['change_24h']:+.2f}%  "
                   f"Vol: {tech['vol_ratio']:.1f}x", "white")

        # Entry score
        entry_score, reasons, rec = score_entry(
            tech, row["funding_8h"], row["oi_usd"], fusion_score, fusion_dir
        )
        all_scores[sym] = entry_score

        colour = "green" if entry_score >= 70 else ("yellow" if entry_score >= 55 else
                 ("yellow" if entry_score >= 40 else "red"))
        cprint(f"\n  Entry Score: {entry_score}/100", colour, attrs=["bold"])
        cprint(f"  {rec}", colour)
        cprint(f"\n  Factors:", "white")
        for r in reasons:
            cprint(f"    {r}", "white")

        if entry_score > best_score:
            best_score  = entry_score
            best_symbol = sym

    # ── Overall Recommendation ────────────────────────────────
    cprint(f"\n{'═'*62}", "cyan")
    cprint("  🎯 OVERALL ENTRY RECOMMENDATION", "cyan", attrs=["bold"])
    cprint(f"{'═'*62}", "cyan")

    for sym, sc in sorted(all_scores.items(), key=lambda x: -x[1]):
        bar = "█" * (sc // 5) + "░" * (20 - sc // 5)
        colour = "green" if sc >= 70 else ("yellow" if sc >= 55 else "red")
        cprint(f"  {sym:<5} [{bar}] {sc}/100", colour)

    cprint(f"\n  Best opportunity: {best_symbol} (score={best_score}/100)", "white", attrs=["bold"])

    if best_score >= 70:
        cprint(f"\n  🟢 NOW is a good time to start live trading on {best_symbol}.", "green", attrs=["bold"])
        cprint(f"     Signal fusion: {fusion_dir} ({fusion_score:+.1f})", "green")
        cprint(f"     Suggested action: Set LIVE_TRADING=True and run src/main.py", "green")
    elif best_score >= 55:
        cprint(f"\n  🟡 Conditions are acceptable but not ideal.", "yellow", attrs=["bold"])
        cprint(f"     Consider starting with minimum size (usd_size=5).", "yellow")
        cprint(f"     Re-run this script in 15–30 min for a better read.", "yellow")
    else:
        cprint(f"\n  🔴 Wait for better conditions.", "red", attrs=["bold"])
        cprint(f"     Signal fusion is NEUTRAL — no strong directional edge.", "red")
        cprint(f"     Re-run in 30–60 min or wait for a clear trend to form.", "red")

    cprint(f"\n  ⚠️  This is analysis only — not financial advice.", "white")
    cprint(f"     Never risk more than you can afford to lose.", "white")
    cprint(f"{'═'*62}\n", "cyan")
