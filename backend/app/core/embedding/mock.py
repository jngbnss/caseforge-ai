"""해시 기반 결정론 임베딩. 문자 2-gram을 고정 차원에 해시해 L2 정규화한다.

의미 검색 품질은 낮지만 글자가 겹치는 문장끼리는 가깝게 나온다. CI와 테스트용이다.
"""

from __future__ import annotations

import hashlib
import math


class MockEmbedding:
    model_id = "mock-bigram"

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        compact = "".join(text.split())
        grams = [compact[i : i + 2] for i in range(max(1, len(compact) - 1))]
        for gram in grams:
            digest = hashlib.md5(gram.encode("utf-8")).digest()
            vec[int.from_bytes(digest[:4], "little") % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]
