"""LLM factory: returns CrewAI-compatible LLM objects via LiteLLM.

Supported free-tier providers (set via PRIMARY_LLM / FAST_LLM in .env):

  groq/llama-3.3-70b-versatile                          GROQ_API_KEY
  cerebras/llama-3.3-70b                                CEREBRAS_API_KEY
  together_ai/meta-llama/Meta-Llama-3.3-70B-Instruct-Turbo  TOGETHER_API_KEY
  openrouter/meta-llama/llama-3.3-70b-instruct:free     OPENROUTER_API_KEY
  gemini/gemini-1.5-flash                               GEMINI_API_KEY
  mistral/mistral-small-latest                          MISTRAL_API_KEY
"""

from functools import lru_cache

from crewai import LLM

from app.config import get_settings

settings = get_settings()

# ── CrewAI 1.14.x bug fix ────────────────────────────────────────────────────
# CrewAI marks every message with `cache_breakpoint: True` for Anthropic prompt
# caching, but only strips that key in the Anthropic provider adapter. For every
# other provider the key leaks into the raw API payload and gets rejected.
# Patch: strip it for non-Anthropic providers before messages reach LiteLLM.
_orig_format_messages = LLM._format_messages_for_provider


def _patched_format_messages(self, messages):  # type: ignore[override]
    result = _orig_format_messages(self, messages)
    if not getattr(self, "is_anthropic", False):
        return [{k: v for k, v in msg.items() if k != "cache_breakpoint"} for msg in result]
    return result


LLM._format_messages_for_provider = _patched_format_messages  # type: ignore[method-assign]
# ─────────────────────────────────────────────────────────────────────────────

_KEY_MAP = {
    "groq":         lambda s: s.groq_api_key,
    "cerebras":     lambda s: s.cerebras_api_key,
    "together_ai":  lambda s: s.together_api_key,
    "openrouter":   lambda s: s.openrouter_api_key,
    "gemini":       lambda s: s.gemini_api_key,
    "mistral":      lambda s: s.mistral_api_key,
}


def _api_key_for(model: str) -> str:
    """Return the correct API key for the provider inferred from the model name."""
    provider = model.split("/")[0] if "/" in model else ""
    getter = _KEY_MAP.get(provider)
    return getter(settings) if getter else ""


@lru_cache(maxsize=2)
def get_primary_llm() -> LLM:
    return LLM(
        model=settings.primary_llm,
        api_key=_api_key_for(settings.primary_llm),
        timeout=settings.llm_timeout_seconds,
        max_retries=settings.max_retries,
    )


@lru_cache(maxsize=2)
def get_fast_llm() -> LLM:
    return LLM(
        model=settings.fast_llm,
        api_key=_api_key_for(settings.fast_llm),
        timeout=settings.llm_timeout_seconds,
        max_retries=settings.max_retries,
    )
