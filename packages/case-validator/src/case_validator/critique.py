"""L01: LLM 비평 인터페이스.

LLM 비평은 경고만 낼 수 있고 통과/실패 판정에는 쓰지 않는다. 구현은 백엔드의 LLM 어댑터가 담당한다.
"""

from __future__ import annotations

from typing import Protocol

from .report import Issue
from .schema import CaseBible


class CaseCritic(Protocol):
    def critique(self, bible: CaseBible) -> list[Issue]: ...


def as_warnings(issues: list[Issue]) -> list[Issue]:
    return [Issue("L01", "warning", i.message, i.refs) for i in issues]
