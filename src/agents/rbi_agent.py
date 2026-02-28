"""
🌙 Moon Dev's RBI AI (Research-Backtest-Implement)
Built with love by Moon Dev 🚀

Required Setup:
1. Create folder structure:
   src/
   ├── data/
   │   └── rbi/
   │       ├── MM_DD_YYYY/         # Date-based folder (created automatically)
   │       │   ├── research/       # Strategy research outputs
   │       │   ├── backtests/      # Initial backtest code
   │       │   ├── backtests_package/ # Package-fixed code
   │       │   ├── backtests_final/ # Debugged backtest code
   │       │   └── charts/         # Charts output directory
   │       └── ideas.txt          # Trading ideas to process

2. Environment Variables:
   - No API keys needed! We're using local Ollama models 🎉

3. Create ideas.txt:
   - One trading idea per line
   - Can be YouTube URLs, PDF links, or text descriptions
   - Lines starting with # are ignored

This AI automates the RBI process:
1. Research: Analyzes trading strategies from various sources
2. Backtest: Creates backtests for promising strategies
3. Debug: Fixes technical issues in generated backtests

✨ NEW FEATURE: All outputs are now organized in date-based folders (MM_DD_YYYY)
This helps keep your strategy research organized by day!

Remember: Past performance doesn't guarantee future results!
"""


# ============================================================================
# MODEL CONFIGS — swap these to change which LLM handles each phase
# ============================================================================

RESEARCH_CONFIG = {"type": "gemini", "name": "gemini-2.5-flash"}
BACKTEST_CONFIG = {"type": "gemini", "name": "gemini-2.5-flash"}
DEBUG_CONFIG    = {"type": "gemini", "name": "gemini-2.5-flash"}
PACKAGE_CONFIG  = {"type": "gemini", "name": "gemini-2.5-flash"}
OPTIMIZE_CONFIG = {"type": "gemini", "name": "gemini-2.5-flash"}

# ============================================================================
# EXECUTION & OPTIMIZATION SETTINGS
# ============================================================================

TARGET_RETURN = 50              # % return the optimizer chases
MAX_DEBUG_ITERATIONS = 10       # max debug retries before giving up
MAX_OPTIMIZATION_ITERATIONS = 10  # max optimize loops after a working run
EXECUTION_TIMEOUT = 300         # seconds per backtest subprocess

# AI Prompts

RESEARCH_PROMPT = """
You are Moon Dev's Research AI 🌙

IMPORTANT NAMING RULES:
1. Create a UNIQUE TWO-WORD NAME for this specific strategy
2. The name must be DIFFERENT from any generic names like "TrendFollower" or "MomentumStrategy"
3. First word should describe the main approach (e.g., Adaptive, Neural, Quantum, Fractal, Dynamic)
4. Second word should describe the specific technique (e.g., Reversal, Breakout, Oscillator, Divergence)
5. Make the name SPECIFIC to this strategy's unique aspects

Examples of good names:
- "AdaptiveBreakout" for a strategy that adjusts breakout levels
- "FractalMomentum" for a strategy using fractal analysis with momentum
- "QuantumReversal" for a complex mean reversion strategy
- "NeuralDivergence" for a strategy focusing on divergence patterns

BAD names to avoid:
- "TrendFollower" (too generic)
- "SimpleMoving" (too basic)
- "PriceAction" (too vague)

Output format must start with:
STRATEGY_NAME: [Your unique two-word name]

Then analyze the trading strategy content and create detailed instructions.
Focus on:
1. Key strategy components
2. Entry/exit rules
3. Risk management
4. Required indicators

Your complete output must follow this format:
STRATEGY_NAME: [Your unique two-word name]

STRATEGY_DETAILS:
[Your detailed analysis]

Remember: The name must be UNIQUE and SPECIFIC to this strategy's approach!
"""

BACKTEST_PROMPT = """
You are Moon Dev's Backtest AI 🌙 ONLY SEND BACK CODE, NO OTHER TEXT.
Create an implementation using the backtesting.py library (pip package name: backtesting).
IMPORTANT: Use "from backtesting import Backtest, Strategy" — DO NOT use backtrader.
DO NOT import backtrader. The library is backtesting.py, NOT backtrader.
Include:
1. All necessary imports
2. Strategy class with indicators
3. Entry/exit logic
4. Risk management
5. your size should be 1,000,000
6. If you need indicators use TA lib or pandas TA.

IMPORTANT DATA HANDLING:
1. Clean column names by removing spaces: data.columns = data.columns.str.strip().str.lower()
2. Drop any unnamed columns: data = data.drop(columns=[col for col in data.columns if 'unnamed' in col.lower()])
3. Ensure proper column mapping to match backtesting requirements:
   - Required columns: 'Open', 'High', 'Low', 'Close', 'Volume'
   - Use proper case (capital first letter)

FOR THE PYTHON BACKTESTING LIBRARY USE BACKTESTING.PY AND SEND BACK ONLY THE CODE, NO OTHER TEXT.

INDICATOR CALCULATION RULES:
1. ALWAYS use self.I() wrapper for ANY indicator calculations
2. Use talib functions instead of pandas operations:
   - Instead of: self.data.Close.rolling(20).mean()
   - Use: self.I(talib.SMA, self.data.Close, timeperiod=20)
3. For swing high/lows use talib.MAX/MIN:
   - Instead of: self.data.High.rolling(window=20).max()
   - Use: self.I(talib.MAX, self.data.High, timeperiod=20)

BACKTEST EXECUTION ORDER:
1. Run initial backtest with default parameters first
2. Print full stats using print(stats) and print(stats._strategy)
3. no optimization code needed, just print the final stats, make sure full stats are printed, not just part or some. stats = bt.run() print(stats) is an example of the last line of code. no need for plotting ever.

do not creeate charts to plot this, just print stats. no charts needed.

CRITICAL POSITION SIZING RULE:
When calculating position sizes in backtesting.py, the size parameter must be either:
1. A fraction between 0 and 1 (for percentage of equity)
2. A whole number (integer) of units

The common error occurs when calculating position_size = risk_amount / risk, which results in floating-point numbers. Always use:
position_size = int(round(position_size))

Example fix:
❌ self.buy(size=3546.0993)  # Will fail
✅ self.buy(size=int(round(3546.0993)))  # Will work

RISK MANAGEMENT:
1. Always calculate position sizes based on risk percentage
2. Use proper stop loss and take profit calculations
4. Print entry/exit signals with Moon Dev themed messages

If you need indicators use TA lib or pandas TA. 

Use this data path: {DATA_PATH}
the above data head looks like below
datetime, open, high, low, close, volume,
2023-01-01 00:00:00, 16531.83, 16532.69, 16509.11, 16510.82, 231.05338022,
2023-01-01 00:15:00, 16509.78, 16534.66, 16509.11, 16533.43, 308.12276951,

Add Moon Dev themed debug prints. Keep emojis OUTSIDE of f-string curly braces.
Example: f"🌙 Moon Dev: Price = {{current_price:.2f}}" — emojis go outside the braces.

FOR THE PYTHON BACKTESTING LIBRARY USE BACKTESTING.PY AND SEND BACK ONLY THE CODE, NO OTHER TEXT.
ONLY SEND BACK CODE, NO OTHER TEXT.
"""

DEBUG_PROMPT = """
You are Moon Dev's Debug AI 🌙
Fix technical issues in the backtest code WITHOUT changing the strategy logic.

CRITICAL BACKTESTING REQUIREMENTS:
1. Position Sizing Rules:
   - Must be either a fraction (0 < size < 1) for percentage of equity
   - OR a positive whole number (round integer) for units
   - Example: size=0.5 (50% of equity) or size=100 (100 units)
   - NEVER use floating point numbers for unit-based sizing

2. Common Fixes Needed:
   - Round position sizes to whole numbers if using units
   - Convert to fraction if using percentage of equity
   - Ensure stop loss and take profit are price levels, not distances

Focus on:
1. Syntax errors (like incorrect string formatting)
2. Import statements and dependencies
3. Class and function definitions
4. Variable scoping and naming
5. Print statement formatting

DO NOT change:
1. Strategy logic
2. Entry/exit conditions
3. Risk management rules
4. Parameter values (unless fixing technical issues)

Return the complete fixed code with Moon Dev themed debug prints! 🌙 ✨
ONLY SEND BACK CODE, NO OTHER TEXT.
"""

PACKAGE_PROMPT = """
You are Moon Dev's Package AI 🌙
Your job is to ensure the backtest code NEVER uses ANY backtesting.lib imports or functions.

❌ STRICTLY FORBIDDEN:
1. from backtesting.lib import *
2. import backtesting.lib
3. from backtesting.lib import crossover
4. ANY use of backtesting.lib

✅ REQUIRED REPLACEMENTS:
1. For crossover detection:
   Instead of: backtesting.lib.crossover(a, b)
   Use: (a[-2] < b[-2] and a[-1] > b[-1])  # for bullish crossover
        (a[-2] > b[-2] and a[-1] < b[-1])  # for bearish crossover

2. For indicators:
   - Use talib for all standard indicators (SMA, RSI, MACD, etc.)
   - Use pandas-ta for specialized indicators
   - ALWAYS wrap in self.I()

3. For signal generation:
   - Use numpy/pandas boolean conditions
   - Use rolling window comparisons with array indexing
   - Use mathematical comparisons (>, <, ==)

Example conversions:
❌ from backtesting.lib import crossover
❌ if crossover(fast_ma, slow_ma):
✅ if fast_ma[-2] < slow_ma[-2] and fast_ma[-1] > slow_ma[-1]:

❌ self.sma = self.I(backtesting.lib.SMA, self.data.Close, 20)
✅ self.sma = self.I(talib.SMA, self.data.Close, timeperiod=20)

IMPORTANT: Scan the ENTIRE code for any backtesting.lib usage and replace ALL instances!
Return the complete fixed code with proper Moon Dev themed debug prints! 🌙 ✨
ONLY SEND BACK CODE, NO OTHER TEXT.
"""

OPTIMIZE_PROMPT = """
You are Moon Dev's Optimization AI 🌙
The strategy below runs but has not hit the target return.

CURRENT PERFORMANCE:
Return [%]: {current_return}%
TARGET RETURN: {target_return}%

Improve the strategy to get closer to the target return. Try these techniques:
1. Entry optimization: tighten or loosen entry conditions
2. Exit optimization: better take-profit / stop-loss levels
3. Risk management: adjust position sizing
4. Indicator tuning: change periods, thresholds
5. Market regime filter: add trend/volatility filter to avoid bad trades

RULES:
- Use "from backtesting import Backtest, Strategy" — DO NOT use backtrader
- Keep using backtesting.py and talib/pandas_ta
- Keep self.I() wrappers for all indicators
- Keep int position sizes
- Keep print(stats) as the last line
- DO NOT add charts or plotting

ONLY SEND BACK CODE, NO OTHER TEXT.
"""

DEBUG_PROMPT_WITH_ERROR = """
You are Moon Dev's Debug AI 🌙
Fix the backtest code based on this error:

ERROR:
{error_message}

CRITICAL RULES:
1. Use "from backtesting import Backtest, Strategy" — DO NOT use backtrader. Never import backtrader.
2. Data must be loaded BEFORE the Strategy class definition
3. Position sizes must be int (use int(round(...)))
4. Use self.I() for ALL indicator calculations
5. Do NOT use .shift() on indicator arrays — use array indexing [-1], [-2]
6. The backtesting.py position object has NO .entry_price attribute.
   Use self.trades[-1].entry_price if you need entry price.
7. Stop loss / take profit must be absolute price levels, not distances.
8. Keep print(stats) as the last line.
9. Do NOT use emojis inside f-string braces. Keep emojis outside the curly braces.
   WRONG: f"{{🌙}} price is {{price}}"
   RIGHT: f"🌙 price is {{price}}"
10. Avoid non-ASCII characters in f-string expressions entirely.

ONLY SEND BACK CODE, NO OTHER TEXT.
"""

NO_TRADES_DEBUG_PROMPT = """
You are Moon Dev's Debug AI 🌙
The backtest code ran without errors but produced ZERO trades.

PROBLEM:
The entry conditions are too restrictive for the dataset. The strategy never triggered a buy or sell.

YOUR TASK — make the strategy actually trade by loosening entry conditions:
1. If RSI thresholds are used, widen them (e.g., oversold 30→40, overbought 70→60)
2. If SMA period is very long (e.g., 200), shorten it (e.g., 50 or 100)
3. If multiple conditions must ALL be true (AND logic), consider removing the weakest filter
4. If ATR multipliers are used for stops, keep them but don't let them prevent entry
5. Add a debug print at the top of next() showing current indicator values so we can see what's happening
6. Make sure the strategy will realistically trigger on 15-minute BTC candle data spanning ~2 years

CRITICAL RULES:
- Use "from backtesting import Backtest, Strategy" — DO NOT use backtrader
- Position sizes must be int (use int(round(...)))
- Use self.I() for ALL indicator calculations
- Keep print(stats) as the last line
- Do NOT use emojis inside f-string braces
- The goal is to get trades happening, then we can optimize later

ONLY SEND BACK CODE, NO OTHER TEXT.
"""

def get_model_id(model):
    """Get DR/DC identifier based on model"""
    return "DR" if model == "deepseek-reasoner" else "DC"

import os
import time
import re
from datetime import datetime
import requests
from io import BytesIO

# Windows-compatible path to BTC backtest data
DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'rbi', 'BTC-USD-15m.csv'
).replace('\\', '/')
import openai
from termcolor import cprint
try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None
    cprint("⚠️ Anthropic SDK not installed. Claude models will be unavailable. (Moon Dev note)", "yellow")
from pathlib import Path
import threading
import itertools
import sys
import hashlib
import subprocess
import json
from src.config import *  # Import config settings including AI_MODEL
from src.models import model_factory
from src.agents.strategy_scorer import parse_backtest_stats, has_nan_results, score_strategy, update_leaderboard

# Override config's tiny 300-token limit — RBI needs full code generation
# claude-sonnet-4-5 supports 8192 output tokens
AI_MAX_TOKENS = 8192

# DeepSeek Configuration
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# Get today's date for organizing outputs
TODAY_DATE = datetime.now().strftime("%m_%d_%Y")

# Update data directory paths
PROJECT_ROOT = Path(__file__).parent.parent  # Points to src/
DATA_DIR = PROJECT_ROOT / "data/rbi"
TODAY_DIR = DATA_DIR / TODAY_DATE  # Today's date folder
RESEARCH_DIR = TODAY_DIR / "research"
BACKTEST_DIR = TODAY_DIR / "backtests"
PACKAGE_DIR = TODAY_DIR / "backtests_package"
FINAL_BACKTEST_DIR = TODAY_DIR / "backtests_final"
OPTIMIZED_DIR = TODAY_DIR / "backtests_optimized"
CHARTS_DIR = TODAY_DIR / "charts"
EXECUTION_DIR = TODAY_DIR / "execution_results"
PROCESSED_IDEAS_LOG = DATA_DIR / "processed_ideas.log"

# Create main directories if they don't exist
for directory in [DATA_DIR, TODAY_DIR, RESEARCH_DIR, BACKTEST_DIR, PACKAGE_DIR,
                  FINAL_BACKTEST_DIR, OPTIMIZED_DIR, CHARTS_DIR, EXECUTION_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

cprint(f"📂 Using RBI data directory: {DATA_DIR}")
cprint(f"📅 Today's date folder: {TODAY_DATE}")
cprint(f"📂 Research directory: {RESEARCH_DIR}")
cprint(f"📂 Backtest directory: {BACKTEST_DIR}")
cprint(f"📂 Package directory: {PACKAGE_DIR}")
cprint(f"📂 Final backtest directory: {FINAL_BACKTEST_DIR}")
cprint(f"📈 Charts directory: {CHARTS_DIR}")

def init_deepseek_client():
    """Initialize DeepSeek client with proper error handling"""
    try:
        deepseek_key = os.getenv("DEEPSEEK_KEY")
        if not deepseek_key:
            cprint("⚠️ DEEPSEEK_KEY not found - DeepSeek models will not be available", "yellow")
            return None
            
        print("🔑 Initializing DeepSeek client...")
        print("🌟 Moon Dev's RBI AI is connecting to DeepSeek...")
        
        client = openai.OpenAI(
            api_key=deepseek_key,
            base_url=DEEPSEEK_BASE_URL
        )
        
        print("✅ DeepSeek client initialized successfully!")
        print("🚀 Moon Dev's RBI AI ready to roll!")
        return client
    except Exception as e:
        print(f"❌ Error initializing DeepSeek client: {str(e)}")
        print("💡 Will fall back to Claude model from config.py")
        return None

def init_anthropic_client():
    """Initialize Anthropic client for Claude models"""
    try:
        if Anthropic is None:
            cprint("⚠️ Anthropic client unavailable (package not installed)", "yellow")
            return None
        anthropic_key = os.getenv("ANTHROPIC_KEY")
        if not anthropic_key:
            cprint("⚠️ ANTHROPIC_KEY not found in env. Skipping Claude init.", "yellow")
            return None
        return Anthropic(api_key=anthropic_key)
    except Exception as e:
        print(f"❌ Error initializing Anthropic client: {str(e)}")
        return None

def chat_with_model(system_prompt, user_content, model_config):
    """Chat with AI model using model factory (or direct Anthropic client for Sonnet key)"""
    try:
        model_name = model_config["name"]
        model_type = model_config["type"]

        # Use dedicated Sonnet API key for sonnet/opus models that need it
        sonnet_key = os.getenv("ANTHROPIC_KEY_SONNET")
        if model_type == "claude" and "sonnet" in model_name and sonnet_key and Anthropic:
            cprint(f"🤖 Using direct Anthropic client: {model_name} (ANTHROPIC_KEY_SONNET)", "cyan")
            cprint("🌟 Moon Dev's RBI AI is thinking...", "yellow")
            cprint(f"📝 System prompt length: {len(system_prompt)} chars", "cyan")
            cprint(f"📝 User content length: {len(user_content)} chars", "cyan")
            client = Anthropic(api_key=sonnet_key)
            response = client.messages.create(
                model=model_name,
                max_tokens=AI_MAX_TOKENS,
                temperature=AI_TEMPERATURE,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}]
            )
            return response.content[0].text.strip()

        # Initialize model using factory with specific config
        model = model_factory.get_model(model_type, model_name)
        if not model:
            raise ValueError(f"🚨 Could not initialize {model_type} {model_name} model!")

        cprint(f"🤖 Using {model_type} model: {model_name}", "cyan")
        cprint("🌟 Moon Dev's RBI AI is thinking...", "yellow")

        # Debug prints for prompt lengths
        cprint(f"📝 System prompt length: {len(system_prompt)} chars", "cyan")
        cprint(f"📝 User content length: {len(user_content)} chars", "cyan")
        # If model returned a wrapper, normalize early
        if hasattr(model, 'model_name') and model.model_type == 'openai':
            cprint(f"🧪 OpenAI model in use: {model.model_name}", "cyan")

        # For Ollama models, handle response differently
        if model_type == "ollama":
            response = model.generate_response(
                system_prompt=system_prompt,
                user_content=user_content,
                temperature=AI_TEMPERATURE
            )
            # Handle string response from Ollama
            if isinstance(response, str):
                return response
            # Handle object response
            if hasattr(response, 'content'):
                return response.content
            return str(response)
        else:
            # For other models, use standard parameters
            response = model.generate_response(
                system_prompt=system_prompt,
                user_content=user_content,
                temperature=AI_TEMPERATURE,
                max_tokens=AI_MAX_TOKENS
            )
            if response is None:
                cprint("❌ Model returned None response", "red")
                return None

            # Coerce response into text content
            content = None
            try:
                from src.models.base_model import ModelResponse
                if isinstance(response, ModelResponse):
                    content = response.content
            except Exception:
                pass

            if content is None:
                if isinstance(response, str):
                    content = response
                elif hasattr(response, 'content'):
                    content = response.content
                else:
                    cprint(f"❌ Response missing content attribute. Response type: {type(response)}", "red")
                    try:
                        cprint(f"Response attributes: {dir(response)}", "yellow")
                    except Exception:
                        pass
                    return None

            if not isinstance(content, str):
                content = str(content) if content is not None else ""
            if not content or len(content.strip()) == 0:
                cprint("❌ Model returned empty content", "red")
                return None

            return content

    except Exception as e:
        cprint(f"❌ Error in AI chat: {str(e)}", "red")
        cprint(f"🔍 Error type: {type(e).__name__}", "yellow")
        if hasattr(e, 'response'):
            cprint(f"🔍 Response error: {getattr(e, 'response', 'No response details')}", "yellow")
        if hasattr(e, '__dict__'):
            cprint("🔍 Error attributes:", "yellow")
            for attr in dir(e):
                if not attr.startswith('_'):
                    cprint(f"  ├─ {attr}: {getattr(e, attr)}", "yellow")
        return None

def get_youtube_transcript(video_id):
    """Get transcript from YouTube video"""
    try:
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
        except ImportError:
            cprint("⚠️ youtube-transcript-api not installed. Skipping YouTube transcript fetch.", "yellow")
            return None
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_generated_transcript(['en'])
        
        # Get the full transcript text
        transcript_text = ' '.join([t['text'] for t in transcript.fetch()])
        
        # Print the transcript with nice formatting
        cprint("\n📝 YouTube Transcript:", "cyan")
        cprint("=" * 80, "yellow")
        print(transcript_text)
        cprint("=" * 80, "yellow")
        cprint(f"📊 Transcript length: {len(transcript_text)} characters", "cyan")
        
        return transcript_text
    except Exception as e:
        cprint(f"❌ Error fetching transcript: {e}", "red")
        return None

def get_pdf_text(url):
    """Extract text from PDF URL"""
    try:
        try:
            import PyPDF2
        except ImportError:
            cprint("⚠️ PyPDF2 not installed. Skipping PDF extraction.", "yellow")
            return None
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        reader = PyPDF2.PdfReader(BytesIO(response.content))
        text = ''
        for page in reader.pages:
            text += page.extract_text() + '\n'
        cprint("📚 Successfully extracted PDF text!", "green")
        return text
    except Exception as e:
        cprint(f"❌ Error reading PDF: {e}", "red")
        return None

def animate_progress(agent_name, stop_event):
    """Fun animation while AI is thinking"""
    spinners = ['🌑', '🌒', '🌓', '🌔', '🌕', '🌖', '🌗', '🌘']
    messages = [
        "brewing coffee ☕️",
        "studying charts 📊",
        "checking signals 📡",
        "doing math 🔢",
        "reading docs 📚",
        "analyzing data 🔍",
        "making magic ✨",
        "trading secrets 🤫",
        "Moon Dev approved 🌙",
        "to the moon! 🚀"
    ]
    
    spinner = itertools.cycle(spinners)
    message = itertools.cycle(messages)
    
    while not stop_event.is_set():
        sys.stdout.write(f'\r{next(spinner)} {agent_name} is {next(message)}...')
        sys.stdout.flush()
        time.sleep(0.5)
    sys.stdout.write('\r' + ' ' * 50 + '\r')
    sys.stdout.flush()

def run_with_animation(func, agent_name, *args, **kwargs):
    """Run a function with a fun loading animation"""
    stop_animation = threading.Event()
    animation_thread = threading.Thread(target=animate_progress, args=(agent_name, stop_animation))
    
    try:
        animation_thread.start()
        result = func(*args, **kwargs)
        return result
    finally:
        stop_animation.set()
        animation_thread.join()

def clean_model_output(output, content_type="text"):
    """Clean model output by removing thinking tags and extracting code from markdown
    
    Args:
        output (str): Raw model output
        content_type (str): Type of content to extract ('text', 'code')
        
    Returns:
        str: Cleaned output
    """
    cleaned_output = output
    
    # Step 1: Remove thinking tags if present
    if "<think>" in output and "</think>" in output:
        cprint(f"🧠 Detected DeepSeek-R1 thinking tags, cleaning...", "yellow")
        
        # First try: Get everything after the last </think> tag
        clean_content = output.split("</think>")[-1].strip()
        
        # If that doesn't work, try removing all <think>...</think> blocks
        if not clean_content:
            import re
            clean_content = re.sub(r'<think>.*?</think>', '', output, flags=re.DOTALL).strip()
            
        if clean_content:
            cleaned_output = clean_content
            cprint("✅ Successfully removed thinking tags", "green")
    
    # Step 2: If code content, extract from markdown code blocks
    if content_type == "code" and "```" in cleaned_output:
        cprint("🔍 Extracting code from markdown blocks...", "yellow")
        
        try:
            import re
            # Normalize line endings first
            normalized = cleaned_output.replace('\r\n', '\n').replace('\r', '\n')

            # Try python-tagged blocks (flexible whitespace after tag)
            code_blocks = re.findall(r'```python[^\n]*\n(.*?)```', normalized, re.DOTALL)

            # If no python blocks, try any fenced code blocks
            if not code_blocks:
                code_blocks = re.findall(r'```[^\n]*\n(.*?)```', normalized, re.DOTALL)

            # Last resort: if entire output starts with ``` strip the fences
            if not code_blocks and normalized.startswith('```'):
                stripped = re.sub(r'^```[^\n]*\n', '', normalized)
                stripped = re.sub(r'\n?```\s*$', '', stripped)
                if stripped.strip():
                    code_blocks = [stripped]

            if code_blocks:
                cleaned_output = "\n\n".join(b.strip() for b in code_blocks)
                cprint("✅ Successfully extracted code from markdown", "green")
            else:
                cprint("⚠️ No code blocks found in markdown", "yellow")
        except Exception as e:
            cprint(f"❌ Error extracting code: {str(e)}", "red")
    
    return cleaned_output

def research_strategy(content):
    """Research AI: Analyzes and creates trading strategy"""
    cprint("\n🔍 Starting Research AI...", "cyan")
    cprint("🤖 Time to discover some alpha!", "yellow")
    
    output = run_with_animation(
        chat_with_model,
        "Research AI",
        RESEARCH_PROMPT, 
        content,
        RESEARCH_CONFIG  # Pass research-specific model config
    )
    
    if output:
        # Clean the output to remove thinking tags
        output = clean_model_output(output, "text")
        
        # Guard against non-string responses from model wrappers
        if not isinstance(output, str):
            try:
                from src.models.base_model import ModelResponse
                if isinstance(output, ModelResponse):
                    output = output.content or ""
                else:
                    output = str(output)
            except Exception:
                output = str(output)
        
        # Extract strategy name from output
        strategy_name = "UnknownStrategy"  # Default name
        if "STRATEGY_NAME:" in output:
            try:
                # Split by the STRATEGY_NAME: marker and get the text after it
                name_section = output.split("STRATEGY_NAME:")[1].strip()
                # Take the first line or up to the next section marker
                if "\n\n" in name_section:
                    strategy_name = name_section.split("\n\n")[0].strip()
                else:
                    strategy_name = name_section.split("\n")[0].strip()
                    
                # Clean up strategy name to be file-system friendly
                strategy_name = re.sub(r'[^\w\s-]', '', strategy_name)
                strategy_name = re.sub(r'[\s]+', '', strategy_name)
                
                cprint(f"✅ Successfully extracted strategy name: {strategy_name}", "green")
            except Exception as e:
                cprint(f"⚠️ Error extracting strategy name: {str(e)}", "yellow")
                cprint(f"🔄 Using default name: {strategy_name}", "yellow")
        else:
            cprint("⚠️ No STRATEGY_NAME found in output, using default", "yellow")
            
            # Try to generate a name based on key terms in the output
            import random
            adjectives = ["Adaptive", "Dynamic", "Quantum", "Neural", "Fractal", "Momentum", "Harmonic", "Volatility"]
            nouns = ["Breakout", "Oscillator", "Reversal", "Momentum", "Divergence", "Scalper", "Crossover", "Arbitrage"]
            strategy_name = f"{random.choice(adjectives)}{random.choice(nouns)}"
            cprint(f"🎲 Generated random strategy name: {strategy_name}", "yellow")
        
        # Save research output
        filepath = RESEARCH_DIR / f"{strategy_name}_strategy.txt"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(output)
        cprint(f"📝 Research AI found something spicy! Saved to {filepath} 🌶️", "green")
        cprint(f"🏷️ Generated strategy name: {strategy_name}", "yellow")
        return output, strategy_name
    return None, None

def create_backtest(strategy, strategy_name="UnknownStrategy"):
    """Backtest AI: Creates backtest implementation"""
    cprint("\n📊 Starting Backtest AI...", "cyan")
    cprint("💰 Let's turn that strategy into profits!", "yellow")
    
    output = run_with_animation(
        chat_with_model,
        "Backtest AI",
        BACKTEST_PROMPT.format(DATA_PATH=DATA_PATH),
        f"Create a backtest for this strategy:\n\n{strategy}",
        BACKTEST_CONFIG  # Pass backtest-specific model config
    )
    
    if output:
        # Clean the output and extract code from markdown
        output = clean_model_output(output, "code")
        if not isinstance(output, str):
            try:
                from src.models.base_model import ModelResponse
                if isinstance(output, ModelResponse):
                    output = output.content or ""
                else:
                    output = str(output)
            except Exception:
                output = str(output)
        
        filepath = BACKTEST_DIR / f"{strategy_name}_BT.py"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(output)
        cprint(f"🔥 Backtest AI cooked up some heat! Saved to {filepath} 🚀", "green")
        return output
    return None

def debug_backtest(backtest_code, strategy=None, strategy_name="UnknownStrategy"):
    """Debug AI: Fixes technical issues in backtest code"""
    cprint("\n🔧 Starting Debug AI...", "cyan")
    cprint("🔍 Time to squash some bugs!", "yellow")
    
    context = f"Here's the backtest code to debug:\n\n{backtest_code}"
    if strategy:
        context += f"\n\nOriginal strategy for reference:\n{strategy}"
    
    output = run_with_animation(
        chat_with_model,
        "Debug AI",
        DEBUG_PROMPT,
        context,
        DEBUG_CONFIG  # Pass debug-specific model config
    )
    
    if output:
        # Clean the output and extract code from markdown
        output = clean_model_output(output, "code")
        if not isinstance(output, str):
            try:
                from src.models.base_model import ModelResponse
                if isinstance(output, ModelResponse):
                    output = output.content or ""
                else:
                    output = str(output)
            except Exception:
                output = str(output)
            
        filepath = FINAL_BACKTEST_DIR / f"{strategy_name}_BTFinal.py"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(output)
        cprint(f"🔧 Debug AI fixed the code! Saved to {filepath} ✨", "green")
        return output
    return None

def package_check(backtest_code, strategy_name="UnknownStrategy"):
    """Package AI: Ensures correct indicator packages are used"""
    cprint("\n📦 Starting Package AI...", "cyan")
    cprint("🔍 Checking for proper indicator imports!", "yellow")
    
    output = run_with_animation(
        chat_with_model,
        "Package AI",
        PACKAGE_PROMPT,
        f"Check and fix indicator packages in this code:\n\n{backtest_code}",
        PACKAGE_CONFIG  # Pass package-specific model config
    )
    
    if output:
        # Clean the output and extract code from markdown
        output = clean_model_output(output, "code")
        if not isinstance(output, str):
            try:
                from src.models.base_model import ModelResponse
                if isinstance(output, ModelResponse):
                    output = output.content or ""
                else:
                    output = str(output)
            except Exception:
                output = str(output)
            
        filepath = PACKAGE_DIR / f"{strategy_name}_PKG.py"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(output)
        cprint(f"📦 Package AI optimized the imports! Saved to {filepath} ✨", "green")
        return output
    return None


# ============================================================================
# EXECUTION & OPTIMIZATION (merged from rbi_agent_v3)
# ============================================================================

def execute_backtest(file_path, strategy_name="Unknown"):
    """Run a backtest .py file as a subprocess and capture output."""
    cprint(f"\n⚡ Executing backtest: {file_path}", "cyan")
    start_time = time.time()

    try:
        # Force UTF-8 encoding in subprocess to handle emojis in LLM-generated print statements
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [sys.executable, str(file_path)],
            capture_output=True, text=True,
            timeout=EXECUTION_TIMEOUT,
            cwd=str(PROJECT_ROOT.parent),  # run from repo root
            env=env,
        )
        execution_time = time.time() - start_time

        output = {
            "success": result.returncode == 0,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat(),
        }

        # Save execution result JSON
        ts = datetime.now().strftime("%H%M%S")
        json_file = EXECUTION_DIR / f"{strategy_name}_{ts}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)

        if output["success"]:
            cprint(f"  Backtest ran OK in {execution_time:.1f}s", "green")
        else:
            cprint(f"  Backtest FAILED (exit code {result.returncode})", "red")
            if result.stderr:
                # Show last 5 lines of stderr
                err_lines = result.stderr.strip().split("\n")
                for line in err_lines[-5:]:
                    cprint(f"    {line}", "red")

        return output

    except subprocess.TimeoutExpired:
        cprint(f"  Backtest TIMED OUT after {EXECUTION_TIMEOUT}s", "red")
        return {"success": False, "return_code": -1, "stdout": "", "stderr": "Timeout", "execution_time": EXECUTION_TIMEOUT, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        cprint(f"  Execution error: {e}", "red")
        return {"success": False, "return_code": -1, "stdout": "", "stderr": str(e), "execution_time": 0, "timestamp": datetime.now().isoformat()}


def analyze_no_trades_issue(execution_result):
    """Build a diagnostic message when backtest produces 0 trades."""
    # Include last 30 lines of stdout for context (indicator values, data info)
    stdout_tail = ""
    if execution_result.get("stdout"):
        lines = execution_result["stdout"].strip().split("\n")
        stdout_tail = "\n".join(lines[-30:])
    return (
        "The backtest ran without errors but took ZERO trades. "
        "Entry conditions are too strict for this dataset.\n\n"
        f"STDOUT (last 30 lines):\n{stdout_tail}"
    )


def debug_backtest_with_error(backtest_code, error_message, strategy_name="Unknown", iteration=1):
    """Debug a backtest using the actual error message (v3-style)."""
    cprint(f"\n🔧 Debug AI (iteration {iteration})...", "cyan")

    prompt = DEBUG_PROMPT_WITH_ERROR.format(error_message=error_message)

    output = run_with_animation(
        chat_with_model,
        f"Debug AI v{iteration}",
        prompt,
        f"Fix this backtest code:\n\n{backtest_code}",
        DEBUG_CONFIG,
    )

    if output:
        output = clean_model_output(output, "code")
        if not isinstance(output, str):
            output = str(output) if output else ""
        filepath = FINAL_BACKTEST_DIR / f"{strategy_name}_BTFinal_v{iteration}.py"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(output)
        cprint(f"  Debug v{iteration} saved: {filepath}", "green")
        return output, str(filepath)
    return None, None


def debug_no_trades(backtest_code, diagnostic_msg, strategy_name="Unknown", iteration=1):
    """Debug a backtest that produces 0 trades — uses specialized loosening prompt."""
    cprint(f"\n🔧 No-Trades Debug AI (iteration {iteration})...", "cyan")

    prompt = NO_TRADES_DEBUG_PROMPT

    output = run_with_animation(
        chat_with_model,
        f"No-Trades Debug v{iteration}",
        prompt,
        f"This backtest produced 0 trades. Loosen the conditions.\n\nDIAGNOSTIC:\n{diagnostic_msg}\n\nCODE:\n{backtest_code}",
        DEBUG_CONFIG,
    )

    if output:
        output = clean_model_output(output, "code")
        if not isinstance(output, str):
            output = str(output) if output else ""
        filepath = FINAL_BACKTEST_DIR / f"{strategy_name}_BTFinal_v{iteration}.py"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(output)
        cprint(f"  No-trades debug v{iteration} saved: {filepath}", "green")
        return output, str(filepath)
    return None, None


def optimize_strategy(backtest_code, current_return, target_return, strategy_name="Unknown", iteration=1):
    """Optimize a working backtest to improve returns."""
    cprint(f"\n🎯 Optimization AI (iteration {iteration}, current: {current_return:.1f}%, target: {target_return}%)...", "cyan")

    prompt = OPTIMIZE_PROMPT.format(
        current_return=current_return,
        target_return=target_return,
    )

    output = run_with_animation(
        chat_with_model,
        f"Optimize AI v{iteration}",
        prompt,
        f"Optimize this backtest code:\n\n{backtest_code}",
        OPTIMIZE_CONFIG,
    )

    if output:
        output = clean_model_output(output, "code")
        if not isinstance(output, str):
            output = str(output) if output else ""
        filepath = OPTIMIZED_DIR / f"{strategy_name}_OPT_v{iteration}.py"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(output)
        cprint(f"  Optimized v{iteration} saved: {filepath}", "green")
        return output, str(filepath)
    return None, None


def get_idea_content(idea_url: str) -> str:
    """Extract content from a trading idea URL or text"""
    print("\n📥 Extracting content from idea...")
    
    try:
        if "youtube.com" in idea_url or "youtu.be" in idea_url:
            # Extract video ID from URL
            if "v=" in idea_url:
                video_id = idea_url.split("v=")[1].split("&")[0]
            else:
                video_id = idea_url.split("/")[-1].split("?")[0]
            
            print("🎥 Detected YouTube video, fetching transcript...")
            transcript = get_youtube_transcript(video_id)
            if transcript:
                print("✅ Successfully extracted YouTube transcript!")
                return f"YouTube Strategy Content:\n\n{transcript}"
            else:
                raise ValueError("Failed to extract YouTube transcript")
                
        elif idea_url.endswith(".pdf"):
            print("📚 Detected PDF file, extracting text...")
            pdf_text = get_pdf_text(idea_url)
            if pdf_text:
                print("✅ Successfully extracted PDF content!")
                return f"PDF Strategy Content:\n\n{pdf_text}"
            else:
                raise ValueError("Failed to extract PDF text")
                
        else:
            print("📝 Using raw text input...")
            return f"Text Strategy Content:\n\n{idea_url}"
            
    except Exception as e:
        print(f"❌ Error extracting content: {str(e)}")
        raise

def get_idea_hash(idea: str) -> str:
    """Generate a unique hash for an idea to track processing status"""
    # Create a hash of the idea to use as a unique identifier
    return hashlib.md5(idea.encode('utf-8')).hexdigest()

def is_idea_processed(idea: str) -> bool:
    """Check if an idea has already been processed"""
    if not PROCESSED_IDEAS_LOG.exists():
        return False
        
    idea_hash = get_idea_hash(idea)
    
    with open(PROCESSED_IDEAS_LOG, 'r', encoding='utf-8') as f:
        processed_hashes = [line.strip().split(',')[0] for line in f if line.strip()]
        
    return idea_hash in processed_hashes

def log_processed_idea(idea: str, strategy_name: str = "Unknown") -> None:
    """Log an idea as processed with timestamp and strategy name"""
    idea_hash = get_idea_hash(idea)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create the log file if it doesn't exist
    if not PROCESSED_IDEAS_LOG.exists():
        PROCESSED_IDEAS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(PROCESSED_IDEAS_LOG, 'w', encoding='utf-8') as f:
            f.write("# Moon Dev's RBI AI - Processed Ideas Log 🌙\n")
            f.write("# Format: hash,timestamp,strategy_name,idea_snippet\n")
    
    # Append the processed idea to the log
    with open(PROCESSED_IDEAS_LOG, 'a', encoding='utf-8') as f:
        # Truncate idea if too long for the log
        idea_snippet = idea[:100] + ('...' if len(idea) > 100 else '')
        f.write(f"{idea_hash},{timestamp},{strategy_name},{idea_snippet}\n")
    
    cprint(f"📝 Idea logged as processed: {idea_hash}", "green")

def process_trading_idea(idea: str) -> None:
    """Process a single trading idea: research → backtest → execute → optimize."""
    cprint("\n🚀 Moon Dev's RBI AI Processing New Idea!", "green")
    cprint(f"📝 Processing: {idea[:100]}...", "yellow")
    cprint(f"📅 Output folder: {TODAY_DATE}", "yellow")

    try:
        # Step 1: Extract content
        idea_content = get_idea_content(idea)
        if not idea_content:
            cprint("❌ Failed to extract content!", "red")
            return

        # Phase 1: Research
        cprint("\n🧪 Phase 1: Research", "cyan")
        strategy, strategy_name = research_strategy(idea_content)
        if not strategy:
            cprint("❌ Research phase failed!", "red")
            return
        log_processed_idea(idea, strategy_name)

        # Phase 2: Backtest code generation
        cprint("\n📈 Phase 2: Backtest", "cyan")
        backtest = create_backtest(strategy, strategy_name)
        if not backtest:
            cprint("❌ Backtest phase failed!", "red")
            return

        # Phase 3: Package check
        cprint("\n📦 Phase 3: Package Check", "cyan")
        package_checked = package_check(backtest, strategy_name)
        if not package_checked:
            cprint("❌ Package check failed!", "red")
            return

        # Phase 4: Initial debug pass
        cprint("\n🔧 Phase 4: Debug", "cyan")
        current_code = debug_backtest(package_checked, strategy, strategy_name)
        if not current_code:
            cprint("❌ Debug phase failed!", "red")
            return

        current_file = str(FINAL_BACKTEST_DIR / f"{strategy_name}_BTFinal.py")

        # Phase 5: EXECUTION + DEBUG LOOP
        cprint("\n⚡ Phase 5: Execute & Debug Loop", "cyan")
        last_error = None
        best_return = None
        best_code = current_code
        best_file = current_file

        for debug_iter in range(1, MAX_DEBUG_ITERATIONS + 1):
            result = execute_backtest(current_file, strategy_name)

            if result["success"]:
                stats = parse_backtest_stats(result["stdout"])

                if has_nan_results(stats):
                    # Ran but no trades — use specialized no-trades prompt
                    cprint(f"  Iteration {debug_iter}: 0 trades, loosening conditions...", "yellow")
                    diagnostic = analyze_no_trades_issue(result)
                    new_code, new_file = debug_no_trades(
                        current_code, diagnostic, strategy_name, debug_iter
                    )
                    if new_code:
                        current_code, current_file = new_code, new_file
                    continue

                # We have real results — parse return
                current_return = stats.get("return_pct") or 0.0
                cprint(f"  Iteration {debug_iter}: Return = {current_return:.1f}%", "green")

                if best_return is None or current_return > best_return:
                    best_return = current_return
                    best_code = current_code
                    best_file = current_file

                if current_return >= TARGET_RETURN:
                    cprint(f"  TARGET HIT! {current_return:.1f}% >= {TARGET_RETURN}%", "green", attrs=["bold"])
                    # Save winning file
                    win_file = OPTIMIZED_DIR / f"{strategy_name}_TARGET_HIT_{int(current_return)}pct.py"
                    with open(win_file, "w", encoding="utf-8") as f:
                        f.write(current_code)
                    # Update leaderboard
                    update_leaderboard(strategy_name, stats, str(win_file))
                    break

                # Haven't hit target — enter optimization loop
                cprint(f"\n🎯 Phase 6: Optimization Loop (best so far: {best_return:.1f}%)", "cyan")
                for opt_iter in range(1, MAX_OPTIMIZATION_ITERATIONS + 1):
                    opt_code, opt_file = optimize_strategy(
                        current_code, best_return, TARGET_RETURN, strategy_name, opt_iter
                    )
                    if not opt_code:
                        cprint(f"  Optimization {opt_iter} failed, stopping", "yellow")
                        break

                    opt_result = execute_backtest(opt_file, strategy_name)
                    if opt_result["success"]:
                        opt_stats = parse_backtest_stats(opt_result["stdout"])
                        opt_return = opt_stats.get("return_pct") or 0.0
                        cprint(f"  Opt {opt_iter}: Return = {opt_return:.1f}%", "cyan")

                        if opt_return > best_return:
                            best_return = opt_return
                            best_code = opt_code
                            best_file = opt_file
                            current_code = opt_code
                            current_file = opt_file

                        if opt_return >= TARGET_RETURN:
                            cprint(f"  TARGET HIT via optimization! {opt_return:.1f}%", "green", attrs=["bold"])
                            win_file = OPTIMIZED_DIR / f"{strategy_name}_TARGET_HIT_{int(opt_return)}pct.py"
                            with open(win_file, "w", encoding="utf-8") as f:
                                f.write(opt_code)
                            update_leaderboard(strategy_name, opt_stats, str(win_file))
                            break
                    else:
                        cprint(f"  Opt {opt_iter} execution failed, skipping", "yellow")

                # After optimization loop, save best and update leaderboard
                if best_return is not None and best_return > 0:
                    best_save = OPTIMIZED_DIR / f"{strategy_name}_BEST_{int(best_return)}pct.py"
                    with open(best_save, "w", encoding="utf-8") as f:
                        f.write(best_code)
                    # Re-parse best stats for leaderboard
                    best_result = execute_backtest(str(best_save), strategy_name)
                    if best_result["success"]:
                        best_stats = parse_backtest_stats(best_result["stdout"])
                        update_leaderboard(strategy_name, best_stats, str(best_save))
                break  # exit debug loop — we got a working run

            else:
                # Execution failed — debug with error
                error_msg = result["stderr"][-2000:] if result["stderr"] else "Unknown error"

                # Guard against infinite loop on same error
                if error_msg == last_error:
                    cprint(f"  Same error repeated, stopping debug loop", "red")
                    break
                last_error = error_msg

                cprint(f"  Iteration {debug_iter}: execution failed, re-debugging...", "yellow")
                new_code, new_file = debug_backtest_with_error(
                    current_code, error_msg, strategy_name, debug_iter
                )
                if new_code:
                    current_code, current_file = new_code, new_file
                else:
                    cprint("  Debug AI returned nothing, stopping", "red")
                    break

        cprint(f"\n🎉 RBI pipeline complete for '{strategy_name}'!", "green")
        if best_return is not None:
            cprint(f"  Best return achieved: {best_return:.1f}%", "green")
        cprint(f"  Best file: {best_file}", "green")

    except Exception as e:
        cprint(f"\n❌ Error processing idea: {str(e)}", "red")
        import traceback
        traceback.print_exc()

def main():
    """Main function to process ideas from file"""
    # We keep ideas.txt in the main RBI directory, not in the date folder
    ideas_file = DATA_DIR / "ideas.txt"
    
    if not ideas_file.exists():
        cprint("❌ ideas.txt not found! Creating template...", "red")
        ideas_file.parent.mkdir(parents=True, exist_ok=True)
        with open(ideas_file, 'w', encoding='utf-8') as f:
            f.write("# Add your trading ideas here (one per line)\n")
            f.write("# Can be YouTube URLs, PDF links, or text descriptions\n")
        return
        
    with open(ideas_file, 'r', encoding='utf-8') as f:
        ideas = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
    total_ideas = len(ideas)
    cprint(f"\n🎯 Found {total_ideas} trading ideas to process", "cyan")
    
    # Count how many ideas have already been processed
    already_processed = sum(1 for idea in ideas if is_idea_processed(idea))
    new_ideas = total_ideas - already_processed
    
    cprint(f"🔍 Status: {already_processed} already processed, {new_ideas} new ideas", "cyan")
    
    # Optional: limit number of ideas via env var (for quick debugging)
    max_ideas_env = os.getenv("RBI_MAX_IDEAS")
    max_ideas = int(max_ideas_env) if max_ideas_env and max_ideas_env.isdigit() else None
    processed_count = 0

    for i, idea in enumerate(ideas, 1):
        # Check if this idea has already been processed
        if is_idea_processed(idea):
            cprint(f"\n{'='*50}", "red")
            cprint(f"⏭️  SKIPPING idea {i}/{total_ideas} - ALREADY PROCESSED", "red", attrs=['reverse'])
            idea_snippet = idea[:100] + ('...' if len(idea) > 100 else '')
            cprint(f"📝 Idea: {idea_snippet}", "red")
            cprint(f"{'='*50}\n", "red")
            continue
            
        cprint(f"\n{'='*50}", "yellow")
        cprint(f"🌙 Processing idea {i}/{total_ideas}", "cyan")
        cprint(f"📝 Idea content: {idea[:100]}{'...' if len(idea) > 100 else ''}", "yellow")
        cprint(f"{'='*50}\n", "yellow")
        
        try:
            # Process each idea in complete isolation
            process_trading_idea(idea)
            
            # Clear separator between ideas
            cprint(f"\n{'='*50}", "green")
            cprint(f"✅ Completed idea {i}/{total_ideas}", "green")
            cprint(f"{'='*50}\n", "green")
            
            # Break between ideas
            if i < total_ideas:
                cprint("😴 Taking a break before next idea...", "yellow")
                time.sleep(5)
            processed_count += 1
            if max_ideas and processed_count >= max_ideas:
                cprint("🛑 Reached RBI_MAX_IDEAS limit, exiting after quick debug run.", "yellow")
                break
                
        except Exception as e:
            cprint(f"\n❌ Error processing idea {i}: {str(e)}", "red")
            cprint("🔄 Continuing with next idea...\n", "yellow")
            continue

if __name__ == "__main__":
    try:
        cprint(f"\n🌟 Moon Dev's RBI AI Starting Up!", "green")
        cprint(f"📅 Today's Date: {TODAY_DATE} - All outputs will be saved in this folder", "magenta")
        cprint(f"🧠 DeepSeek-R1 thinking tags will be automatically removed from outputs", "magenta")
        cprint(f"📋 Processed ideas log: {PROCESSED_IDEAS_LOG}", "magenta")
        cprint("\n🤖 Model Configurations:", "cyan")
        cprint(f"📚 Research: {RESEARCH_CONFIG['type']} - {RESEARCH_CONFIG['name']}", "cyan")
        cprint(f"📊 Backtest: {BACKTEST_CONFIG['type']} - {BACKTEST_CONFIG['name']}", "cyan")
        cprint(f"🔧 Debug: {DEBUG_CONFIG['type']} - {DEBUG_CONFIG['name']}", "cyan")
        cprint(f"📦 Package: {PACKAGE_CONFIG['type']} - {PACKAGE_CONFIG['name']}", "cyan")
        main()
    except KeyboardInterrupt:
        cprint("\n👋 Moon Dev's RBI AI shutting down gracefully...", "yellow")
    except Exception as e:
        cprint(f"\n❌ Fatal error: {str(e)}", "red")
