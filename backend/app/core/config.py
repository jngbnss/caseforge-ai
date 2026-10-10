from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cases_dir: Path = REPO_ROOT / "cases"
    default_case_id: str = "museum-001"
    database_url: str = "sqlite:///./caseforge.db"
    llm_backend: str = "mock"
    llm_model: str = "qwen3:8b"
    embedding_backend: str = "mock"


settings = Settings()
