from fastapi.testclient import TestClient

from app.cases.registry import get_case
from app.core.config import settings
from app.main import app


def test_health() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_default_case_loads() -> None:
    loaded = get_case(settings.default_case_id)
    assert loaded.bible.case_id == "museum-001"
    assert len(loaded.sha256) == 64
