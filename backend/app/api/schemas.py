"""Public API models. Nothing here may carry the solution, puzzle answers, evidence roles,
locked facts or the internal lie/secret ids. tests/test_leaks.py enforces this."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.core.session import Emotion

# ------------------------------------------------------------------------------ common


class Hotspot(BaseModel):
    x: float
    y: float


class Option(BaseModel):
    id: str
    label: str


class BriefingOut(BaseModel):
    headline: str
    summary: str
    objective: str
    opening_location_id: str
    motive_options: list[Option]
    method_options: list[Option]


class LocationOut(BaseModel):
    location_id: str
    name: str
    description: str


class SuspectOut(BaseModel):
    suspect_id: str
    name: str
    role: str
    public_profile: str
    apparent_suspicion: str
    trust: int
    emotion: Emotion


class EvidenceOut(BaseModel):
    evidence_id: str
    name: str
    description: str
    location_id: str
    hotspot: Hotspot | None = None


class PuzzleItemOut(BaseModel):
    item_id: str
    label: str


class PuzzleOut(BaseModel):
    puzzle_id: str
    title: str
    prompt: str
    location_id: str
    input_type: Literal["sequence", "code", "arrangement"]
    items: list[PuzzleItemOut]  # shuffled per session; never in answer order
    code_length: int | None
    status: Literal["locked", "available", "solved"]
    attempts: int
    hints_used: int
    hints_total: int
    hotspot: Hotspot | None = None


class SceneObject(BaseModel):
    object_id: str
    kind: Literal["evidence", "puzzle"]
    location_id: str
    label: str
    hotspot: Hotspot | None
    done: bool  # collected / solved


class ContradictionOut(BaseModel):
    contradiction_id: str
    npc_id: str
    type: str
    statement_ids: list[str]
    evidence_ids: list[str]
    source: Literal["rule", "llm"]
    confidence: float
    explanation: str


class SessionOut(BaseModel):
    session_id: str
    case_id: str
    case_sha256: str
    title: str
    briefing: BriefingOut
    locations: list[LocationOut]
    suspects: list[SuspectOut]
    collected_evidence: list[EvidenceOut]
    objects: list[SceneObject]
    puzzles: list[PuzzleOut]
    deduction_submitted: bool


# ---------------------------------------------------------------------------- requests


class CreateSessionIn(BaseModel):
    case_id: str | None = None


class PuzzleAttemptIn(BaseModel):
    answer: str | list[str] = Field(max_length=32)


class PresentIn(BaseModel):
    evidence_id: str = Field(max_length=32)


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=300)


class DeductionIn(BaseModel):
    culprit_id: str
    motive_id: str
    method_id: str
    evidence_ids: list[str] = Field(default_factory=list, max_length=16)
    narrative: str = Field(default="", max_length=3000)


# --------------------------------------------------------------------------- responses


class CollectOut(BaseModel):
    evidence: EvidenceOut
    new_contradictions: list[ContradictionOut]


class PuzzleAttemptOut(BaseModel):
    correct: bool
    attempts: int
    unlocked_evidence: list[EvidenceOut]


class HintOut(BaseModel):
    hint: str
    hints_used: int
    hints_remaining: int


class PresentOut(BaseModel):
    npc_id: str
    evidence_id: str
    reaction: str
    emotion: Emotion
    trust: int
    trust_delta: int
    lie_broken: bool


class AskOut(BaseModel):
    turn_id: str
    npc_id: str
    answer: str
    emotion: Emotion
    trust: int
    trust_delta: int
    revealed_fact_ids: list[str]
    contradiction_detected: bool
    guard_blocked: bool


class StatementOut(BaseModel):
    statement_id: str
    npc_id: str
    question: str
    text: str
    pinned: bool


class TimelineMark(BaseModel):
    evidence_id: str
    evidence_name: str
    location_id: str
    time: str | None  # "21:12" or "21:04-21:07"


class BoardOut(BaseModel):
    suspects: list[SuspectOut]
    evidence: list[EvidenceOut]
    statements: list[StatementOut]
    contradictions: list[ContradictionOut]
    timeline: list[TimelineMark]


class DialogueOut(BaseModel):
    npc_id: str
    statements: list[StatementOut]


class ScoreOut(BaseModel):
    culprit: int
    motive: int
    method: int
    evidence: int
    total: int


class DeductionOut(BaseModel):
    score: ScoreOut
    flags: list[str]


class TimelineEventOut(BaseModel):
    time: str
    actor: str | None
    location: str
    action: str


class NamedRef(BaseModel):
    id: str
    name: str
    reason: str = ""


class DebriefOut(BaseModel):
    culprit: NamedRef
    motive: str
    method: str
    method_steps: list[str]
    key_evidence: list[NamedRef]
    timeline: list[TimelineEventOut]
    missed_clues: list[NamedRef]
    wrong_links: list[NamedRef]
    score: ScoreOut
    flags: list[str]
    your_answer: DeductionIn
    narrative_feedback: dict | None = None


class Health(BaseModel):
    status: str
    version: str
    llm_backend: str
    embedding_backend: str
