"""NPC별 독립 FAISS 인덱스.

인덱스에는 그 NPC가 알 수 있는 사실(known_by)과 누구에게나 제시될 수 있는 증거 기록만 넣는다.
다른 NPC만 아는 사실과 금지 사실은 인덱스에 아예 없으므로, 어떤 질문으로도 검색되지 않는다.
검색 결과는 다시 이번 턴의 지식 범위(공개 조건 충족 여부)로 거른다.
"""

from __future__ import annotations

from dataclasses import dataclass

import faiss
import numpy as np

from app.core.embedding.ports import EmbeddingPort
from case_validator import CaseBible


@dataclass(frozen=True)
class Hit:
    id: str
    score: float


def indexable_fact_ids(bible: CaseBible, npc_id: str) -> list[str]:
    evidence_facts = {fid for e in bible.evidence for fid in e.proves_fact_ids}
    return [
        f.fact_id
        for f in bible.facts
        if not f.forbidden and (npc_id in f.known_by or f.fact_id in evidence_facts)
    ]


class NpcIndex:
    def __init__(
        self,
        embedder: EmbeddingPort,
        ids: list[str],
        texts: list[str],
        vectors: list[list[float]] | None = None,
    ) -> None:
        self.embedder = embedder
        self.ids = ids
        if vectors is None and texts:
            vectors = embedder.embed(texts)
        vectors = np.asarray(vectors, dtype="float32") if vectors else None
        self.index: faiss.Index | None = None
        if vectors is not None and len(vectors):
            faiss.normalize_L2(vectors)
            self.index = faiss.IndexFlatIP(vectors.shape[1])
            self.index.add(vectors)

    def __len__(self) -> int:
        return len(self.ids)

    def search(self, query: str, k: int, allowed: set[str] | None = None) -> list[Hit]:
        if self.index is None:
            return []
        q = np.asarray(self.embedder.embed([query]), dtype="float32")
        faiss.normalize_L2(q)
        scores, positions = self.index.search(q, len(self.ids))
        hits = [
            Hit(self.ids[p], float(s))
            for s, p in zip(scores[0], positions[0], strict=True)
            if p >= 0 and (allowed is None or self.ids[p] in allowed)
        ]
        return hits[:k]


class NpcIndexRegistry:
    """(임베딩 모델, 사건 해시, NPC)마다 인덱스를 한 번만 만든다."""

    def __init__(self) -> None:
        self._indexes: dict[tuple[str, str, str], NpcIndex] = {}
        self._vectors: dict[tuple[str, str], list[float]] = {}

    def get(
        self, embedder: EmbeddingPort, bible: CaseBible, case_sha: str, npc_id: str
    ) -> NpcIndex:
        key = (embedder.model_id, case_sha, npc_id)
        if key not in self._indexes:
            ids = indexable_fact_ids(bible, npc_id)
            texts = [f.content for fid in ids if (f := bible.fact(fid))]
            missing = [
                t for t in dict.fromkeys(texts) if (embedder.model_id, t) not in self._vectors
            ]
            for text, vec in zip(missing, embedder.embed(missing), strict=True):
                self._vectors[(embedder.model_id, text)] = vec
            vectors = [self._vectors[(embedder.model_id, t)] for t in texts]
            self._indexes[key] = NpcIndex(embedder, ids, texts, vectors)
        return self._indexes[key]

    def warm(self, embedder: EmbeddingPort, bible: CaseBible, case_sha: str) -> None:
        """서버 시작 때 모든 NPC 인덱스를 미리 만든다 (첫 심문이 느려지지 않게)."""
        for suspect in bible.suspects:
            self.get(embedder, bible, case_sha, suspect.suspect_id)


registry = NpcIndexRegistry()
