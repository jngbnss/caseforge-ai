from app.core.session import DeductionSubmission
from app.deduction.scoring import score_deduction


def _sub(**kw) -> DeductionSubmission:
    base = {
        "culprit_id": "suspect-03",
        "motive_id": "motive-gambling-debt",
        "method_id": "method-card-theft-swap",
        "evidence_ids": ["ev-03", "ev-04", "rec-01", "rec-03"],
    }
    return DeductionSubmission(**{**base, **kw})


def test_perfect_answer(museum):
    score, flags, wrong = score_deduction(museum.bible, _sub())
    assert score.total == 100 and flags == [] and wrong == []


def test_partial_evidence_and_acceptable_bonus(museum):
    score, _, _ = score_deduction(museum.bible, _sub(evidence_ids=["ev-03", "ev-02"]))
    assert score.evidence == 5 + 2


def test_red_herring_is_penalised_and_listed(museum):
    score, flags, wrong = score_deduction(
        museum.bible, _sub(evidence_ids=["ev-03", "ev-04", "rec-01", "rec-03", "ev-01"])
    )
    assert score.evidence == 15
    assert "red_herring_linked" in flags and wrong == ["ev-01"]


def test_wrong_culprit_scores_zero_for_culprit(museum):
    score, flags, _ = score_deduction(museum.bible, _sub(culprit_id="suspect-02", evidence_ids=[]))
    assert score.culprit == 0 and "unsupported_guess" not in flags
