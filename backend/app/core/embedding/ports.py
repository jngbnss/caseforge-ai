from __future__ import annotations

from typing import Protocol


class EmbeddingPort(Protocol):
    model_id: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...
