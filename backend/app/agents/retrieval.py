"""Per-NPC vector indexes (proposal §3, build-time separation).

index[npc] contains only facts with npc ∈ known_by (leak_forbidden facts are left out
entirely). Another NPC's secret is not filtered out of the results - it was never indexed.
Results are filtered once more by the request-time KnowledgeScope.
"""

from __future__ import annotations

from case_validator import CaseBible
from case_validator.schema import Fact

from app.agents.knowledge_scope import KnowledgeScope
from app.agents.prompting import RetrievedFact
from app.core.embedding.ports import EmbeddingPort


class NpcIndex:
    """Exact inner-product index over normalised vectors (FAISS IndexFlatIP when available)."""

    def __init__(self, facts: list[Fact], vectors: list[list[float]]) -> None:
        self.facts = facts
        self._faiss = None
        self._vectors = vectors
        try:
            import faiss  # type: ignore[import-not-found]
            import numpy as np
        except ImportError:
            return
        if vectors:
            matrix = np.asarray(vectors, dtype="float32")
            index = faiss.IndexFlatIP(matrix.shape[1])
            index.add(matrix)
            self._faiss = index

    @property
    def fact_ids(self) -> frozenset[str]:
        return frozenset(f.fact_id for f in self.facts)

    def search(self, query: list[float], k: int) -> list[tuple[Fact, float]]:
        if not self.facts:
            return []
        k = min(k, len(self.facts))
        if self._faiss is not None:
            import numpy as np

            scores, ids = self._faiss.search(np.asarray([query], dtype="float32"), k)
            return [(self.facts[i], float(s)) for i, s in zip(ids[0], scores[0], strict=True)]
        scored = [
            (fact, sum(a * b for a, b in zip(query, vec, strict=True)))
            for fact, vec in zip(self.facts, self._vectors, strict=True)
        ]
        return sorted(scored, key=lambda pair: -pair[1])[:k]


class IndexRegistry:
    """Builds the per-NPC indexes once per (case hash, NPC)."""

    def __init__(self, embedder: EmbeddingPort) -> None:
        self.embedder = embedder
        self._indexes: dict[tuple[str, str], NpcIndex] = {}

    def get(self, bible: CaseBible, case_sha256: str, npc_id: str) -> NpcIndex:
        key = (case_sha256, npc_id)
        if key not in self._indexes:
            facts = [f for f in bible.facts if npc_id in f.known_by and not f.leak_forbidden]
            vectors = self.embedder.embed([f.content for f in facts]) if facts else []
            self._indexes[key] = NpcIndex(facts, vectors)
        return self._indexes[key]


def retrieve(
    registry: IndexRegistry,
    bible: CaseBible,
    case_sha256: str,
    scope: KnowledgeScope,
    question: str,
    k: int = 5,
) -> list[RetrievedFact]:
    index = registry.get(bible, case_sha256, scope.npc_id)
    query = registry.embedder.embed([question])[0]
    hits = index.search(query, k=len(index.facts))
    results = [RetrievedFact(f, s) for f, s in hits if f.fact_id in scope.allowed_fact_ids][:k]
    # Facts the player handed over by presenting evidence are always in context.
    seen = {r.fact.fact_id for r in results}
    for item in scope.presented_evidence:
        for fid in item.proves_fact_ids:
            if fid in scope.facts and fid not in seen:
                results.append(RetrievedFact(scope.facts[fid], 1.0))
                seen.add(fid)
    return results
