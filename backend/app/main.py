from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import settings
from app.core.db import make_engine, make_sessionmaker
from app.core.embedding.mock import MockEmbedding
from app.core.embedding.ports import EmbeddingPort
from app.core.game import GameError
from app.core.llm.mock import MockLLM
from app.core.llm.ports import LLMPort


def default_llm_factory() -> Callable[[str], LLMPort]:
    if settings.llm_backend == "mock":
        return lru_cache(MockLLM.for_case)
    raise RuntimeError(f"LLM_BACKEND={settings.llm_backend}는 4단계에서 지원한다. mock을 쓴다.")


def default_embedder() -> EmbeddingPort:
    if settings.embedding_backend == "mock":
        return MockEmbedding()
    raise RuntimeError(f"EMBEDDING_BACKEND={settings.embedding_backend}는 4단계에서 지원한다.")


def create_app(
    database_url: str | None = None,
    llm_for_case: Callable[[str], LLMPort] | None = None,
    embedder: EmbeddingPort | None = None,
) -> FastAPI:
    app = FastAPI(title="CaseForge AI", version="0.2.0")
    app.state.sessionmaker = make_sessionmaker(make_engine(database_url or settings.database_url))
    app.state.llm_for_case = llm_for_case or default_llm_factory()
    app.state.embedder = embedder or default_embedder()

    @app.exception_handler(GameError)
    async def game_error(_: Request, exc: GameError) -> JSONResponse:
        return JSONResponse(status_code=exc.status, content={"detail": exc.message})

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)
    return app


app = create_app()
