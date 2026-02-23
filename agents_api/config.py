import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()

# When using OpenAI:
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or ""

# When using Ollama with its OpenAI-compatible API:
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")

MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

SUPABASE_URL = os.getenv("SUPABASE_URL") or ""
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""

# Simple, overridable threshold for intent scoring
try:
    QUALIFICATION_INTENT_THRESHOLD = int(os.getenv("QUALIFICATION_INTENT_THRESHOLD", "70"))
except ValueError:
    QUALIFICATION_INTENT_THRESHOLD = 70


def ensure_supabase_config() -> None:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set for Agents API.")


def create_async_llm_client() -> AsyncOpenAI:
    """
    Create an AsyncOpenAI-compatible client.

    Supports:
    - LLM_PROVIDER=openai  (default)
    - LLM_PROVIDER=ollama  (uses Ollama's OpenAI-compatible /v1 API)
    """
    if LLM_PROVIDER == "ollama":
        # Ollama's OpenAI-compatible API ignores the API key but requires something non-empty.
        api_key = OPENAI_API_KEY or "ollama"
        return AsyncOpenAI(api_key=api_key, base_url=OLLAMA_BASE_URL)

    # Default: OpenAI using the official endpoint; ignore any OPENAI_BASE_URL env.
    os.environ.pop("OPENAI_BASE_URL", None)
    return AsyncOpenAI(api_key=OPENAI_API_KEY)
