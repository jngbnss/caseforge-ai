"""메모리 벡터 인덱스. 4단계에서 NPC별 FAISS 인덱스로 바꾼다."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.embedding.ports import EmbeddingPort


@dataclass(frozen=True)
class Hit:
    id: str
    score: float


class VectorIndex:
    def __init__(self, embedder: EmbeddingPort, items: dict[str, str]) -> None:
        self.embedder = embedder
        self.ids = list(items)
        self.vectors = embedder.embed(list(items.values())) if items else []

    def __len__(self) -> int:
        return len(self.ids)

    def search(self, query: str, k: int, allowed: set[str] | None = None) -> list[Hit]:
        """코사인 유사도 상위 k개. allowed가 있으면 그 안에서만 고른다."""
        if not self.ids:
            return []
        (q,) = self.embedder.embed([query])
        hits = [
            Hit(i, sum(a * b for a, b in zip(q, v, strict=True)))
            for i, v in zip(self.ids, self.vectors, strict=True)
            if allowed is None or i in allowed
        ]
        return sorted(hits, key=lambda h: (-h.score, h.id))[:k]
