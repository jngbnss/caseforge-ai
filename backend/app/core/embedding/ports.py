from typing import Protocol


class EmbeddingPort(Protocol):
    model_id: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one L2-normalised vector per text."""
        ...
