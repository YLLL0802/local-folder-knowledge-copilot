from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Runtime configuration loaded from environment variables and defaults."""

    llm_provider: str = "openai_compatible"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    embedding_provider: str = "sentence_transformers"
    embedding_model: str = "BAAI/bge-large-en-v1.5"
    qdrant_url: str = ""
    qdrant_path: Path = Path(".qdrant")
    qdrant_collection: str = "local_onedrive_copilot"
    chunk_size: int = Field(default=800, gt=0)
    chunk_overlap: int = Field(default=120, ge=0)
    top_k: int = Field(default=5, gt=0)
    min_score: float = Field(default=0.25, ge=0.0)
    audit_log_path: Path = Path("logs/audit.jsonl")


def _getenv(name: str, default: str = "") -> str:
    """Read an environment variable with a fallback default value."""

    import os

    return os.getenv(name, default)


@lru_cache
def get_settings() -> Settings:
    """Load `.env` once and return cached application settings."""

    load_dotenv()
    return Settings(
        llm_provider=_getenv("LLM_PROVIDER", "openai_compatible"),
        llm_base_url=_getenv("LLM_BASE_URL"),
        llm_api_key=_getenv("LLM_API_KEY"),
        llm_model=_getenv("LLM_MODEL"),
        embedding_provider=_getenv("EMBEDDING_PROVIDER", "sentence_transformers"),
        embedding_model=_getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5"),
        qdrant_url=_getenv("QDRANT_URL"),
        qdrant_path=Path(_getenv("QDRANT_PATH", ".qdrant")),
        qdrant_collection=_getenv("QDRANT_COLLECTION", "local_onedrive_copilot"),
        chunk_size=int(_getenv("CHUNK_SIZE", "800")),
        chunk_overlap=int(_getenv("CHUNK_OVERLAP", "120")),
        top_k=int(_getenv("TOP_K", "5")),
        min_score=float(_getenv("MIN_SCORE", "0.25")),
        audit_log_path=Path(_getenv("AUDIT_LOG_PATH", "logs/audit.jsonl")),
    )
