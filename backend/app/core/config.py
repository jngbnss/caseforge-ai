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
    ollama_base_url: str = "http://127.0.0.1:11434"
    embedding_backend: str = "mock"
    embedding_model: str = "bge-m3"
    embedding_on_cpu: bool = True
    llm_contradictions: bool = True
    """심문 응답 뒤에 LLM 모순 판정을 비동기로 돌린다 (source='llm')."""
    debug_api: bool = False
    """True면 심문 응답에 근거·가드 결과를 넣는다. 비밀 키워드가 보이므로 개발 환경에서만 켠다."""


settings = Settings()
