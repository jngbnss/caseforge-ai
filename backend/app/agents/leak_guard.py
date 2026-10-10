"""누설 가드: LLM 응답이 NPC의 지식 범위를 벗어나는지 규칙으로 검사한다."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.agents.knowledge_scope import Scope
from app.agents.schemas import NpcReply
from app.core.llm.markers import NPC_ID_PREFIX, QUESTION_OPEN
from case_validator import CaseBible

PROMPT_MARKERS = ("[fact-", "[lie-", NPC_ID_PREFIX, QUESTION_OPEN, "## 알고 있는", "## 유지해야")


@dataclass
class GuardResult:
    violations: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations


def check_reply(reply: NpcReply, scope: Scope, bible: CaseBible, question: str) -> GuardResult:
    result = GuardResult()
    allowed = scope.allowed_fact_ids

    for fid in reply.revealed_fact_ids:
        if fid not in allowed:
            result.violations.append(f"unauthorized_fact:{fid}")
    for lid in reply.used_lie_ids:
        if lid not in scope.active_lie_ids:
            result.violations.append(f"inactive_lie:{lid}")

    # 범위 밖 사실의 카나리 키워드. 질문이나 범위 안 문장에 이미 있는 단어는 예외로 둔다.
    exempt = question + "\n" + scope.allowed_text()
    for fact in bible.facts:
        if fact.fact_id in allowed:
            continue
        for keyword in fact.canary_keywords:
            if keyword in reply.answer and keyword not in exempt:
                result.violations.append(f"canary:{fact.fact_id}:{keyword}")

    if any(marker in reply.answer for marker in PROMPT_MARKERS):
        result.violations.append("prompt_leak")
    return result
