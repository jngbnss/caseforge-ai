from fastapi.testclient import TestClient

from app.main import app


def test_health():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_default_llm_backend_is_mock():
    from app.core.config import Settings

    assert Settings(_env_file=None).llm_backend == "mock"
