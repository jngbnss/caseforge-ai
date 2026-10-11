"""LLM 모순 판정. 규칙 판정(contradiction.py)을 보조하며 결과는 source='llm'으로 따로 저장한다.

심문 응답을 보낸 뒤 비동기로 돈다. 판정자에게는 공개된 정보만 준다: 그 NPC의 진술과 플레이어가 그 NPC에게
제시한 증거의 설명. Case Bible의 사실·거짓말·정답은 프롬프트에 넣지 않는다.
모델 출력은 Pydantic으로 검증한 뒤, 실제로 있는 진술 턴·제시한 증거를 가리키고 양쪽 원문을 글자 그대로
인용한 판정만 남긴다 (LLM 판정 결과만 믿지 않는다).
"""

from __future__ import annotations

import logging
import time
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.db import DialogueRow, LlmContradictionRow
from app.core.llm.markers import (
    JUDGE_CHECK,
    JUDGE_EVIDENCE,
    JUDGE_NEW_STATEMENT,
    JUDGE_PREVIOUS,
    NPC_ID_PREFIX,
)
from app.core.llm.ports import LLMPort, Message
from app.core.llm.structured import generate_structured
from app.core.session import GameSession

log = logging.getLogger(__name__)

MIN_CONFIDENCE = 0.6
PREVIOUS_STATEMENTS = 6

ContradictionType = Literal["time", "location", "possession", "statement"]


class ContradictionFinding(BaseModel):
    type: ContradictionType
    statement_turns: list[int] = Field(min_length=1, max_length=4)
    """모순에 관련된 진술의 턴 번호. 새 진술의 턴을 반드시 포함해야 저장한다."""
    evidence_ids: list[str] = Field(max_length=4)
    """관련된 제시 증거 ID. 필수 필드로 두어 모델이 빠뜨리지 않게 한다 (없으면 빈 목록)."""
    quotes: list[str] = Field(min_length=2, max_length=4)
    """충돌하는 양쪽에서 글자 그대로 옮긴 짧은 구절. 코드가 원문에 실제로 있는지 확인한다."""
    confidence: float = Field(ge=0, le=1)
    explanation: str = Field(min_length=1, max_length=200)


class ContradictionJudgement(BaseModel):
    findings: list[ContradictionFinding] = Field(default_factory=list, max_length=4)


class ContradictionCheck(BaseModel):
    """판정 하나를 다시 확인한다 (EXP-003). 양쪽 주장을 먼저 글자 그대로 옮기게 해 성급한 판정을 거른다.

    '둘 다 참인 상황을 먼저 써 보라'는 방식은 8B 모델이 '계속'·'한 번도'를 무시한 억지 상황을 만들어
    모든 판정을 버렸다 (재현율 0). 그래서 주장을 옮긴 뒤 판정하게 한다.
    """

    claim_a: str = Field(max_length=300)
    claim_b: str = Field(max_length=300)
    same_person_time_place: bool
    """두 내용이 같은 사람의 같은(겹치는) 시간대에 대한 것인가."""
    contradiction: bool


UNCONFIRMED = ContradictionCheck(
    claim_a="", claim_b="", same_person_time_place=False, contradiction=False
)


JUDGE_SYSTEM = (
    "너는 추리 게임의 기록 담당관이다. 한 용의자의 새 진술이 그 사람의 이전 진술이나, "
    "탐정이 그 사람에게 보여 준 증거와 **둘 다 참일 수 없을 만큼** 충돌하는지 판정한다.\n"
    "- 충돌의 종류: time(시각), location(장소), possession(소지품·물건), statement(앞뒤 진술끼리 불일치)\n"
    "- 모순이 아닌 것: 같은 주장을 다른 말로 반복함, 서로 다른 주제를 말함, 질문을 피함, 말투나 감정이 달라짐.\n"
    "- 증거 때문에 충돌하면 그 증거 ID를 evidence_ids에 반드시 넣는다. "
    "진술끼리만 충돌할 때만 statement 종류를 쓴다.\n"
    "- quotes에는 충돌하는 양쪽(진술 또는 증거 설명)에서 **글자 그대로** 옮긴 짧은 구절을 하나씩 넣는다.\n"
    "- 아래 목록에 있는 진술과 증거만 근거로 쓴다. 애매하면 판정하지 않는다. "
    "확신이 클 때만 confidence를 0.9 이상으로 쓴다.\n"
    "- statement_turns에는 관련된 진술의 턴 번호를 쓴다. 새 진술의 턴을 꼭 넣는다.\n"
    "- explanation은 한국어 한 문장으로, 무엇과 무엇이 맞지 않는지 쓴다.\n"
    "- 충돌이 없으면 findings를 빈 목록으로 둔다. 대부분의 진술에는 모순이 없다.\n"
    'JSON 하나로만 답한다: {"findings": [{"type": str, "statement_turns": [int], '
    '"evidence_ids": [str], "quotes": [str], "confidence": 0~1, "explanation": str}]}'
)


CHECK_SYSTEM = (
    "너는 추리 게임의 검토관이다. 다른 담당관이 아래 두 내용을 모순이라고 판정했다. "
    "판정이 맞는지 다시 확인한다.\n"
    "- claim_a, claim_b에 각 내용이 주장하는 것을 시각·장소·'계속/한 번도/내내' 같은 말까지 빠짐없이 옮긴다.\n"
    "- same_person_time_place: 두 내용이 같은 사람의 같은 시각(또는 겹치는 시간대)에 대한 것이면 true. "
    "증거가 다른 사람의 기록이거나 시간대가 겹치지 않으면 false.\n"
    "- contradiction: 두 주장을 글자 그대로 받아들였을 때 둘 다 참일 수 없으면 true. "
    "시각은 앞뒤를 정확히 비교한다 (21:07에 나가 21:08에 그 근처에 있는 것은 모순이 아니다).\n"
    'JSON 하나로만 답한다: {"claim_a": str, "claim_b": str, '
    '"same_person_time_place": bool, "contradiction": bool}'
)


def build_check_messages(
    npc_name: str, finding: ContradictionFinding, texts: dict[int, str], evidence: dict[str, str]
) -> list[Message]:
    lines = [f"용의자: {npc_name}", JUDGE_CHECK]
    lines += [f"- [진술 turn {t}] {texts[t]}" for t in sorted(set(finding.statement_turns))]
    lines += [f"- [증거 {e}] {evidence[e]}" for e in finding.evidence_ids]
    lines.append(f"판정 이유: {finding.explanation}")
    return [Message("system", CHECK_SYSTEM), Message("user", "\n".join(lines))]


def build_judge_messages(
    npc_id: str,
    npc_name: str,
    new: tuple[int, str],
    previous: list[tuple[int, str]],
    evidence: list[tuple[str, str, str]],
) -> list[Message]:
    lines = [f"{NPC_ID_PREFIX}{npc_id}", f"용의자: {npc_name}", JUDGE_NEW_STATEMENT]
    lines.append(f"- [turn {new[0]}] {new[1]}")
    lines.append(JUDGE_PREVIOUS)
    lines += [f"- [turn {t}] {text}" for t, text in previous] or ["- (없음)"]
    lines.append(JUDGE_EVIDENCE)
    lines += [f"- [{eid}] {name}: {desc}" for eid, name, desc in evidence] or ["- (없음)"]
    return [Message("system", JUDGE_SYSTEM), Message("user", "\n".join(lines))]


def _compact(text: str) -> str:
    return "".join(text.split()).strip("\"'“”‘’.,…")


def resolve_evidence(
    finding: ContradictionFinding, new_turn: int, texts: dict[int, str], evidence: dict[str, str]
) -> ContradictionFinding:
    """진술에 없는 인용이 제시 증거의 원문과 글자 그대로 맞으면 그 증거 ID를 붙인다.

    모델이 증거를 정확히 인용하고도 evidence_ids를 비워 두는 경우가 많다 (EXP-001).
    """
    statements = [_compact(texts[t]) for t in finding.statement_turns if t in texts]
    statements.append(_compact(texts.get(new_turn, "")))
    ids = list(finding.evidence_ids)
    for quote in (_compact(q) for q in finding.quotes):
        if not quote or any(quote in st for st in statements):
            continue
        for eid, text in evidence.items():
            if quote in _compact(text) and eid not in ids:
                ids.append(eid)
    return (
        finding if ids == finding.evidence_ids else finding.model_copy(update={"evidence_ids": ids})
    )


def accept(
    finding: ContradictionFinding,
    new_turn: int,
    texts: dict[int, str],
    evidence: dict[str, str],
) -> bool:
    """모델이 지어낸 턴·증거·인용을 가리키거나 확신이 낮은 판정은 버린다.

    texts: 턴 → 진술 원문, evidence: 제시한 증거 ID → 이름과 설명 원문.
    """
    if finding.confidence < MIN_CONFIDENCE or new_turn not in finding.statement_turns:
        return False
    if not set(finding.statement_turns) <= set(texts):
        return False
    if not set(finding.evidence_ids) <= set(evidence):
        return False
    # 새 진술 하나만으로는 모순이 아니다: 다른 진술이나 증거가 있어야 한다.
    if len(set(finding.statement_turns)) < 2 and not finding.evidence_ids:
        return False
    # 인용은 판정이 가리킨 원문에 그대로 있어야 하고, 새 진술과 반대편 양쪽에서 나와야 한다.
    new_text = _compact(texts[new_turn])
    others = [_compact(texts[t]) for t in finding.statement_turns if t != new_turn]
    others += [_compact(evidence[e]) for e in finding.evidence_ids]
    quotes = [q for q in (_compact(q) for q in finding.quotes) if q]
    if not quotes or any(not (q in new_text or any(q in o for o in others)) for q in quotes):
        return False
    return any(q in new_text for q in quotes) and any(q in o for q in quotes for o in others)


async def confirm(
    llm: LLMPort,
    npc_name: str,
    finding: ContradictionFinding,
    texts: dict[int, str],
    evidence: dict[str, str],
) -> bool:
    """코드 검사를 통과한 판정을 모델이 한 번 더 확인한다. 검증 실패면 판정을 버린다 (보조 판정이므로 보수적으로)."""
    result = await generate_structured(
        llm,
        build_check_messages(npc_name, finding, texts, evidence),
        ContradictionCheck,
        fallback=UNCONFIRMED,
        temperature=0.0,
    )
    return result.value.contradiction and result.value.same_person_time_place


async def judge_turn(
    llm: LLMPort,
    db: DbSession,
    session: GameSession,
    npc_id: str,
    turn_no: int,
    *,
    verify: bool = False,
) -> list[LlmContradictionRow]:
    """새 진술 한 턴을 판정하고, 새로 찾은 모순만 저장해 돌려준다."""
    bible = session.bible
    suspect = bible.suspect(npc_id)
    if suspect is None:
        return []
    rows = db.scalars(
        select(DialogueRow)
        .where(
            DialogueRow.session_id == session.id,
            DialogueRow.npc_id == npc_id,
            DialogueRow.role == "npc",
        )
        .order_by(DialogueRow.id)
    ).all()
    by_turn = {r.turn: r.text for r in rows}
    if turn_no not in by_turn:
        return []
    previous = [(t, text) for t, text in by_turn.items() if t < turn_no][-PREVIOUS_STATEMENTS:]
    presented = [
        e for eid in session.state.presented_to(npc_id) if (e := bible.evidence_by_id(eid))
    ]
    if not previous and not presented:
        return []  # 비교할 대상이 없으면 모델을 부르지 않는다

    messages = build_judge_messages(
        npc_id,
        suspect.name,
        (turn_no, by_turn[turn_no]),
        previous,
        [(e.evidence_id, e.name, e.description) for e in presented],
    )
    started = time.perf_counter()
    result = await generate_structured(
        llm, messages, ContradictionJudgement, fallback=ContradictionJudgement(), temperature=0.0
    )
    latency_ms = (time.perf_counter() - started) * 1000

    texts = dict(previous) | {turn_no: by_turn[turn_no]}
    shown = {e.evidence_id: f"{e.name} {e.description}" for e in presented}
    existing = {
        (tuple(c.statement_turns), tuple(c.evidence_ids))
        for c in db.scalars(
            select(LlmContradictionRow).where(
                LlmContradictionRow.session_id == session.id, LlmContradictionRow.npc_id == npc_id
            )
        )
    }
    new: list[LlmContradictionRow] = []
    for f in result.value.findings:
        f = resolve_evidence(f, turn_no, texts, shown)
        if not accept(f, turn_no, texts, shown):
            log.info("LLM 모순 판정 기각: %s", f.model_dump())
            continue
        key = (tuple(sorted(set(f.statement_turns))), tuple(sorted(set(f.evidence_ids))))
        if key in existing:
            continue
        if verify and not await confirm(llm, suspect.name, f, texts, shown):
            log.info("LLM 모순 판정 재확인에서 기각: %s", f.model_dump())
            continue
        existing.add(key)
        new.append(
            LlmContradictionRow(
                session_id=session.id,
                npc_id=npc_id,
                statement_turn=turn_no,
                statement_turns=list(key[0]),
                evidence_ids=list(key[1]),
                type=f.type,
                confidence=round(f.confidence, 2),
                explanation=f.explanation,
                model_id=result.raw.model_id if result.raw else llm.model_id,
                latency_ms=round(latency_ms, 1),
            )
        )
    if new:
        db.add_all(new)
        db.commit()
    return new
