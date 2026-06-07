"""Central configuration loaded from environment variables."""

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────────────────────────
    # Model names include the provider prefix, e.g. "groq/llama-3.3-70b-versatile"
    # Supported prefixes: groq | cerebras | together_ai | openrouter | gemini | mistral
    primary_llm: str = "groq/llama-3.3-70b-versatile"
    fast_llm: str = "groq/llama-3.3-70b-versatile"

    # ── LLM Provider API Keys (only the one matching your model prefix is needed)
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    cerebras_api_key: str = Field(default="", alias="CEREBRAS_API_KEY")
    together_api_key: str = Field(default="", alias="TOGETHER_API_KEY")
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    mistral_api_key: str = Field(default="", alias="MISTRAL_API_KEY")

    # ── Models ────────────────────────────────────────────────────────────────
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # ── Qdrant ────────────────────────────────────────────────────────────────
    qdrant_mode: str = "local"
    qdrant_path: str = "./storage/qdrant"
    qdrant_collection: str = "hermes_docs"

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./storage/hermes.db"

    # ── Dataset ───────────────────────────────────────────────────────────────
    dataset_profile: str = "medium"
    hf_dataset_id: str = "onyx-dot-app/EnterpriseRAG-Bench"
    hf_token: str = Field(default="", alias="HF_TOKEN")

    # ── Retrieval ─────────────────────────────────────────────────────────────
    embedding_batch_size: int = 16
    index_write_batch_size: int = 100
    max_chunk_tokens: int = 400
    chunk_overlap_tokens: int = 50
    max_retrieved_documents: int = 50
    max_reranked_documents: int = 10
    max_llm_context_documents: int = 8

    # ── Agent limits ──────────────────────────────────────────────────────────
    max_agent_iterations: int = 5
    max_tool_calls: int = 10

    # ── Timeouts ──────────────────────────────────────────────────────────────
    retrieval_timeout_seconds: int = 10
    tool_timeout_seconds: int = 20
    llm_timeout_seconds: int = 60
    workflow_timeout_seconds: int = 120
    max_retries: int = 3

    # ── Langfuse ──────────────────────────────────────────────────────────────
    langfuse_public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = "https://cloud.langfuse.com"
    langfuse_enabled: bool = True

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_dir: str = "./storage/logs"

    # ── API ───────────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    secret_key: str = "change_this_secret"

    # ── Dataset profiles ──────────────────────────────────────────────────────
    @property
    def dataset_config(self) -> dict:
        profiles = {
            "small":  {"questions": 25,  "distractors": 5_000,  "seed": 42},
            "medium": {"questions": 75,  "distractors": 20_000, "seed": 42},
            "full":   {"questions": 500, "distractors": None,   "seed": 42},
        }
        return profiles.get(self.dataset_profile, profiles["medium"])


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
