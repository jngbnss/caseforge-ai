"""규칙 기반 모순 탐지.

NPC가 Case Bible에 정의된 거짓말을 진술했고, 그 거짓말을 무너뜨리는 증거를 플레이어가 확보했으면 모순이다.
LLM 판정(4단계)은 source='llm'으로 따로 저장한다.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.db import ContradictionRow, DialogueRow
from app.core.session import GameSession
from case_validator import CaseBible
from case_validator.schema import Lie


def contradiction_type(bible: CaseBible, lie: Lie) -> str:
    fact = bible.fact(lie.contradicts_fact_id)
    if fact is None:
        return "statement"
    if fact.location_id:
        return "location"
    if fact.time:
        return "time"
    return "statement"


def detect_rule_contradictions(db: DbSession, session: GameSession) -> list[ContradictionRow]:
    """새로 생긴 모순만 저장하고 돌려준다. 같은 (NPC, 거짓말, 증거)는 한 번만 기록한다."""
    bible = session.bible
    lies = {lie.lie_id: lie for lie in bible.lies}
    collected = set(session.state.collected)

    first_turn: dict[tuple[str, str], int] = {}
    rows = db.scalars(
        select(DialogueRow)
        .where(DialogueRow.session_id == session.id, DialogueRow.role == "npc")
        .order_by(DialogueRow.id)
    )
    for row in rows:
        for lie_id in row.used_lie_ids:
            first_turn.setdefault((row.npc_id, lie_id), row.turn)

    existing = {
        (c.npc_id, c.lie_id, c.evidence_id)
        for c in db.scalars(
            select(ContradictionRow).where(
                ContradictionRow.session_id == session.id, ContradictionRow.source == "rule"
            )
        )
    }
    new: list[ContradictionRow] = []
    for (npc_id, lie_id), turn in first_turn.items():
        lie = lies.get(lie_id)
        if lie is None:
            continue
        for evidence_id in lie.breaks_on:
            key = (npc_id, lie_id, evidence_id)
            if evidence_id in collected and key not in existing:
                new.append(
                    ContradictionRow(
                        session_id=session.id,
                        npc_id=npc_id,
                        lie_id=lie_id,
                        statement_turn=turn,
                        evidence_id=evidence_id,
                        type=contradiction_type(bible, lie),
                        source="rule",
                    )
                )
    if new:
        db.add_all(new)
        db.commit()
    return new
