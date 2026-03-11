"""
Application settings loaded from environment variables.
Uses pydantic-settings for validation and type coercion.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the AI Knowledge Platform."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────
    app_name: str = "AI Knowledge Platform"
    debug: bool = False
    log_level: str = "info"

    # ── Database ─────────────────────────────────────────
    database_url: str = "postgresql://postgres:postgres@localhost:5432/ai_knowledge_platform"

    # ── AWS S3 ───────────────────────────────────────────
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "ai-knowledge-platform-docs"

    # ── Ollama ───────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"

    # ── External LLM Keys (Optional) ────────────────────
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # ── Embeddings ───────────────────────────────────────
    embedding_model: str = "BAAI/bge-large-en-v1.5"

    # ── Vector Store ─────────────────────────────────────
    vector_store_type: str = "chroma"  # "chroma" | "qdrant"
    chroma_persist_dir: str = "./data/chroma"
    qdrant_url: str = "http://localhost:6333"

    # ── RAG ──────────────────────────────────────────────
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k: int = 5

    # ── Auth / JWT ───────────────────────────────────────
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 h

    # ── Rate Limiting ────────────────────────────────────
    rate_limit: str = "60/minute"


settings = Settings()
