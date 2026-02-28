"""
Moon Dev's Strategy Scorer & Leaderboard
Built with love by Moon Dev

Parses backtesting.py stats output, scores strategies with a composite metric,
and maintains a ranked leaderboard CSV.

Standalone: python src/agents/strategy_scorer.py
"""

import os
import re
import csv
from datetime import datetime, timezone
from pathlib import Path
from termcolor import cprint

# ============================================================================
# CONFIGURATION
# ============================================================================

LEADERBOARD_FILE = "src/data/rbi/leaderboard.csv"

# Minimum thresholds — strategies below these are auto-rejected
MIN_TRADES = 20
MIN_SHARPE = 0.0

# Scoring weights (must sum to 1.0)
WEIGHT_SHARPE = 0.40
WEIGHT_RETURN = 0.30
WEIGHT_DRAWDOWN = 0.20
WEIGHT_WIN_RATE = 0.10

# Leaderboard CSV columns
LEADERBOARD_COLUMNS = [
    "timestamp", "strategy_name", "source_file", "composite_score",
    "return_pct", "sharpe", "sortino", "max_drawdown_pct", "trades",
    "win_rate_pct", "profit_factor", "avg_trade_pct", "buy_hold_return_pct",
    "exposure_pct", "equity_final",
]


# ============================================================================
# STAT PARSING
# ============================================================================

def parse_backtest_stats(stdout: str) -> dict:
    """Parse backtesting.py stats output into a structured dict.

    The stats are printed as:
        Key Name                           Value
    one per line. We regex-match known fields.

    Returns:
        dict with numeric values (float), or empty dict if parsing fails.
    """
    if not stdout:
        return {}

    # Map of stat label -> (dict key, type)
    FIELD_MAP = {
        r"Return \[%\]":           ("return_pct",          float),
        r"Buy & Hold Return \[%\]":("buy_hold_return_pct", float),
        r"Sharpe Ratio":           ("sharpe",              float),
        r"Sortino Ratio":          ("sortino",             float),
        r"Max\. Drawdown \[%\]":   ("max_drawdown_pct",    float),
        r"# Trades":               ("trades",              int),
        r"Win Rate \[%\]":         ("win_rate_pct",        float),
        r"Profit Factor":          ("profit_factor",       float),
        r"Avg\. Trade \[%\]":      ("avg_trade_pct",       float),
        r"Exposure Time \[%\]":    ("exposure_pct",        float),
        r"Equity Final \[\$\]":    ("equity_final",        float),
        r"Equity Peak \[\$\]":     ("equity_peak",         float),
        r"Return \(Ann\.\) \[%\]": ("annual_return_pct",   float),
        r"Volatility \(Ann\.\) \[%\]": ("annual_vol_pct",  float),
        r"Calmar Ratio":           ("calmar",              float),
        r"SQN":                    ("sqn",                 float),
        r"Expectancy \[%\]":       ("expectancy_pct",      float),
    }

    stats = {}
    for pattern, (key, dtype) in FIELD_MAP.items():
        match = re.search(rf"{pattern}\s+([-\d.eE+nan]+)", stdout)
        if match:
            raw = match.group(1).strip()
            if raw.lower() == "nan":
                stats[key] = None
            else:
                try:
                    stats[key] = dtype(float(raw))
                except (ValueError, TypeError):
                    stats[key] = None

    return stats


def has_nan_results(stats: dict) -> bool:
    """Check if backtest produced NaN/zero results (no trades taken)."""
    trades = stats.get("trades", 0) or 0
    win_rate = stats.get("win_rate_pct")
    exposure = stats.get("exposure_pct", 0) or 0
    return_pct = stats.get("return_pct", 0) or 0

    nan_count = 0
    if trades == 0:
        nan_count += 1
    if win_rate is None:
        nan_count += 1
    if exposure == 0:
        nan_count += 1
    if return_pct == 0:
        nan_count += 1

    return nan_count >= 2


# ============================================================================
# SCORING
# ============================================================================

def score_strategy(stats: dict) -> float:
    """Compute a composite score (0–100) for a strategy.

    Rejects strategies below minimum thresholds (returns 0.0).

    Weights:
        Sharpe   40%  — capped contribution at Sharpe=3.0
        Return   30%  — logistic scaling, 100% return = ~75% of max
        Drawdown 20%  — penalty, lower drawdown = higher score
        Win Rate 10%  — linear 0–100%
    """
    trades = stats.get("trades", 0) or 0
    sharpe = stats.get("sharpe") or 0.0
    return_pct = stats.get("return_pct") or 0.0
    max_dd = abs(stats.get("max_drawdown_pct") or 0.0)
    win_rate = stats.get("win_rate_pct") or 0.0

    # Hard reject
    if trades < MIN_TRADES:
        return 0.0
    if sharpe < MIN_SHARPE:
        return 0.0

    # Sharpe component (0–100, cap at 3.0)
    sharpe_score = min(sharpe / 3.0, 1.0) * 100

    # Return component (logistic: 100% return → ~75, 200% → ~88, 500% → ~97)
    import math
    return_score = 100 * (1 - math.exp(-return_pct / 200)) if return_pct > 0 else 0

    # Drawdown component (lower is better; 0% dd → 100, 50% dd → 0)
    drawdown_score = max(0, 100 - max_dd * 2)

    # Win rate component (linear)
    win_score = min(win_rate, 100)

    composite = (
        WEIGHT_SHARPE * sharpe_score
        + WEIGHT_RETURN * return_score
        + WEIGHT_DRAWDOWN * drawdown_score
        + WEIGHT_WIN_RATE * win_score
    )

    return round(composite, 2)


# ============================================================================
# LEADERBOARD
# ============================================================================

def load_leaderboard() -> list:
    """Load the leaderboard CSV as a list of dicts, sorted by composite_score desc."""
    if not os.path.isfile(LEADERBOARD_FILE):
        return []

    rows = []
    with open(LEADERBOARD_FILE, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert numeric fields
            for key in row:
                if key not in ("timestamp", "strategy_name", "source_file"):
                    try:
                        row[key] = float(row[key]) if row[key] else None
                    except (ValueError, TypeError):
                        row[key] = None
            rows.append(row)

    rows.sort(key=lambda r: r.get("composite_score") or 0, reverse=True)
    return rows


def update_leaderboard(strategy_name: str, stats: dict, source_file: str) -> float:
    """Score a strategy and append it to the leaderboard.

    Returns:
        float: the composite score
    """
    os.makedirs(os.path.dirname(LEADERBOARD_FILE), exist_ok=True)

    composite = score_strategy(stats)

    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "strategy_name": strategy_name,
        "source_file": source_file,
        "composite_score": composite,
    }
    # Add all stat fields
    for col in LEADERBOARD_COLUMNS:
        if col not in row:
            row[col] = stats.get(col)

    file_exists = os.path.isfile(LEADERBOARD_FILE)
    with open(LEADERBOARD_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LEADERBOARD_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    cprint(f"  Leaderboard updated: {strategy_name} — score {composite:.1f}", "green")
    return composite


def get_top_strategies(n: int = 5) -> list:
    """Return the top N strategies by composite score."""
    lb = load_leaderboard()
    return lb[:n]


def print_leaderboard(n: int = 10):
    """Print a formatted leaderboard table."""
    top = get_top_strategies(n)
    if not top:
        cprint("  Leaderboard is empty.", "yellow")
        return

    cprint("\n" + "=" * 80, "cyan")
    cprint("  STRATEGY LEADERBOARD", "cyan", attrs=["bold"])
    cprint("=" * 80, "cyan")
    cprint(f"  {'#':<4} {'Strategy':<25} {'Score':>7} {'Return%':>9} {'Sharpe':>7} {'Trades':>7} {'MaxDD%':>7} {'WinR%':>7}", "white")
    cprint("-" * 80, "cyan")

    for i, row in enumerate(top, 1):
        score = row.get("composite_score") or 0
        ret = row.get("return_pct") or 0
        sharpe = row.get("sharpe") or 0
        trades = int(row.get("trades") or 0)
        dd = row.get("max_drawdown_pct") or 0
        wr = row.get("win_rate_pct") or 0

        color = "green" if score >= 50 else "yellow" if score >= 25 else "red"
        cprint(
            f"  {i:<4} {row.get('strategy_name', '?'):<25} {score:>7.1f} {ret:>8.1f}% {sharpe:>7.2f} {trades:>7} {dd:>6.1f}% {wr:>6.1f}%",
            color,
        )

    cprint("=" * 80, "cyan")


# ============================================================================
# STANDALONE
# ============================================================================

if __name__ == "__main__":
    cprint("\n  Moon Dev's Strategy Leaderboard\n", "cyan", attrs=["bold"])
    print_leaderboard(20)
