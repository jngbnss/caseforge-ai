"""llama.cpp 어댑터 (비교 실험용, 미구현).

TODO: llama.cpp 서버(`llama-server`)의 OpenAI 호환 `/v1/chat/completions`에 붙는다.
- 구조화 출력은 JSON 스키마 대신 GBNF 문법(`grammar`) 또는 `response_format`으로 강제한다.
- `complete()`는 LLMRaw(원문, 지연, 토큰)를, `stream()`은 텍스트 조각을 낸다 (`ports.LLMPort`).
- 같은 평가셋(`evals.run`)으로 Ollama와 지연·구조화 출력 성공률을 비교해 `docs/model-selection.md`에 기록한다.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from app.core.llm.ports import LLMRaw, Message


class LlamaCppLLM:
    def __init__(self, model: str, base_url: str = "http://127.0.0.1:8080") -> None:
        self.model_id = f"llamacpp:{model}"
        self.base_url = base_url

    async def complete(
        self,
        messages: list[Message],
        *,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 512,
    ) -> LLMRaw:
        raise NotImplementedError("llama.cpp 어댑터는 아직 구현하지 않았다 (비교 실험용 TODO)")

    def stream(
        self,
        messages: list[Message],
        *,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 512,
    ) -> AsyncIterator[str]:
        raise NotImplementedError("llama.cpp 어댑터는 아직 구현하지 않았다 (비교 실험용 TODO)")
