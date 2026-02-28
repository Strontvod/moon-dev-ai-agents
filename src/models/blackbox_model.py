"""
Blackbox AI Model Implementation

Blackbox AI — OpenAI-compatible chat completions API.
Endpoint: https://api.blackbox.ai/chat/completions
API Key format: sk-xxxx (get at https://www.blackbox.ai/dashboard → API Keys)

NOTE: Blackbox has TWO key types:
  - sk-xxxx  → Chat completions API (api.blackbox.ai) — used by this model
  - bb_xxxx  → Cloud tasks/multi-agent API (cloud.blackbox.ai) — used by blackbox_multi_agent.py
"""

from openai import OpenAI
from termcolor import cprint
from .base_model import BaseModel, ModelResponse
import time
import re


class BlackboxModel(BaseModel):
    """OpenAI-compatible model wrapper for Blackbox AI Cloud"""

    AVAILABLE_MODELS = {
        "blackboxai/blackbox-pro": {
            "description": "Blackbox Pro — flagship coding model",
            "input_price": "See cloud.blackbox.ai",
            "output_price": "See cloud.blackbox.ai"
        },
        "blackboxai/anthropic/claude-sonnet-4.5": {
            "description": "Claude Sonnet 4.5 via Blackbox",
            "input_price": "See cloud.blackbox.ai",
            "output_price": "See cloud.blackbox.ai"
        },
        "blackboxai/anthropic/claude-opus-4.5": {
            "description": "Claude Opus 4.5 via Blackbox",
            "input_price": "See cloud.blackbox.ai",
            "output_price": "See cloud.blackbox.ai"
        },
        "blackboxai/openai/gpt-5.2-codex": {
            "description": "GPT-5.2 Codex via Blackbox",
            "input_price": "See cloud.blackbox.ai",
            "output_price": "See cloud.blackbox.ai"
        },
        "blackboxai/google/gemini-2.5-pro": {
            "description": "Gemini 2.5 Pro via Blackbox",
            "input_price": "See cloud.blackbox.ai",
            "output_price": "See cloud.blackbox.ai"
        },
        "blackboxai/x-ai/grok-code-fast-1:free": {
            "description": "Grok Code Fast (free tier)",
            "input_price": "Free",
            "output_price": "Free"
        },
    }

    def __init__(self, api_key: str, model_name: str = "blackboxai/blackbox-pro", **kwargs):
        cprint(f"\n🔌 Blackbox AI Model Initialization", "cyan")

        if not api_key or len(api_key.strip()) == 0:
            raise ValueError("Blackbox API key is empty or None")

        cprint(f"🔑 API Key: {len(api_key)} chars, starts with sk-: {'yes' if api_key.startswith('sk-') else 'no'}", "cyan")
        cprint(f"📝 Model: {model_name}", "cyan")

        if model_name not in self.AVAILABLE_MODELS:
            cprint(f"  ⚠️ Model not in predefined list (will still try)", "yellow")

        self.model_name = model_name
        self.max_tokens = 300
        super().__init__(api_key, **kwargs)

    def initialize_client(self, **kwargs) -> None:
        """Initialize the Blackbox AI client (OpenAI-compatible)"""
        try:
            cprint(f"  🔌 Connecting to Blackbox AI Cloud...", "cyan")
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.blackbox.ai"
            )
            cprint(f"  ✅ Blackbox AI client created", "green")

            # Test connection
            cprint(f"  🧪 Testing connection...", "cyan")
            test_response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            cprint(f"  ✅ Test OK: {test_response.choices[0].message.content}", "green")

            model_info = self.AVAILABLE_MODELS.get(self.model_name, {})
            cprint(f"  ✨ Blackbox AI ready: {self.model_name}", "green")
            if model_info:
                cprint(f"  └─ {model_info.get('description', '')}", "cyan")

        except Exception as e:
            cprint(f"\n❌ Failed to initialize Blackbox AI client", "red")
            cprint(f"  ├─ {type(e).__name__}: {e}", "red")
            if "401" in str(e):
                cprint(f"  └─ Check your BLACKBOX_CHAT_KEY in .env (format: sk-xxxx from blackbox.ai/dashboard)", "red")
            self.client = None
            raise

    def generate_response(self, system_prompt, user_content, temperature=0.7, max_tokens=None):
        """Generate response via Blackbox AI chat completions"""
        try:
            timestamp = int(time.time() * 1000)

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{user_content}_{timestamp}"}
                ],
                temperature=temperature,
                max_tokens=max_tokens if max_tokens else self.max_tokens,
                stream=False
            )

            raw_content = response.choices[0].message.content

            # Strip <think>...</think> blocks from reasoning models
            filtered = re.sub(r'<think>.*?</think>', '', raw_content, flags=re.DOTALL).strip()
            if '<think>' in filtered:
                filtered = filtered.split('<think>')[0].strip()
            final_content = filtered if filtered else raw_content

            return ModelResponse(
                content=final_content,
                raw_response=response,
                model_name=self.model_name,
                usage=response.usage
            )

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "rate_limit" in error_str:
                cprint(f"⚠️  Blackbox rate limit — skipping", "yellow")
                return None
            if "402" in error_str:
                cprint(f"⚠️  Blackbox credits insufficient — add at cloud.blackbox.ai", "yellow")
                return None
            if "503" in error_str:
                raise e
            cprint(f"❌ Blackbox error: {error_str}", "red")
            return None

    def is_available(self) -> bool:
        return self.client is not None

    @property
    def model_type(self) -> str:
        return "blackbox"
