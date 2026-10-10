"""LLM 출력을 Pydantic으로 검증한다. 실패하면 1회 재요청, 그래도 실패하면 안전 기본값."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from pydantic import BaseModel, ValidationError

from app.core.llm.ports import LLMPort, LLMRaw, Message

log = logging.getLogger(__name__)

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


@dataclass
class StructuredResult[T: BaseModel]:
    value: T
    raw: LLMRaw | None
    attempts: int
    fallback_used: bool
    errors: list[str] = field(default_factory=list)


def _strip(text: str) -> str:
    return _FENCE.sub("", text.strip())


async def generate_structured[T: BaseModel](
    llm: LLMPort,
    messages: list[Message],
    schema: type[T],
    *,
    fallback: T,
    temperature: float = 0.3,
    max_tokens: int = 512,
) -> StructuredResult[T]:
    errors: list[str] = []
    raw: LLMRaw | None = None
    history = list(messages)
    for attempt in (1, 2):
        raw = await llm.complete(
            history,
            json_schema=schema.model_json_schema(),
            temperature=temperature,
            max_tokens=max_tokens,
        )
        try:
            value = schema.model_validate_json(_strip(raw.text))
            return StructuredResult(value, raw, attempt, False, errors)
        except ValidationError as exc:
            errors.append(exc.errors(include_url=False, include_input=False).__repr__()[:500])
            history += [
                Message("assistant", raw.text),
                Message(
                    "user",
                    "직전 출력이 JSON 스키마에 맞지 않는다. 스키마에 맞는 JSON만 다시 출력하라.",
                ),
            ]
    log.warning("구조화 출력 검증 2회 실패, 기본값 사용 (model=%s)", raw.model_id if raw else "?")
    return StructuredResult(fallback, raw, 2, True, errors)
