from app.core.config import Settings


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "0.1.0",
        "llm_backend": "mock",
        "embedding_backend": "mock",
    }


def test_default_backends_are_mock():
    settings = Settings(_env_file=None)
    assert settings.llm_backend == "mock"
    assert settings.embedding_backend == "mock"
