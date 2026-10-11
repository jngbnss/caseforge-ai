"""LLM port. Every model call goes through `StructuredLLM.generate`.

`generate` validates the reply with Pydantic, re-asks once with the validation error,
and falls back to a caller-supplied safe default (logged) if the second reply fails too.
"""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Literal, Protocol

from pydantic import BaseModel, ValidationError

log = logging.getLogger(__name__)


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def __iadd__(self, other: Usage) -> Usage:
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens
        return self


@dataclass
class LLMResult[T: BaseModel]:
    parsed: T
    raw_text: str
    model_id: str
    usage: Usage = field(default_factory=Usage)
    latency_ms: float = 0.0
    calls: int = 1
    validation_failures: int = 0
    fallback_used: bool = False


@dataclass
class ChatReply:
    text: str
    usage: Usage = field(default_factory=Usage)


class LLMPort(Protocol):
    model_id: str

    async def generate[T: BaseModel](
        self,
        messages: list[Message],
        schema: type[T],
        *,
        default: T | None = None,
        temperature: float = 0.3,
        max_tokens: int = 512,
    ) -> LLMResult[T]: ...

    def stream(
        self,
        messages: list[Message],
        schema: type[BaseModel] | None = None,
    ) -> AsyncIterator[str]: ...


class LLMOutputError(RuntimeError):
    """Both attempts failed validation and no safe default was given."""


class StructuredLLM(ABC):
    """Shared validate → re-ask once → safe default logic. Adapters implement `_chat`."""

    model_id: str = "unknown"

    @abstractmethod
    async def _chat(
        self,
        messages: list[Message],
        json_schema: dict | None,
        temperature: float,
        max_tokens: int,
    ) -> ChatReply: ...

    @abstractmethod
    def stream(
        self,
        messages: list[Message],
        schema: type[BaseModel] | None = None,
    ) -> AsyncIterator[str]: ...

    async def generate[T: BaseModel](
        self,
        messages: list[Message],
        schema: type[T],
        *,
        default: T | None = None,
        temperature: float = 0.3,
        max_tokens: int = 512,
    ) -> LLMResult[T]:
        started = time.perf_counter()
        usage = Usage()
        convo = list(messages)
        failures = 0
        raw = ""
        for attempt in range(2):
            reply = await self._chat(convo, schema.model_json_schema(), temperature, max_tokens)
            usage += reply.usage
            raw = reply.text
            try:
                parsed = schema.model_validate_json(_strip_fences(raw))
            except ValidationError as exc:
                failures += 1
                log.warning("LLM output failed validation (attempt %d): %s", attempt + 1, exc)
                convo = [
                    *convo,
                    Message(role="assistant", content=raw),
                    Message(
                        role="user",
                        content="이전 출력이 JSON 스키마 검증에 실패했다. 오류: "
                        f"{_short_errors(exc)}. 스키마에 맞는 JSON 하나만 다시 출력하라.",
                    ),
                ]
                continue
            return LLMResult(
                parsed=parsed,
                raw_text=raw,
                model_id=self.model_id,
                usage=usage,
                latency_ms=(time.perf_counter() - started) * 1000,
                calls=attempt + 1,
                validation_failures=failures,
            )
        if default is None:
            raise LLMOutputError(f"{self.model_id}: output failed validation twice")
        log.error("LLM output failed validation twice; using safe default")
        return LLMResult(
            parsed=default,
            raw_text=raw,
            model_id=self.model_id,
            usage=usage,
            latency_ms=(time.perf_counter() - started) * 1000,
            calls=2,
            validation_failures=failures,
            fallback_used=True,
        )


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.removeprefix("json").strip()
    return text


def _short_errors(exc: ValidationError) -> str:
    return json.dumps(
        [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()[:5]], ensure_ascii=False
    )
