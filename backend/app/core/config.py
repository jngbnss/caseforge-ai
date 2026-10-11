from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    """Runtime settings from environment variables or a local .env (never committed)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cases_dir: Path = REPO_ROOT / "cases"
    default_case_id: str = "museum-001"
    database_url: str = f"sqlite:///{BACKEND_ROOT / 'caseforge.sqlite3'}"

    llm_backend: Literal["mock", "ollama", "llamacpp"] = "mock"
    llm_model: str = "qwen3:8b"
    llm_timeout_s: float = 120.0
    ollama_base_url: str = "http://localhost:11434"
    mock_script_path: Path = BACKEND_ROOT / "tests" / "fixtures" / "mock_npc.yaml"

    embedding_backend: Literal["mock", "bge"] = "mock"
    embedding_model: str = "bge-m3"

    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
