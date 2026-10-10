"""게임 세션: 고정된 Case Bible + 변하는 플레이 상태."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from app.cases.registry import get_case
from app.core.db import SessionRow
from case_validator import CaseBible, PlayState
from case_validator.conditions import MAX_TRUST

DEFAULT_EMOTION = "calm"


class DeductionRecord(BaseModel):
    culprit_id: str
    motive_id: str
    method_id: str
    evidence_ids: list[str]
    narrative: str = ""
    scores: dict[str, int]
    total: int
    flags: dict[str, bool | list[str]]


class GameState(BaseModel):
    collected: list[str] = Field(default_factory=list)
    solved: list[str] = Field(default_factory=list)
    presented: dict[str, list[str]] = Field(default_factory=dict)
    trust: dict[str, int] = Field(default_factory=dict)
    emotion: dict[str, str] = Field(default_factory=dict)
    puzzle_attempts: dict[str, int] = Field(default_factory=dict)
    hints_used: dict[str, int] = Field(default_factory=dict)
    turns: dict[str, int] = Field(default_factory=dict)
    deduction: DeductionRecord | None = None

    def play_state(self) -> PlayState:
        return PlayState(
            collected=set(self.collected),
            solved=set(self.solved),
            presented={k: set(v) for k, v in self.presented.items()},
            trust=dict(self.trust),
        )

    def presented_to(self, npc_id: str) -> list[str]:
        return self.presented.get(npc_id, [])

    def add_trust(self, npc_id: str, delta: int) -> int:
        value = max(0, min(MAX_TRUST, self.trust.get(npc_id, 0) + delta))
        self.trust[npc_id] = value
        return value

    def next_turn(self, npc_id: str) -> int:
        self.turns[npc_id] = self.turns.get(npc_id, 0) + 1
        return self.turns[npc_id]


class CaseChangedError(Exception):
    """세션이 시작된 뒤 사건 데이터가 바뀌었다."""


class SessionNotFoundError(Exception):
    pass


@dataclass
class GameSession:
    id: str
    bible: CaseBible
    case_sha256: str
    state: GameState


class SessionStore:
    def __init__(self, db: DbSession) -> None:
        self.db = db

    def create(self, case_id: str) -> GameSession:
        loaded = get_case(case_id)
        state = GameState(
            emotion={s.suspect_id: DEFAULT_EMOTION for s in loaded.bible.suspects},
            trust={s.suspect_id: 0 for s in loaded.bible.suspects},
        )
        row = SessionRow(
            id=str(uuid.uuid4()),
            case_id=case_id,
            case_sha256=loaded.sha256,
            state=state.model_dump(mode="json"),
        )
        self.db.add(row)
        self.db.commit()
        return GameSession(row.id, loaded.bible, loaded.sha256, state)

    def get(self, session_id: str) -> GameSession:
        row = self.db.get(SessionRow, session_id)
        if row is None:
            raise SessionNotFoundError(session_id)
        loaded = get_case(row.case_id)
        if loaded.sha256 != row.case_sha256:
            raise CaseChangedError(f"{row.case_id} 사건 데이터가 세션 시작 후 바뀌었다")
        return GameSession(row.id, loaded.bible, row.case_sha256, GameState(**row.state))

    def save(self, session: GameSession) -> None:
        row = self.db.get(SessionRow, session.id)
        if row is None:
            raise SessionNotFoundError(session.id)
        row.state = session.state.model_dump(mode="json")
        self.db.commit()
