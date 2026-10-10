from __future__ import annotations

import asyncio

from app.agents.interrogation import Interrogator
from app.cases.registry import get_case
from app.core.embedding.mock import MockEmbedding
from app.core.llm.mock import MockLLM
from app.core.session import SessionStore
from app.deduction.scoring import DeductionSubmission, score_deduction
from app.evidence.contradiction import detect_rule_contradictions


def test_rule_contradiction_after_lie_and_evidence(db) -> None:
    session = SessionStore(db).create("museum-001")
    interrogator = Interrogator(MockLLM.for_case("museum-001"), MockEmbedding(), db)
    asyncio.run(interrogator.ask(session, "suspect-03", "21시에 어디 있었어요?"))  # lie-03

    assert detect_rule_contradictions(db, session) == []  # 아직 반박 증거 없음

    session.state.collected += ["ev-04"]
    found = detect_rule_contradictions(db, session)
    assert [(c.npc_id, c.lie_id, c.evidence_id, c.type, c.source) for c in found] == [
        ("suspect-03", "lie-03", "ev-04", "location", "rule")
    ]
    assert found[0].statement_turn == 1
    assert detect_rule_contradictions(db, session) == []  # 중복 기록 없음

    session.state.collected += ["rec-03"]
    assert [c.evidence_id for c in detect_rule_contradictions(db, session)] == ["rec-03"]


def bible():
    return get_case("museum-001").bible


def sub(**kw) -> DeductionSubmission:
    base = dict(
        culprit_id="suspect-03",
        motive_id="mot-debt",
        method_id="met-swap",
        evidence_ids=["ev-03", "ev-04", "rec-01", "rec-02", "rec-03"],
    )
    return DeductionSubmission(**(base | kw))


def test_perfect_deduction_scores_100() -> None:
    result = score_deduction(bible(), sub())
    assert result.total == 100
    assert result.flags["missing_key"] == []
    assert result.flags["unsupported_guess"] is False


def test_red_herring_is_penalized() -> None:
    result = score_deduction(
        bible(), sub(evidence_ids=["ev-03", "ev-04", "rec-01", "rec-02", "rec-03", "ev-01"])
    )
    assert result.scores["evidence"] == 15
    assert result.flags["wrong_links"] == ["ev-01"]


def test_partial_and_wrong_culprit() -> None:
    result = score_deduction(
        bible(), sub(culprit_id="suspect-02", method_id="met-guard-card", evidence_ids=["ev-01"])
    )
    assert result.scores == {"culprit": 0, "motive": 20, "method": 0, "evidence": 0}
    assert result.flags["correct_culprit"] is False


def test_guess_without_evidence_is_flagged() -> None:
    result = score_deduction(bible(), sub(evidence_ids=[]))
    assert result.scores["culprit"] == 40
    assert result.flags["unsupported_guess"] is True


def test_acceptable_evidence_gives_half_credit() -> None:
    result = score_deduction(bible(), sub(evidence_ids=["ev-03", "ev-05"]))
    assert result.scores["evidence"] == round(20 * 1.5 / 5)
