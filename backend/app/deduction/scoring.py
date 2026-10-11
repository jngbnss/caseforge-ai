"""Structured deduction scoring: culprit 40, motive 20, method 20, evidence 20.

Evidence: 20 × (selected key evidence / all key evidence) + 2 per acceptable item, capped
at 20, minus 5 per red-herring link (floor 0). A correct culprit with no supporting evidence
is flagged `unsupported_guess`. The free-text narrative is stored, never scored here.
"""

from __future__ import annotations

from case_validator import CaseBible

from app.core.session import DeductionScore, DeductionSubmission

CULPRIT_POINTS = 40
MOTIVE_POINTS = 20
METHOD_POINTS = 20
EVIDENCE_POINTS = 20
ACCEPTABLE_BONUS = 2
RED_HERRING_PENALTY = 5


def score_deduction(
    bible: CaseBible, submission: DeductionSubmission
) -> tuple[DeductionScore, list[str], list[str]]:
    """Return (score, flags, wrong_links)."""
    sol = bible.solution
    roles = {e.evidence_id: e.role for e in bible.evidence}
    selected = set(submission.evidence_ids)
    key = set(sol.key_evidence)
    acceptable = set(sol.acceptable_evidence)

    culprit = CULPRIT_POINTS if submission.culprit_id == sol.culprit_id else 0
    motive = MOTIVE_POINTS if submission.motive_id == sol.motive_id else 0
    method = METHOD_POINTS if sol.method_id and submission.method_id == sol.method_id else 0

    raw = EVIDENCE_POINTS * len(selected & key) / len(key) if key else 0
    raw += ACCEPTABLE_BONUS * len(selected & acceptable)
    red_herrings = sorted(e for e in selected if roles.get(e) == "red_herring")
    evidence = max(0, round(min(raw, EVIDENCE_POINTS)) - RED_HERRING_PENALTY * len(red_herrings))

    flags: list[str] = []
    if culprit and not selected & (key | acceptable):
        flags.append("unsupported_guess")
    if red_herrings:
        flags.append("red_herring_linked")

    wrong_links = sorted(selected - key - acceptable)
    score = DeductionScore(
        culprit=culprit,
        motive=motive,
        method=method,
        evidence=evidence,
        total=culprit + motive + method + evidence,
    )
    return score, flags, wrong_links
