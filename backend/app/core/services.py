"""Adapter selection from settings, and the service container the API uses."""

from __future__ import annotations

from dataclasses import dataclass

from app.agents.interrogation import Interrogator
from app.agents.retrieval import IndexRegistry
from app.core.config import Settings
from app.core.db import SessionRepository, make_engine
from app.core.embedding.mock import HashEmbedding
from app.core.embedding.ports import EmbeddingPort
from app.core.llm.mock import MockLLM
from app.core.llm.ports import LLMPort


def make_llm(settings: Settings) -> LLMPort:
    if settings.llm_backend == "mock":
        return MockLLM(settings.mock_script_path)
    if settings.llm_backend == "ollama":
        from app.core.llm.ollama import OllamaLLM

        return OllamaLLM(settings.ollama_base_url, settings.llm_model, settings.llm_timeout_s)
    raise NotImplementedError("llamacpp adapter is not implemented yet (see core/llm/llamacpp.py)")


def make_embedder(settings: Settings) -> EmbeddingPort:
    if settings.embedding_backend == "mock":
        return HashEmbedding()
    from app.core.embedding.bge import BgeEmbedding

    return BgeEmbedding(settings.ollama_base_url, settings.embedding_model)


@dataclass
class Services:
    settings: Settings
    repo: SessionRepository
    llm: LLMPort
    interrogator: Interrogator

    @classmethod
    def build(
        cls,
        settings: Settings,
        llm: LLMPort | None = None,
        embedder: EmbeddingPort | None = None,
    ) -> Services:
        llm = llm or make_llm(settings)
        embedder = embedder or make_embedder(settings)
        return cls(
            settings=settings,
            repo=SessionRepository(make_engine(settings.database_url)),
            llm=llm,
            interrogator=Interrogator(llm, IndexRegistry(embedder)),
        )
