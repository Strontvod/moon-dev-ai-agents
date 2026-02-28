"""
Moon Dev's Strategy Converter
Built with love by Moon Dev

Converts a winning backtesting.py backtest file into a live strategy file
that implements the analyze(df, token) interface expected by strategy_agent.py.

Usage:
    python src/agents/strategy_converter.py path/to/winning_backtest.py StrategyName
"""

import os
import re
import sys
from pathlib import Path
from termcolor import cprint
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))

from src.models.model_factory import model_factory as _global_model_factory

# ============================================================================
# CONFIGURATION
# ============================================================================

OUTPUT_DIR = "src/strategies/custom"

# Which model to use for conversion (cheap + reliable)
CONVERTER_MODEL_TYPE = "claude"
CONVERTER_MODEL_NAME = "claude-3-haiku-20240307"

# ============================================================================
# CONVERSION PROMPT
# ============================================================================

CONVERSION_PROMPT = """You are Moon Dev's Strategy Converter AI.

Convert a backtesting.py strategy into a LIVE strategy class that implements
the analyze(df, token) interface. The output must be a standalone Python file.

REFERENCE IMPLEMENTATION (this is exactly what the output should look like):
```python
import pandas as pd
import numpy as np
from termcolor import cprint

# Parameters
PARAM_1 = 20
PARAM_2 = 50

class {class_name}:
    def __init__(self):
        self.name = "{class_name}"
        cprint(f"  {{self.name}} loaded", "cyan")

    def analyze(self, df: pd.DataFrame, token: str = "BTC") -> dict:
        \"\"\"Analyze OHLCV data and return a trading signal.

        Args:
            df: DataFrame with columns [open, high, low, close, volume], datetime index.
            token: Symbol string (e.g., "BTC", "ETH").

        Returns:
            dict with keys: token, signal (0.0-1.0), direction ("BUY"/"SELL"/"NEUTRAL"), metadata
        \"\"\"
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]

        if len(df) < 50:  # need enough bars for indicators
            return self._neutral(token)

        # Compute indicators using pure pandas/numpy (NO backtesting.py, NO self.I())
        # ... indicator calculations here ...

        # Generate signal
        # ... signal logic here ...

        return {{
            "token": token,
            "signal": confidence,      # float 0.0 to 1.0
            "direction": direction,    # "BUY", "SELL", or "NEUTRAL"
            "metadata": {{}}            # optional indicator values
        }}

    def _neutral(self, token):
        return {{"token": token, "signal": 0.0, "direction": "NEUTRAL", "metadata": {{}}}}
```

RULES:
1. Extract ALL indicator logic from the backtesting.py Strategy class
2. Convert self.I(talib.XXX, ...) calls to equivalent pandas/numpy/talib direct calls
3. Convert self.buy() conditions to direction="BUY", self.sell() to direction="SELL"
4. Remove ALL backtesting.py imports and references
5. Remove ALL self.data references — use the df parameter instead
6. Use df['close'], df['high'], df['low'], df['open'], df['volume']
7. Import talib at the top if the strategy uses talib indicators
8. The class MUST have __init__(self) setting self.name, and analyze(self, df, token) method
9. Signal confidence should be 0.0-1.0 based on how many conditions are met
10. Include a _neutral(self, token) helper method

ONLY SEND BACK THE COMPLETE PYTHON FILE, NO OTHER TEXT.
"""


# ============================================================================
# CONVERTER
# ============================================================================

def convert_backtest_to_strategy(backtest_file: str, strategy_name: str) -> str:
    """Convert a backtesting.py file to a live strategy file.

    Args:
        backtest_file: Path to the winning backtest .py file
        strategy_name: CamelCase name (e.g., "AdaptiveBreakout")

    Returns:
        str: Path to the generated strategy file, or None on failure
    """
    cprint(f"\n  Converting backtest to live strategy: {strategy_name}", "cyan")

    # Read the backtest code
    with open(backtest_file, "r", encoding="utf-8") as f:
        backtest_code = f.read()

    # Build class name
    class_name = re.sub(r'[^a-zA-Z0-9]', '', strategy_name) + "Strategy"

    # Format the prompt
    prompt = CONVERSION_PROMPT.format(class_name=class_name)

    # Get model
    model = _global_model_factory.get_model(CONVERTER_MODEL_TYPE, CONVERTER_MODEL_NAME)
    if not model:
        # Fallback chain
        for fallback in ["claude", "openai", "deepseek", "groq"]:
            model = _global_model_factory.get_model(fallback)
            if model:
                break

    if not model:
        cprint("  No LLM available for conversion!", "red")
        return None

    # Generate the live strategy
    response = model.generate_response(
        system_prompt=prompt,
        user_content=f"Convert this backtesting.py strategy to a live strategy class named {class_name}:\n\n{backtest_code}",
        temperature=0.3,  # low temperature for code generation
        max_tokens=4096,
    )

    if response is None:
        cprint("  LLM returned None!", "red")
        return None

    # Extract text
    if hasattr(response, 'content'):
        code = response.content
    else:
        code = str(response)

    # Clean markdown fences if present
    code = _clean_code_output(code)

    if not code or len(code.strip()) < 50:
        cprint("  Generated code too short, conversion likely failed", "red")
        return None

    # Validate it has the required interface
    if "def analyze(self" not in code:
        cprint("  Generated code missing analyze() method!", "red")
        return None

    # Write to strategies/custom/
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    snake_name = _to_snake_case(strategy_name)
    output_file = os.path.join(OUTPUT_DIR, f"{snake_name}_strategy.py")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(code)

    cprint(f"  Live strategy saved: {output_file}", "green")

    # Verify syntax
    try:
        import ast
        ast.parse(code)
        cprint(f"  Syntax verified OK", "green")
    except SyntaxError as e:
        cprint(f"  WARNING: generated code has syntax error: {e}", "yellow")
        cprint(f"  File saved but may need manual fix: {output_file}", "yellow")

    return output_file


def _clean_code_output(text: str) -> str:
    """Strip markdown code fences and thinking tags from LLM output."""
    import re as _re

    # Remove <think>...</think> blocks
    text = _re.sub(r'<think>.*?</think>', '', text, flags=_re.DOTALL).strip()

    # Extract from ```python ... ``` blocks
    blocks = _re.findall(r'```python[^\n]*\n(.*?)```', text, _re.DOTALL)
    if blocks:
        return "\n\n".join(b.strip() for b in blocks)

    # Try any fenced block
    blocks = _re.findall(r'```[^\n]*\n(.*?)```', text, _re.DOTALL)
    if blocks:
        return "\n\n".join(b.strip() for b in blocks)

    return text


def _to_snake_case(name: str) -> str:
    """Convert CamelCase to snake_case."""
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    s = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', s)
    return s.lower().replace(' ', '_').replace('-', '_')


# ============================================================================
# STANDALONE
# ============================================================================

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python src/agents/strategy_converter.py <backtest_file> <StrategyName>")
        print("Example: python src/agents/strategy_converter.py src/data/rbi/02_28_2026/backtests_final/AdaptiveBreakout_BTFinal.py AdaptiveBreakout")
        sys.exit(1)

    bt_file = sys.argv[1]
    name = sys.argv[2]

    if not os.path.isfile(bt_file):
        print(f"File not found: {bt_file}")
        sys.exit(1)

    result = convert_backtest_to_strategy(bt_file, name)
    if result:
        cprint(f"\n  Conversion complete: {result}", "green")
    else:
        cprint(f"\n  Conversion failed!", "red")
        sys.exit(1)
