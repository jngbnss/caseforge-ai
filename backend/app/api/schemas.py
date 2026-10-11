"""API 공개 응답 모델.

정답(범인, 퍼즐 답, 잠긴 사실, solution)을 담을 필드가 아예 없다. 해설(Debrief) 모델만 예외이며,
추리를 제출한 뒤에만 만들어진다.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SuspectView(BaseModel):
    suspect_id: str
    name: str
    role: str
    public_profile: str


class BriefingView(BaseModel):
    title: str
    summary: str
    damage: str
    objective: str
    public_facts: list[str]


class SceneObjectView(BaseModel):
    evidence_id: str
    spot: str
    location_name: str
    collected: bool


class EvidenceView(BaseModel):
    evidence_id: str
    name: str
    description: str
    spot: str
    location_name: str
    facts: list[str]
    time: str | None = Field(default=None, description="증거가 기록한 시각 (HH:MM)")


class PuzzleOptionView(BaseModel):
    id: str
    label: str


class PuzzleView(BaseModel):
    puzzle_id: str
    title: str
    available: bool
    solved: bool
    prompt: str | None = None
    input_type: str | None = None
    options: list[PuzzleOptionView] = Field(default_factory=list)
    code_length: int | None = None
    attempts: int = 0
    hints: list[str] = Field(default_factory=list)
    hints_remaining: int = 0


class NpcStateView(BaseModel):
    npc_id: str
    emotion: str
    trust: int
    presented: list[str]


class OptionView(BaseModel):
    id: str
    text: str


class DeductionOptionsView(BaseModel):
    motives: list[OptionView]
    methods: list[OptionView]


class DeductionResultView(BaseModel):
    scores: dict[str, int]
    total: int
    correct_culprit: bool
    unsupported_guess: bool
    wrong_links: list[str]
    missing_key: list[str]


class SessionView(BaseModel):
    session_id: str
    case_id: str
    briefing: BriefingView
    suspects: list[SuspectView]
    scene: list[SceneObjectView]
    evidence: list[EvidenceView]
    puzzles: list[PuzzleView]
    npcs: list[NpcStateView]
    deduction_options: DeductionOptionsView
    deduction: DeductionResultView | None = None


# ---------- 요청 ----------


class CreateSessionRequest(BaseModel):
    case_id: str = Field(default="museum-001", pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")


class PuzzleAttemptRequest(BaseModel):
    answer: str | list[str] = Field(description="code 퍼즐은 문자열, 순서 퍼즐은 선택지 ID 목록")


class PresentRequest(BaseModel):
    evidence_id: str


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=300)


# ---------- 행동 응답 ----------


class CollectResponse(BaseModel):
    evidence: EvidenceView
    puzzles: list[PuzzleView]
    contradictions_found: int


class PuzzleAttemptResponse(BaseModel):
    correct: bool
    unlocked: list[EvidenceView]
    puzzle: PuzzleView


class HintResponse(BaseModel):
    hint: str
    hints_used: int
    remaining: int


class PresentResponse(BaseModel):
    npc: NpcStateView
    reaction: str = Field(description="none | shaken (반응이 달라졌다)")


class AskDebug(BaseModel):
    """개발자 모드 전용 (DEBUG_API=true일 때만 채운다)."""

    grounding_fact_ids: list[str]
    used_lie_ids: list[str]
    guard_violations: list[str]
    regenerated: bool
    fallback: bool
    llm_calls: int


class AskResponse(BaseModel):
    """기획서의 Interrogation 출력 형식."""

    answer: str
    emotion: str
    revealed_fact_ids: list[str]
    contradiction_detected: bool
    trust_delta: int
    turn: int
    debug: AskDebug | None = None


class StatementView(BaseModel):
    npc_id: str
    turn: int
    question: str
    answer: str
    emotion: str | None


class ContradictionView(BaseModel):
    npc_id: str
    statement_turn: int
    statement: str
    evidence_id: str | None
    """증거와 충돌하면 그 증거. 진술끼리 충돌하는 LLM 판정은 None."""
    evidence_name: str | None
    type: str
    source: str
    """rule: Case Bible 거짓말 규칙 · llm: 모델 판정 (보조)"""
    confidence: float | None = None
    explanation: str | None = None
    other_statements: list[str] = Field(default_factory=list)
    """LLM 판정에서 함께 충돌한 이전 진술."""


class BoardView(BaseModel):
    evidence: list[EvidenceView]
    statements: list[StatementView]
    contradictions: list[ContradictionView]


# ---------- 해설 (추리 제출 후) ----------


class TimelineRowView(BaseModel):
    start: str
    end: str
    actor: str
    location: str
    action: str
    is_crime: bool


class DebriefEvidenceView(BaseModel):
    evidence_id: str
    name: str
    spot: str
    role: str
    collected: bool


class DebriefView(BaseModel):
    culprit: SuspectView
    motive: str
    method: str
    method_steps: list[str]
    timeline: list[TimelineRowView]
    key_evidence: list[DebriefEvidenceView]
    missed_key: list[DebriefEvidenceView]
    wrong_links: list[DebriefEvidenceView]
    result: DeductionResultView
