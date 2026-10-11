"""평가 데이터(4-7): 형식·건수 검사, 그리고 라벨이 실제 게임 규칙과 맞는지 교차 검증한다."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from evals.schema import check, load  # noqa: E402

from app.agents.knowledge_scope import build_scope  # noqa: E402
from app.cases.registry import get_case  # noqa: E402
from app.core.session import GameState  # noqa: E402
from app.deduction.scoring import DeductionSubmission, score_deduction  # noqa: E402

BIBLE = get_case("museum-001").bible
NPCS = [s.suspect_id for s in BIBLE.suspects]


def game_state(s) -> GameState:
    return GameState(
        collected=list(s.collected),
        solved=list(s.solved),
        presented={k: list(v) for k, v in s.presented.items()},
        trust={n: s.trust.get(n, 0) for n in NPCS},
    )


def test_all_suites_have_the_planned_size_and_valid_rows() -> None:
    assert check() == {
        "secret-leak": 120,
        "evidence-grounding": 60,
        "contradiction": 40,
        "deduction": 40,
    }


def test_secret_leak_covers_8_attack_types_x_3_npcs_x_5_variants() -> None:
    rows = load("secret-leak")
    assert Counter((r.attack_type, r.npc_id) for r in rows) == {
        (a, n): 5 for a in {r.attack_type for r in rows} for n in NPCS
    }
    assert len({r.attack_type for r in rows}) == 8


def test_forbidden_facts_are_never_in_scope_and_grounding_facts_always_are() -> None:
    for r in load("secret-leak"):
        scope = build_scope(BIBLE, game_state(r.state), r.npc_id)
        assert not set(r.forbidden_fact_ids) & scope.allowed_fact_ids, r.id
    for r in load("evidence-grounding"):
        scope = build_scope(BIBLE, game_state(r.state), r.npc_id)
        assert set(r.allowed_fact_ids) == scope.allowed_fact_ids, r.id
        assert r.must_cite is None or r.must_cite in scope.allowed_fact_ids, r.id


def test_contradiction_set_is_balanced() -> None:
    rows = load("contradiction")
    assert sum(bool(r.expected) for r in rows) == 20
    assert sum(not r.expected for r in rows) == 20


def test_deduction_labels_match_the_scorer() -> None:
    rows = load("deduction")
    assert Counter(r.tier for r in rows) == {
        "correct": 10,
        "partial": 10,
        "wrong": 10,
        "unsupported": 10,
    }
    for r in rows:
        rec = score_deduction(BIBLE, DeductionSubmission(**r.submission.model_dump()))
        exp = r.expected_scores
        assert rec.scores == {
            "culprit": exp.culprit,
            "motive": exp.motive,
            "method": exp.method,
            "evidence": exp.evidence,
        }, r.id
        if r.tier == "unsupported":
            assert rec.flags["unsupported_guess"] is True, r.id
