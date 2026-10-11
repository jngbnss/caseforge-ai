"""Authoritative per-session game state. The client only ever sees projections of it."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from case_validator import CaseBible, ConditionState
from pydantic import BaseModel, Field

Emotion = Literal["calm", "nervous", "defensive", "ashamed", "angry", "resigned", "shaken"]
INITIAL_TRUST = 1


class NpcState(BaseModel):
    trust: int = INITIAL_TRUST
    emotion: Emotion = "calm"
    presented: list[str] = Field(default_factory=list)
    broken_lies: list[str] = Field(default_factory=list)


class Turn(BaseModel):
    turn_id: str
    npc_id: str
    question: str
    answer: str
    emotion: Emotion
    revealed_fact_ids: list[str] = Field(default_factory=list)
    asserted_lie_ids: list[str] = Field(default_factory=list)
    used_fact_ids: list[str] = Field(default_factory=list)  # retrieved grounding
    trust_delta: int = 0
    guard_blocked: bool = False
    contradiction_detected: bool = False
    pinned: bool = False


class Contradiction(BaseModel):
    contradiction_id: str
    npc_id: str
    type: Literal["time", "location", "possession", "other"]
    statement_ids: list[str]
    evidence_ids: list[str]
    source: Literal["rule", "llm"]
    confidence: float = 1.0
    explanation: str = ""
    lie_id: str | None = None  # internal, never serialized to clients


class DeductionSubmission(BaseModel):
    culprit_id: str
    motive_id: str
    method_id: str
    evidence_ids: list[str] = Field(default_factory=list)
    narrative: str = ""


class DeductionScore(BaseModel):
    culprit: int
    motive: int
    method: int
    evidence: int
    total: int


class DeductionResult(BaseModel):
    submission: DeductionSubmission
    score: DeductionScore
    flags: list[str] = Field(default_factory=list)
    wrong_links: list[str] = Field(default_factory=list)
    feedback: dict | None = None  # LLM reading of the narrative (feedback only, no points)
    submitted_at: datetime


class GameState(BaseModel):
    session_id: str
    case_id: str
    case_sha256: str
    created_at: datetime
    collected: list[str] = Field(default_factory=list)
    solved: list[str] = Field(default_factory=list)
    puzzle_attempts: dict[str, int] = Field(default_factory=dict)
    hints_used: dict[str, int] = Field(default_factory=dict)
    npcs: dict[str, NpcState] = Field(default_factory=dict)
    turns: list[Turn] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)
    deduction: DeductionResult | None = None

    @classmethod
    def new(cls, bible: CaseBible, case_sha256: str) -> GameState:
        return cls(
            session_id=uuid.uuid4().hex,
            case_id=bible.case_id,
            case_sha256=case_sha256,
            created_at=datetime.now(UTC),
            npcs={s.suspect_id: NpcState() for s in bible.suspects},
        )

    def condition_state(self) -> ConditionState:
        return ConditionState(
            collected=frozenset(self.collected),
            presented={npc: frozenset(s.presented) for npc, s in self.npcs.items()},
            solved=frozenset(self.solved),
            trust={npc: s.trust for npc, s in self.npcs.items()},
        )

    def turns_with(self, npc_id: str) -> list[Turn]:
        return [t for t in self.turns if t.npc_id == npc_id]

    def next_turn_id(self) -> str:
        return f"t-{len(self.turns) + 1:03d}"
