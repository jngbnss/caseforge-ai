"""Case Bible schema (Pydantic v2).

Every model is frozen and every collection is a tuple, so a loaded Case Bible cannot be
mutated during a game session. Field meanings are documented in docs/case-schema.md.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_CLOCK = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# --------------------------------------------------------------------------- time


class TimeRange(_Frozen):
    """Closed-open clock interval within a single night. A single "HH:MM" string is an instant."""

    start: str
    end: str

    @model_validator(mode="before")
    @classmethod
    def _instant_shorthand(cls, data: object) -> object:
        if isinstance(data, str):
            return {"start": data, "end": data}
        return data

    @field_validator("start", "end")
    @classmethod
    def _clock_format(cls, value: str) -> str:
        if not _CLOCK.match(value):
            raise ValueError(f"time must be HH:MM, got {value!r}")
        return value

    @model_validator(mode="after")
    def _ordered(self) -> TimeRange:
        if self.end_min < self.start_min:
            raise ValueError(f"time range ends before it starts: {self.start}-{self.end}")
        return self

    @property
    def start_min(self) -> int:
        h, m = self.start.split(":")
        return int(h) * 60 + int(m)

    @property
    def end_min(self) -> int:
        h, m = self.end.split(":")
        return int(h) * 60 + int(m)

    @property
    def is_instant(self) -> bool:
        return self.start_min == self.end_min

    def overlaps(self, other: TimeRange) -> bool:
        """Half-open overlap; an instant occupies [t, t + 0.5)."""
        a_end = max(self.end_min, self.start_min + 0.5)
        b_end = max(other.end_min, other.start_min + 0.5)
        return self.start_min < b_end and other.start_min < a_end

    def touches(self, other: TimeRange) -> bool:
        """Closed overlap: shared endpoints count (a 21:07 receipt fits a 21:04-21:07 event)."""
        return self.start_min <= other.end_min and other.start_min <= self.end_min


# ---------------------------------------------------------------------- condition DSL


class Always(_Frozen):
    always: Literal[True]


class AllOf(_Frozen):
    all: tuple[Condition, ...]


class AnyOf(_Frozen):
    any: tuple[Condition, ...]


class EvidenceCollected(_Frozen):
    evidence_collected: str


class EvidencePresented(_Frozen):
    evidence_presented: str
    npc: str | None = None  # None: presented to any NPC (or to the contextual NPC)


class PuzzleSolved(_Frozen):
    puzzle_solved: str


class TrustGte(_Frozen):
    trust_gte: int = Field(ge=0)
    npc: str | None = None  # None: the NPC the condition belongs to (e.g. Secret.npc_id)


Condition = Always | AllOf | AnyOf | EvidenceCollected | EvidencePresented | PuzzleSolved | TrustGte

AllOf.model_rebuild()
AnyOf.model_rebuild()


# ------------------------------------------------------------------------- entities


class Adjacency(_Frozen):
    to: str
    minutes: int = Field(ge=0)


class Location(_Frozen):
    location_id: str
    name: str
    description: str = ""
    adjacent: tuple[Adjacency, ...] = ()


class MotiveOption(_Frozen):
    motive_id: str
    label: str


class MethodOption(_Frozen):
    method_id: str
    label: str


class Briefing(_Frozen):
    headline: str
    summary: str
    objective: str
    opening_location_id: str
    motive_options: tuple[MotiveOption, ...]
    method_options: tuple[MethodOption, ...] = ()


class ReactionLines(_Frozen):
    """Lines spoken when the player presents evidence (no LLM involved)."""

    lie_broken: str  # the evidence breaks one of this NPC's lies
    relevant: str  # the evidence concerns something this NPC knows
    unrelated: str


class Dialogue(_Frozen):
    personality: str
    speech_style: str
    sample_lines: tuple[str, ...] = Field(min_length=1)
    evasion_lines: tuple[str, ...] = Field(min_length=1)
    reaction_lines: ReactionLines | None = None


class Suspect(_Frozen):
    suspect_id: str
    name: str
    role: str
    public_profile: str
    apparent_suspicion: str
    capabilities: tuple[str, ...] = ()  # means the person actually has (U01)
    dialogue: Dialogue


class Fact(_Frozen):
    fact_id: str
    content: str
    kind: Literal["truth", "testimony", "lie", "record"]
    source: str
    time: TimeRange | None = None
    location_id: str | None = None
    subjects: tuple[str, ...] = ()
    known_by: tuple[str, ...]
    available_to_player: bool = False
    unlock_condition: Condition | None = None
    implicates: tuple[str, ...] = ()  # suspects this fact points at as perpetrator (U01)
    leak_forbidden: bool = False  # must never be spoken by an NPC
    canary_keywords: tuple[str, ...] = ()  # rule-based leak guard strings


class Lie(_Frozen):
    lie_id: str
    npc_id: str
    contradicts_fact_id: str
    claim: str
    breaks_on: tuple[str, ...]
    contradiction_type: Literal["time", "location", "possession"] = "location"


class Secret(_Frozen):
    secret_id: str
    npc_id: str
    fact_ids: tuple[str, ...] = Field(min_length=1)
    reveal_when: Condition


class Attestation(_Frozen):
    """What an evidence item says about a timeline event (checked by T02)."""

    event_id: str
    location_id: str
    time: TimeRange | None = None


class Hotspot(_Frozen):
    """Click area on the 2D scene, in percent of the scene width/height."""

    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)


class Evidence(_Frozen):
    evidence_id: str
    name: str
    description: str = ""
    location_id: str  # where the player finds it
    discoverable: Condition
    proves_fact_ids: tuple[str, ...]
    role: Literal["key", "supporting", "red_herring"]
    attests: tuple[Attestation, ...] = ()
    hotspot: Hotspot | None = None


class PuzzleItem(_Frozen):
    item_id: str
    label: str


class Before(_Frozen):
    kind: Literal["before"]
    first: str
    then: str
    clue: str = ""


class ImmediatelyBefore(_Frozen):
    kind: Literal["immediately_before"]
    first: str
    then: str
    clue: str = ""


class SegmentIn(_Frozen):
    kind: Literal["segment_in"]
    start: int = Field(ge=0)
    length: int = Field(ge=1)
    values: tuple[str, ...]
    clue: str = ""


class SegmentNotIn(_Frozen):
    kind: Literal["segment_not_in"]
    start: int = Field(ge=0)
    length: int = Field(ge=1)
    values: tuple[str, ...]
    clue: str = ""


class SegmentsAscending(_Frozen):
    kind: Literal["segments_ascending"]
    length: int = Field(ge=1)
    clue: str = ""


PuzzleConstraint = Annotated[
    Before | ImmediatelyBefore | SegmentIn | SegmentNotIn | SegmentsAscending,
    Field(discriminator="kind"),
]


class Puzzle(_Frozen):
    puzzle_id: str
    title: str
    prompt: str
    location_id: str
    input_type: Literal["sequence", "code", "arrangement"]
    items: tuple[PuzzleItem, ...] = ()  # sequence / arrangement pieces
    code_length: int | None = None  # code puzzles
    code_alphabet: str = "0123456789"
    constraints: tuple[PuzzleConstraint, ...]
    answer: str | tuple[str, ...]  # server only, never sent to clients
    hints: tuple[str, ...] = ()
    requires: Condition | None = None
    unlocks_evidence: tuple[str, ...] = ()
    hotspot: Hotspot | None = None


class TimelineEvent(_Frozen):
    event_id: str
    time: TimeRange
    actor_id: str | None  # None for building-wide events (e.g. closing time)
    location_id: str
    action: str
    fact_ids: tuple[str, ...] = ()


class CrimeScene(_Frozen):
    location_id: str
    time: TimeRange


class Solution(_Frozen):
    culprit_id: str
    motive_id: str
    motive_keywords: tuple[str, ...] = ()
    method_id: str | None = None  # correct entry of briefing.method_options
    method_steps: tuple[str, ...]  # fact ids in order
    key_evidence: tuple[str, ...]  # minimal proof set
    acceptable_evidence: tuple[str, ...] = ()  # partial credit
    crime: CrimeScene
    required_means: tuple[str, ...] = ()  # capabilities needed to commit the crime (U01)


class CaseBible(_Frozen):
    case_id: str
    title: str
    briefing: Briefing
    locations: tuple[Location, ...]
    suspects: tuple[Suspect, ...]
    facts: tuple[Fact, ...]
    lies: tuple[Lie, ...]
    secrets: tuple[Secret, ...]
    evidence: tuple[Evidence, ...]
    puzzles: tuple[Puzzle, ...]
    timeline: tuple[TimelineEvent, ...]
    solution: Solution
