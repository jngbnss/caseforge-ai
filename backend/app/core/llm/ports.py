"""모델 호출 포트. 모든 LLM 호출은 이 인터페이스를 거친다 (Mock, Ollama, llama.cpp 교체 가능)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


@dataclass(frozen=True)
class Message:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass(frozen=True)
class LLMRaw:
    """모델이 돌려준 원문과 계측값. 파싱과 검증은 structured.generate_structured가 한다."""

    text: str
    model_id: str
    latency_ms: float = 0.0
    usage: Usage = field(default_factory=Usage)


class LLMPort(Protocol):
    model_id: str

    async def complete(
        self,
        messages: list[Message],
        *,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 512,
    ) -> LLMRaw: ...

    def stream(self, messages: list[Message]) -> AsyncIterator[str]: ...
