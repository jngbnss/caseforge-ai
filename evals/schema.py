"""평가셋 한 줄의 형식 (기획서 8절). `uv run python -m evals.schema`로 전체 파일을 검사한다."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from evals import DATA_DIR


class _Line(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvalState(_Line):
    """심문 직전의 게임 상태. 러너가 이대로 세션을 만든다."""

    collected: list[str] = Field(default_factory=list)
    presented: dict[str, list[str]] = Field(default_factory=dict)
    trust: dict[str, int] = Field(default_factory=dict)
    solved: list[str] = Field(default_factory=list)


AttackType = Literal[
    "direct",
    "other_npc_secret",
    "system_prompt",
    "role_hijack",
    "hypothetical",
    "unshown_evidence_lure",
    "multilingual_encoding",
    "repeated_pressure",
]


class SecretLeakCase(_Line):
    id: str
    npc_id: str
    state: EvalState
    question: str = Field(min_length=1, max_length=300)
    forbidden_fact_ids: list[str] = Field(min_length=1)
    attack_type: AttackType
    history: list[str] = Field(default_factory=list)
    """같은 공격을 앞서 몇 번 했는지 (repeated_pressure). 러너가 차례로 묻는다."""


class EvidenceGroundingCase(_Line):
    id: str
    npc_id: str
    state: EvalState
    question: str = Field(min_length=1, max_length=300)
    allowed_fact_ids: list[str]
    must_cite: str | None = None
    """정답 근거로 기대하는 fact. 답변의 revealed_fact_ids에 있으면 적중."""


class Statement(_Line):
    turn: int
    text: str


ContradictionType = Literal["time", "location", "possession", "statement"]


class ExpectedContradiction(_Line):
    type: ContradictionType
    pair: list[str] = Field(min_length=2, max_length=2)
    """('t<turn>' | evidence_id) 두 개. 예: ['t2', 'ev-02'], ['t1', 't2']"""


class ContradictionCase(_Line):
    id: str
    npc_id: str
    statements: list[Statement] = Field(min_length=1)
    evidence: list[str] = Field(default_factory=list)
    """그 NPC에게 제시한 증거."""
    expected: list[ExpectedContradiction]
    """비어 있으면 음성 사례 (모순 없음)."""
    note: str = ""

    @model_validator(mode="after")
    def _pairs_exist(self) -> ContradictionCase:
        refs = {f"t{s.turn}" for s in self.statements} | set(self.evidence)
        for e in self.expected:
            missing = set(e.pair) - refs
            if missing:
                raise ValueError(f"{self.id}: unknown refs {missing}")
        return self


class DeductionSubmissionLine(_Line):
    culprit_id: str
    motive_id: str
    method_id: str
    evidence_ids: list[str]
    narrative: str


class ExpectedScores(_Line):
    culprit: int
    motive: int
    method: int
    evidence: int
    leaps: bool
    """서술에 논리 비약이나 근거 없는 주장이 있도록 만들었는가 (LLM 피드백이 표시해야 함)."""


class DeductionCase(_Line):
    id: str
    tier: Literal["correct", "partial", "wrong", "unsupported"]
    collected: list[str]
    submission: DeductionSubmissionLine
    expected_scores: ExpectedScores


SUITES: dict[str, tuple[str, type[_Line], int]] = {
    "secret-leak": ("secret-leak-cases.jsonl", SecretLeakCase, 120),
    "evidence-grounding": ("evidence-grounding.jsonl", EvidenceGroundingCase, 60),
    "contradiction": ("contradiction-cases.jsonl", ContradictionCase, 40),
    "deduction": ("deduction-cases.jsonl", DeductionCase, 40),
}


def load(suite: str, data_dir: Path = DATA_DIR) -> list:
    name, model, _ = SUITES[suite]
    lines = (data_dir / name).read_text(encoding="utf-8").splitlines()
    return [model.model_validate(json.loads(line)) for line in lines if line.strip()]


def check(data_dir: Path = DATA_DIR) -> dict[str, int]:
    """모든 평가셋이 형식에 맞고, 건수가 맞고, ID가 겹치지 않는지 검사한다."""
    counts: dict[str, int] = {}
    for suite, (_, _, expected) in SUITES.items():
        rows = load(suite, data_dir)
        dup = [i for i, n in Counter(r.id for r in rows).items() if n > 1]
        if dup:
            raise ValueError(f"{suite}: duplicate ids {dup[:5]}")
        if len(rows) != expected:
            raise ValueError(f"{suite}: {len(rows)} rows, expected {expected}")
        counts[suite] = len(rows)
    return counts


if __name__ == "__main__":
    try:
        print(check())
    except Exception as exc:  # noqa: BLE001
        print(f"evals schema check failed: {exc}")
        sys.exit(1)
