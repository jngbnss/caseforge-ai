"""추리 구조 채점: 범인 40 · 동기 20 · 수법 20 · 증거 20.

자유 서술은 저장만 한다. 의미 평가(근거 없는 주장, 논리 비약)는 4단계 LLM 피드백이 맡는다.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.session import DeductionRecord
from case_validator import CaseBible

WEIGHTS = {"culprit": 40, "motive": 20, "method": 20, "evidence": 20}
RED_HERRING_PENALTY = 5
ACCEPTABLE_CREDIT = 0.5


class DeductionSubmission(BaseModel):
    culprit_id: str
    motive_id: str
    method_id: str
    evidence_ids: list[str] = Field(default_factory=list, max_length=12)
    narrative: str = Field(default="", max_length=2000)


def score_deduction(bible: CaseBible, sub: DeductionSubmission) -> DeductionRecord:
    sol = bible.solution
    chosen = list(dict.fromkeys(sub.evidence_ids))
    key = set(sol.key_evidence)
    acceptable = set(sol.acceptable_evidence)
    red_herrings = {e.evidence_id for e in bible.evidence if e.role == "red_herring"}

    key_hits = [e for e in chosen if e in key]
    acc_hits = [e for e in chosen if e in acceptable]
    wrong = [e for e in chosen if e in red_herrings]
    unrelated = [e for e in chosen if e not in key | acceptable | red_herrings]

    raw = (len(key_hits) + ACCEPTABLE_CREDIT * len(acc_hits)) / len(key) if key else 0
    evidence_score = min(WEIGHTS["evidence"], round(WEIGHTS["evidence"] * raw))
    evidence_score = max(0, evidence_score - RED_HERRING_PENALTY * len(wrong))

    scores = {
        "culprit": WEIGHTS["culprit"] if sub.culprit_id == sol.culprit_id else 0,
        "motive": WEIGHTS["motive"] if sub.motive_id == sol.motive_id else 0,
        "method": WEIGHTS["method"] if sub.method_id == sol.method_id else 0,
        "evidence": evidence_score,
    }
    flags: dict[str, bool | list[str]] = {
        "correct_culprit": scores["culprit"] > 0,
        "unsupported_guess": scores["culprit"] > 0 and not key_hits,
        "wrong_links": wrong + unrelated,
        "missing_key": [e for e in sol.key_evidence if e not in chosen],
    }
    return DeductionRecord(
        culprit_id=sub.culprit_id,
        motive_id=sub.motive_id,
        method_id=sub.method_id,
        evidence_ids=chosen,
        narrative=sub.narrative,
        scores=scores,
        total=sum(scores.values()),
        flags=flags,
    )
