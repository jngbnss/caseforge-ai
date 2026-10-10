"""스트리밍 중인 JSON 원문에서 "answer" 문자열 값만 조금씩 꺼낸다."""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable

from app.agents.knowledge_scope import Scope
from app.agents.leak_guard import holdback, id_violations, text_violations
from case_validator import CaseBible

_KEY = re.compile(r'"answer"\s*:\s*"')
_ESCAPES = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t"}


_IDS = re.compile(r'"(revealed_fact_ids|used_lie_ids)"\s*:\s*\[([^\]]*)\]')


class AnswerExtractor:
    """feed()에 원문 조각을 넣으면 그동안 새로 확정된 answer 글자를 돌려준다."""

    def __init__(self) -> None:
        self.raw = ""
        self.start: int | None = None
        self.pos = 0
        self.done = False

    def feed(self, chunk: str) -> str:
        self.raw += chunk
        if self.done:
            return ""
        if self.start is None:
            match = _KEY.search(self.raw)
            if not match:
                return ""
            self.start = self.pos = match.end()
        out: list[str] = []
        raw = self.raw
        while self.pos < len(raw):
            ch = raw[self.pos]
            if ch == '"':
                self.done = True
                break
            if ch != "\\":
                out.append(ch)
                self.pos += 1
                continue
            if self.pos + 1 >= len(raw):
                break  # 이스케이프가 다음 조각에서 끝난다
            esc = raw[self.pos + 1]
            if esc == "u":
                if self.pos + 6 > len(raw):
                    break
                out.append(json.loads(f'"{raw[self.pos : self.pos + 6]}"'))
                self.pos += 6
            else:
                out.append(_ESCAPES.get(esc, esc))
                self.pos += 2
        return "".join(out)


class GuardedStream:
    """스트리밍 답변을 가드가 허용한 만큼만 내보낸다.

    - 답변보다 먼저 나오는 근거 ID가 범위 밖이면 아무것도 내보내지 않는다.
    - 답변 글자는 키워드 검사를 통과한 부분만, 끝의 몇 글자는 붙잡아 두었다가 내보낸다.
    - 위반을 발견하면 그 뒤로는 멈춘다. 최종 답변은 일반 가드가 다시 판정한다.
    """

    def __init__(
        self,
        scope: Scope,
        bible: CaseBible,
        question: str,
        emit: Callable[[str], Awaitable[None]],
    ) -> None:
        self.scope = scope
        self.bible = bible
        self.question = question
        self.emit = emit
        self.extractor = AnswerExtractor()
        self.answer = ""
        self.sent = 0
        self.blocked = False
        self.hold = holdback(bible)

    @property
    def raw(self) -> str:
        return self.extractor.raw

    async def feed(self, chunk: str) -> None:
        before_answer = self.extractor.start is None
        self.answer += self.extractor.feed(chunk)
        if self.blocked or self.extractor.start is None:
            return
        if before_answer:
            prefix = self.raw[: self.extractor.start]
            ids = {key: json.loads(f"[{value}]") for key, value in _IDS.findall(prefix)}
            revealed = ids.get("revealed_fact_ids", [])
            if id_violations(revealed, ids.get("used_lie_ids", []), self.scope):
                self.blocked = True
                return
        if text_violations(self.answer, self.scope, self.bible, self.question):
            self.blocked = True
            return
        done = self.extractor.done
        safe = len(self.answer) if done else max(0, len(self.answer) - self.hold)
        if safe > self.sent:
            await self.emit(self.answer[self.sent : safe])
            self.sent = safe

    async def finish(self) -> None:
        """스트림이 끝나면 붙잡아 둔 나머지를 내보낸다 (위반이 없을 때만)."""
        if self.blocked or self.sent >= len(self.answer):
            return
        if not text_violations(self.answer, self.scope, self.bible, self.question):
            await self.emit(self.answer[self.sent :])
            self.sent = len(self.answer)
