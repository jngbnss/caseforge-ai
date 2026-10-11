from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Runtime settings from environment variables or a local .env (never committed)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cases_dir: Path = REPO_ROOT / "cases"
    default_case_id: str = "museum-001"
    llm_backend: Literal["mock", "ollama", "llamacpp"] = "mock"
    llm_model: str = "qwen3:8b-q4_K_M"
    ollama_base_url: str = "http://localhost:11434"
    embedding_backend: Literal["mock", "bge"] = "mock"
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
