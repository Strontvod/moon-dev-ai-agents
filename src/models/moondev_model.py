"""
Moon Dev AI Chat API Model
OpenAI-compatible drop-in replacement using MOONDEV_API_KEY.

No extra API key needed — uses the same MOONDEV_API_KEY from .env.
Endpoint: https://api.moondev.com/v1/chat/completions (OpenAI-compatible)

Usage in config.py:
    AI_MODEL = "moondev"   # Use MoonDev AI Chat API

Usage via ModelFactory:
    model = ModelFactory.create_model('moondev')
    response = model.generate("Analyze BTC price action...")

Fallback: If MOONDEV_API_KEY is not set or the API call fails,
          falls back to the model specified in MOONDEV_FALLBACK_MODEL.
"""

import os
from termcolor import cprint
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

from src.models.base_model import BaseModel

# MoonDev AI Chat API endpoint (OpenAI-compatible)
MOONDEV_CHAT_URL  = "https://api.moondev.com/v1/chat/completions"
MOONDEV_API_KEY   = os.getenv("MOONDEV_API_KEY", "")

# Default model served by MoonDev AI Chat API
# (check moondev.com/docs for available models)
DEFAULT_MODEL_NAME = "gpt-4o-mini"   # cheap, fast — good for BUY/SELL/NOTHING decisions

# Fallback model type if MoonDev API unavailable
MOONDEV_FALLBACK_MODEL = "groq"      # free, fast


class MoonDevModel(BaseModel):
    """
    OpenAI-compatible model wrapper for Moon Dev AI Chat API.

    Saves cost vs direct Claude/GPT calls:
    - Uses MOONDEV_API_KEY (already needed for data layer)
    - No separate OpenAI/Anthropic key required
    - Supports all OpenAI-compatible models served by MoonDev
    """

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME):
        self.model_name = model_name
        self.api_key    = MOONDEV_API_KEY
        self._client    = None
        self._fallback  = None

        if not self.api_key:
            cprint("⚠️  MOONDEV_API_KEY not set — MoonDevModel will use fallback", "yellow")
        else:
            try:
                import openai
                self._client = openai.OpenAI(
                    api_key=self.api_key,
                    base_url=MOONDEV_CHAT_URL.replace("/chat/completions", ""),
                )
                cprint(f"✅ MoonDevModel initialized ({self.model_name})", "green")
            except ImportError:
                cprint("⚠️  openai package not installed — pip install openai", "yellow")
            except Exception as e:
                cprint(f"⚠️  MoonDevModel init error: {e}", "yellow")

    def _get_fallback(self):
        """Lazy-load fallback model."""
        if self._fallback is None:
            try:
                from src.models.model_factory import ModelFactory
                self._fallback = ModelFactory.create_model(MOONDEV_FALLBACK_MODEL)
                cprint(f"  Using fallback model: {MOONDEV_FALLBACK_MODEL}", "yellow")
            except Exception as e:
                cprint(f"  Fallback model error: {e}", "red")
        return self._fallback

    def generate(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful AI trading assistant.",
        max_tokens: int = 300,
        temperature: float = 0.7,
    ) -> str:
        """
        Generate a response using MoonDev AI Chat API.

        Args:
            prompt:        User message / trading analysis request
            system_prompt: System context (role, instructions)
            max_tokens:    Max response tokens (300 is plenty for BUY/SELL/NOTHING)
            temperature:   0 = deterministic, 1 = creative

        Returns:
            str: Model response text, or empty string on failure
        """
        # Try MoonDev API first
        if self._client:
            try:
                response = self._client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": prompt},
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                cprint(f"⚠️  MoonDev API call failed: {e} — falling back", "yellow")

        # Fallback to groq/deepseek/etc.
        fallback = self._get_fallback()
        if fallback:
            try:
                return fallback.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            except Exception as e:
                cprint(f"❌ Fallback model also failed: {e}", "red")

        return ""

    def __repr__(self) -> str:
        status = "connected" if self._client else "fallback-only"
        return f"MoonDevModel(model={self.model_name}, status={status})"


if __name__ == "__main__":
    cprint("🌙 MoonDev AI Chat API Model Test", "cyan", attrs=["bold"])
    model = MoonDevModel()
    print(repr(model))

    test_prompt = (
        "BTC is up 2% in the last hour with increasing volume. "
        "Funding rate is +0.01% (slightly positive). "
        "Respond in exactly 3 lines:\n"
        "Line 1: BUY, SELL, or NOTHING\n"
        "Line 2: One short reason\n"
        "Line 3: Confidence: X%"
    )

    cprint("\nTest prompt:", "white")
    cprint(test_prompt, "white")
    cprint("\nResponse:", "cyan")
    result = model.generate(test_prompt)
    cprint(result if result else "(no response)", "green" if result else "red")
