"""Deterministic hash embedding: character bigrams hashed into a fixed-size vector.

Shared bigrams give a crude lexical similarity, which is enough for retrieval tests in CI
without downloading a model.
"""

import hashlib
import math


class HashEmbedding:
    model_id = "mock-hash"

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        compact = "".join(text.lower().split())
        grams = [compact[i : i + 2] for i in range(max(len(compact) - 1, 1))]
        for gram in grams:
            digest = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "little") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[index] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]
