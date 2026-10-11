"""누설 가드: LLM 응답이 NPC의 지식 범위를 벗어나는지 규칙으로 검사한다."""

from __future__ import annotations

import re
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
    out += anchor_violations(text, scope, bible)
    if any(marker in text for marker in PROMPT_MARKERS):
        out.append("prompt_leak")
    return out


_TIME = re.compile(r"\d{1,2}:\d{2}")
_SENTENCE = re.compile(r"[^.!?。…\n]+")
_JOSA = (
    "에서", "으로", "부터", "까지", "에게", "한테",
    "을", "를", "이", "가", "은", "는", "에", "의", "로", "와", "과", "도",
)  # fmt: skip


def _nouns(content: str, exclude: set[str]) -> set[str]:
    """사실 문장에서 장소·물건 단어를 거칠게 뽑는다 (시각·숫자·동사·이름 제외)."""
    out: set[str] = set()
    for token in content.replace(".", " ").replace(",", " ").split():
        if _TIME.fullmatch(token) or token.endswith("다"):
            continue
        for josa in _JOSA:
            if token.endswith(josa) and len(token) > len(josa) + 1:
                token = token[: -len(josa)]
                break
        if len(token) >= 2 and not token[0].isdigit() and token not in exclude:
            out.add(token)
    return out


def anchor_violations(text: str, scope: Scope, bible: CaseBible) -> list[str]:
    """NPC가 숨겨야 하는 사실의 '시각 + 장소·물건'을 한 문장에서 같이 말하면 위반 (EXP-002).

    카나리는 질문에 있던 단어를 예외로 두므로, 플레이어가 정답 추측("21:10에 사물함에서…")을 질문에 넣으면
    NPC가 그대로 시인해도 통과했다. 이 규칙은 질문을 예외로 두지 않는다. 같은 조합이 말해도 되는 문장
    (범위 안 사실·제시 증거·유지 중인 거짓말) 한 곳에 같이 있으면 예외다.
    """
    names = {s.name for s in bible.suspects}
    allowed = [s for s in scope.allowed_text().split("\n") if s]
    out: list[str] = []
    for fid in sorted(scope.withheld_fact_ids):
        fact = bible.fact(fid)
        if fact is None:
            continue
        times = set(_TIME.findall(fact.content))
        nouns = _nouns(fact.content, names)
        for sentence in _SENTENCE.findall(text):
            hit_times = [t for t in times if t in sentence]
            hit_nouns = [n for n in nouns if n in sentence]
            pairs = [(t, n) for t in hit_times for n in hit_nouns]
            if any(not any(t in a and n in a for a in allowed) for t, n in pairs):
                out.append(f"anchor:{fid}")
                break
    return out


def holdback(bible: CaseBible) -> int:
    """스트리밍 때 내보내지 않고 붙잡아 둘 글자 수 (비밀 키워드가 반쯤 나가지 않게).

    프롬프트 표시는 사건 비밀이 아니므로 기준에서 뺀다. 넣으면 화면 글자가 16자씩 늦게 나온다.
    """
    lengths = [len(k) for f in bible.facts for k in f.canary_keywords]
    return max(lengths, default=1) - 1
