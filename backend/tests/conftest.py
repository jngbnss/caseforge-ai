from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.cases import get_case
from app.core.config import Settings
from app.core.services import Services
from app.main import create_app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url="sqlite://",
        llm_backend="mock",
        embedding_backend="mock",
        mock_script_path=FIXTURES / "mock_npc.yaml",
    )


@pytest.fixture
def services(settings: Settings) -> Services:
    return Services.build(settings)


@pytest.fixture
def client(settings: Settings, services: Services) -> Iterator[TestClient]:
    with TestClient(create_app(settings, services)) as c:
        yield c


@pytest.fixture(scope="session")
def museum():
    return get_case("museum-001")
