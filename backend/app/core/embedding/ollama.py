"""Ollama로 서빙하는 bge-m3 임베딩. 한국어를 지원하고 torch 설치 없이 LLM과 같은 런타임을 쓴다."""

from __future__ import annotations

import httpx


class OllamaEmbedding:
    def __init__(
        self,
        model: str = "bge-m3",
        base_url: str = "http://127.0.0.1:11434",
        dim: int = 1024,
        timeout: float = 60.0,
        cpu: bool = True,
    ) -> None:
        self.model = model
        self.model_id = f"ollama:{model}"
        self.base_url = base_url.rstrip("/")
        self.dim = dim
        self.timeout = timeout
        # 8GB GPU에서는 LLM과 VRAM을 다투지 않도록 임베딩을 CPU에서 돌린다 (짧은 문장은 0.3초 안팎)
        self.options = {"num_gpu": 0} if cpu else {}

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = httpx.post(
            f"{self.base_url}/api/embed",
            json={
                "model": self.model,
                "input": texts,
                "keep_alive": "30m",
                "options": self.options,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()["embeddings"]
