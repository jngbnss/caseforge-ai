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
    result = GuardResult(id_violations(reply.revealed_fact_ids, reply.used_lie_ids, scope))
    result.violations += text_violations(reply.answer, scope, bible, question)
    return result


def id_violations(revealed: list[str], used_lies: list[str], scope: Scope) -> list[str]:
    out = [f"unauthorized_fact:{fid}" for fid in revealed if fid not in scope.allowed_fact_ids]
    out += [f"inactive_lie:{lid}" for lid in used_lies if lid not in scope.active_lie_ids]
    return out


def text_violations(text: str, scope: Scope, bible: CaseBible, question: str) -> list[str]:
    """범위 밖 사실의 카나리 키워드와 프롬프트 표시. 질문이나 범위 안 문장에 이미 있는 단어는 예외."""
    out: list[str] = []
    allowed = scope.allowed_fact_ids
    exempt = question + "\n" + scope.allowed_text()
    for fact in bible.facts:
        if fact.fact_id in allowed:
            continue
        for keyword in fact.canary_keywords:
            if keyword in text and keyword not in exempt:
                out.append(f"canary:{fact.fact_id}:{keyword}")
    if any(marker in text for marker in PROMPT_MARKERS):
        out.append("prompt_leak")
    return out


def holdback(bible: CaseBible) -> int:
    """스트리밍 때 내보내지 않고 붙잡아 둘 글자 수 (비밀 키워드가 반쯤 나가지 않게).

    프롬프트 표시는 사건 비밀이 아니므로 기준에서 뺀다. 넣으면 화면 글자가 16자씩 늦게 나온다.
    """
    lengths = [len(k) for f in bible.facts for k in f.canary_keywords]
    return max(lengths, default=1) - 1
