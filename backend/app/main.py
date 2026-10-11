from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import router, ws_router
from app.cases.registry import get_case
from app.core.config import settings
from app.core.db import make_engine, make_sessionmaker
from app.core.embedding.mock import MockEmbedding
from app.core.embedding.npc_index import registry
from app.core.embedding.ollama import OllamaEmbedding
from app.core.embedding.ports import EmbeddingPort
from app.core.game import GameError
from app.core.llm.mock import MockLLM
from app.core.llm.ollama import OllamaLLM
from app.core.llm.ports import LLMPort


def default_llm_factory() -> Callable[[str], LLMPort]:
    if settings.llm_backend == "mock":
        return lru_cache(MockLLM.for_case)
    if settings.llm_backend == "ollama":
        llm = OllamaLLM(settings.llm_model, settings.ollama_base_url)
        return lambda _case_id: llm
    raise RuntimeError(f"지원하지 않는 LLM_BACKEND: {settings.llm_backend} (mock | ollama)")


def default_embedder() -> EmbeddingPort:
    if settings.embedding_backend == "mock":
        return MockEmbedding()
    if settings.embedding_backend == "ollama":
        return OllamaEmbedding(
            settings.embedding_model, settings.ollama_base_url, cpu=settings.embedding_on_cpu
        )
    raise RuntimeError(
        f"지원하지 않는 EMBEDDING_BACKEND: {settings.embedding_backend} (mock | ollama)"
    )


def _log_warm_failure(task: asyncio.Task) -> None:
    if not task.cancelled() and task.exception():
        logging.getLogger(__name__).warning("NPC 인덱스 미리 만들기 실패: %r", task.exception())


def create_app(
    database_url: str | None = None,
    llm_for_case: Callable[[str], LLMPort] | None = None,
    embedder: EmbeddingPort | None = None,
    debug_api: bool | None = None,
    llm_contradictions: bool | None = None,
    deduction_feedback: bool | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        loaded = get_case(settings.default_case_id)
        task = asyncio.create_task(
            asyncio.to_thread(registry.warm, app.state.embedder, loaded.bible, loaded.sha256)
        )
        task.add_done_callback(_log_warm_failure)
        yield

    app = FastAPI(title="CaseForge AI", version="0.3.0", lifespan=lifespan)
    app.state.sessionmaker = make_sessionmaker(make_engine(database_url or settings.database_url))
    app.state.llm_for_case = llm_for_case or default_llm_factory()
    app.state.embedder = embedder or default_embedder()
    app.state.debug_api = settings.debug_api if debug_api is None else debug_api
    app.state.llm_contradictions = (
        settings.llm_contradictions if llm_contradictions is None else llm_contradictions
    )
    app.state.deduction_feedback = (
        settings.deduction_feedback if deduction_feedback is None else deduction_feedback
    )
    app.state.judge_tasks = set()

    @app.exception_handler(GameError)
    async def game_error(_: Request, exc: GameError) -> JSONResponse:
        return JSONResponse(status_code=exc.status, content={"detail": exc.message})

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)
    app.include_router(ws_router)
    return app


app = create_app()
