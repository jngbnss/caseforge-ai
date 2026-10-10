"""Case Bible 스키마.

모든 모델은 frozen이고 시퀀스는 tuple이다. 로드 후 사건 데이터를 바꿀 수 없다.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

_CLOCK = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _check_clock(value: str) -> str:
    if not _CLOCK.match(value):
        raise ValueError(f"시각은 HH:MM 형식이어야 한다: {value!r}")
    return value


Clock = Annotated[str, AfterValidator(_check_clock)]


def to_minutes(clock: str) -> int:
    hours, minutes = clock.split(":")
    return int(hours) * 60 + int(minutes)


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TimeRange(Frozen):
    start: Clock
    end: Clock

    @model_validator(mode="after")
    def _ordered(self) -> TimeRange:
        if to_minutes(self.end) < to_minutes(self.start):
            raise ValueError(f"end({self.end})가 start({self.start})보다 앞선다")
        return self

    @property
    def start_min(self) -> int:
        return to_minutes(self.start)

    @property
    def end_min(self) -> int:
        return to_minutes(self.end)

    def overlaps(self, other: TimeRange) -> bool:
        return self.start_min < other.end_min and other.start_min < self.end_min


# ---------- 조건 DSL ----------


class AllOf(Frozen):
    all: tuple[Condition, ...]


class AnyOf(Frozen):
    any: tuple[Condition, ...]


class EvidenceCollected(Frozen):
    evidence_collected: str


class PresentedTo(Frozen):
    evidence_id: str
    npc_id: str


class EvidencePresented(Frozen):
    evidence_presented: PresentedTo


class PuzzleSolved(Frozen):
    puzzle_solved: str


class TrustThreshold(Frozen):
    npc_id: str
    value: int = Field(ge=0)


class TrustGte(Frozen):
    trust_gte: TrustThreshold


Condition = AllOf | AnyOf | EvidenceCollected | EvidencePresented | PuzzleSolved | TrustGte

AllOf.model_rebuild()
AnyOf.model_rebuild()


# ---------- 사건 구성 요소 ----------


class Adjacency(Frozen):
    to: str
    minutes: int = Field(ge=0)


class Location(Frozen):
    location_id: str
    name: str
    adjacent: tuple[Adjacency, ...] = ()


class Briefing(Frozen):
    summary: str
    damage: str
    objective: str
    public_fact_ids: tuple[str, ...] = ()


class Fact(Frozen):
    fact_id: str
    content: str
    kind: Literal["truth", "testimony", "lie", "record"]
    source: str
    time: TimeRange | None = None
    location_id: str | None = None
    subjects: tuple[str, ...] = ()
    known_by: tuple[str, ...] = ()
    available_to_player: bool = False
    unlock_condition: Condition | None = None
    forbidden: bool = False
    """True면 어떤 NPC도 직접 진술하지 않는다 (범인 전용 사실 등)."""
    canary_keywords: tuple[str, ...] = ()
    """누설 가드가 NPC 답변에서 찾는 문자열."""


class Suspect(Frozen):
    suspect_id: str
    name: str
    role: str
    public_profile: str
    capabilities: tuple[str, ...] = ()


class Lie(Frozen):
    lie_id: str
    npc_id: str
    contradicts_fact_id: str
    claim: str
    breaks_on: tuple[str, ...]


class Secret(Frozen):
    secret_id: str
    npc_id: str
    fact_ids: tuple[str, ...]
    reveal_when: Condition


class Attestation(Frozen):
    """증거가 기록하고 있는 순간. T02에서 시간선과 대조한다."""

    event_id: str
    time: TimeRange
    location_id: str


Claim = Literal["opportunity", "means", "motive"]


class Implication(Frozen):
    suspect_id: str
    claim: Claim


class Evidence(Frozen):
    evidence_id: str
    name: str
    description: str
    location_id: str
    spot: str | None = None
    """현장에서 조사하는 지점 이름 (예: 진열장 받침). 화면의 조사 오브젝트 라벨로 쓴다."""
    source: Literal["scene", "puzzle"]
    discoverable: Condition | None = None
    """None이면 처음부터 발견 가능하다."""
    proves_fact_ids: tuple[str, ...] = ()
    role: Literal["key", "supporting", "red_herring"]
    attests: Attestation | None = None
    implicates: tuple[Implication, ...] = ()


class PuzzleOption(Frozen):
    id: str
    label: str


class OrderClue(Frozen):
    """순서형 퍼즐의 단서. before/after 쌍, 또는 first/last 하나."""

    before: str | None = None
    after: str | None = None
    first: str | None = None
    last: str | None = None

    @model_validator(mode="after")
    def _shape(self) -> OrderClue:
        pair = self.before is not None and self.after is not None
        single = (self.first is not None) != (self.last is not None)
        if pair == single or (pair and (self.first or self.last)):
            raise ValueError("before/after 쌍 또는 first/last 중 하나만 지정한다")
        return self


class CodeClue(Frozen):
    """코드형 퍼즐의 단서: code[start:end]는 one_of 중 하나다."""

    start: int = Field(ge=0)
    end: int
    one_of: tuple[str, ...]


class Puzzle(Frozen):
    puzzle_id: str
    title: str
    prompt: str
    input_type: Literal["sequence", "code", "arrangement"]
    options: tuple[PuzzleOption, ...] = ()
    order_clues: tuple[OrderClue, ...] = ()
    code_length: int | None = None
    code_clues: tuple[CodeClue, ...] = ()
    answer: tuple[str, ...] | str
    hints: tuple[str, ...] = ()
    requires: Condition | None = None
    unlocks_evidence: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _shape(self) -> Puzzle:
        if self.input_type == "code":
            if not isinstance(self.answer, str) or self.code_length is None:
                raise ValueError("code 퍼즐은 문자열 answer와 code_length가 필요하다")
        elif isinstance(self.answer, str) or not self.options:
            raise ValueError(f"{self.input_type} 퍼즐은 options와 순서 answer가 필요하다")
        return self


class TimelineEvent(Frozen):
    event_id: str
    time: TimeRange
    actor_id: str
    location_id: str
    action: str
    fact_ids: tuple[str, ...] = ()
    is_crime: bool = False


class DeductionOption(Frozen):
    id: str
    text: str


class DeductionOptions(Frozen):
    motives: tuple[DeductionOption, ...]
    methods: tuple[DeductionOption, ...]


class CrimeScene(Frozen):
    location_id: str
    time: TimeRange


class Solution(Frozen):
    culprit_id: str
    motive_id: str
    method_id: str
    method_steps: tuple[str, ...]
    key_evidence: tuple[str, ...]
    acceptable_evidence: tuple[str, ...] = ()
    crime: CrimeScene
    required_means: tuple[str, ...] = ()


class Dialogue(Frozen):
    suspect_id: str
    personality: str
    speech_style: str
    sample_lines: tuple[str, ...] = Field(min_length=5)
    evasions: tuple[str, ...] = Field(min_length=3)


class CaseBible(Frozen):
    case_id: str
    title: str
    briefing: Briefing
    locations: tuple[Location, ...]
    suspects: tuple[Suspect, ...]
    facts: tuple[Fact, ...]
    lies: tuple[Lie, ...] = ()
    secrets: tuple[Secret, ...] = ()
    evidence: tuple[Evidence, ...]
    puzzles: tuple[Puzzle, ...] = ()
    timeline: tuple[TimelineEvent, ...]
    deduction_options: DeductionOptions
    solution: Solution
    dialogues: tuple[Dialogue, ...] = ()

    @model_validator(mode="after")
    def _unique_ids(self) -> CaseBible:
        groups = {
            "location": [x.location_id for x in self.locations],
            "suspect": [x.suspect_id for x in self.suspects],
            "fact": [x.fact_id for x in self.facts],
            "lie": [x.lie_id for x in self.lies],
            "secret": [x.secret_id for x in self.secrets],
            "evidence": [x.evidence_id for x in self.evidence],
            "puzzle": [x.puzzle_id for x in self.puzzles],
            "event": [x.event_id for x in self.timeline],
        }
        for name, ids in groups.items():
            dupes = {i for i in ids if ids.count(i) > 1}
            if dupes:
                raise ValueError(f"중복된 {name} ID: {sorted(dupes)}")
        return self

    # 조회 헬퍼
    def suspect(self, suspect_id: str) -> Suspect | None:
        return next((s for s in self.suspects if s.suspect_id == suspect_id), None)

    def evidence_by_id(self, evidence_id: str) -> Evidence | None:
        return next((e for e in self.evidence if e.evidence_id == evidence_id), None)

    def fact(self, fact_id: str) -> Fact | None:
        return next((f for f in self.facts if f.fact_id == fact_id), None)
