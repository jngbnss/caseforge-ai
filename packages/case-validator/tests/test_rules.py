"""규칙마다 museum-001을 일부러 망가뜨리고, 정확히 그 규칙이 걸리는지 확인한다."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from case_validator import CaseBible, validate
from conftest import find


def run(case: dict[str, Any]):
    return validate(CaseBible.model_validate(case))


def test_museum_passes(museum: dict) -> None:
    report = run(museum)
    assert report.errors == []
    assert report.warnings == []
    assert report.metrics["reachable_evidence"] == 8
    assert report.metrics["solvable_puzzles"] == 3


# ---------- 망가뜨리기 ----------


def missing_location(c: dict) -> None:
    find(c["evidence"], "evidence_id", "ev-03")["location_id"] = "loc-nowhere"


def key_evidence_unreachable(c: dict) -> None:
    find(c["evidence"], "evidence_id", "ev-04")["discoverable"] = {"evidence_collected": "ev-04"}


def puzzle_cycle(c: dict) -> None:
    find(c["puzzles"], "puzzle_id", "pz-02")["requires"] = {"puzzle_solved": "pz-03"}
    find(c["puzzles"], "puzzle_id", "pz-03")["requires"] = {"puzzle_solved": "pz-02"}


def code_two_answers(c: dict) -> None:
    find(c["puzzles"], "puzzle_id", "pz-02")["code_clues"][0]["one_of"] = ["07", "19"]


def order_two_answers(c: dict) -> None:
    find(c["puzzles"], "puzzle_id", "pz-01")["order_clues"].pop()


def answer_mismatch(c: dict) -> None:
    find(c["puzzles"], "puzzle_id", "pz-02")["answer"] = "0785"


def solvable_without_puzzles(c: dict) -> None:
    find(c["evidence"], "evidence_id", "ev-03")["implicates"].append(
        {"suspect_id": "suspect-03", "claim": "motive"}
    )


def briefing_leaks_answer(c: dict) -> None:
    c["briefing"]["public_fact_ids"].append("fact-042")


def lie_unbreakable(c: dict) -> None:
    find(c["lies"], "lie_id", "lie-02")["breaks_on"] = []


def secret_never_revealed(c: dict) -> None:
    find(c["secrets"], "secret_id", "sec-01")["reveal_when"] = {
        "trust_gte": {"npc_id": "suspect-01", "value": 5}
    }


def double_presence(c: dict) -> None:
    # 한서윤이 20:30–20:35 전시실에 있는 동안 사무실에도 있다
    find(c["timeline"], "event_id", "e-s01-2")["time"] = {"start": "20:33", "end": "20:45"}


def evidence_time_mismatch(c: dict) -> None:
    find(c["evidence"], "evidence_id", "ev-02")["attests"]["time"] = {
        "start": "21:30",
        "end": "21:30",
    }


def impossible_travel(c: dict) -> None:
    # 휴게실 21:24 → 보안실 21:24 (2분 필요)
    find(c["timeline"], "event_id", "e-s02-6")["time"]["start"] = "21:24"


def second_full_suspect(c: dict) -> None:
    # 박도현을 흡연 구역 대신 전시실에 두고, 수단과 증거 체인을 모두 준다
    find(c["timeline"], "event_id", "e-s02-4")["location_id"] = "loc-hall"
    ev02 = find(c["evidence"], "evidence_id", "ev-02")
    ev02.pop("attests")
    ev02["implicates"] = [
        {"suspect_id": "suspect-02", "claim": "means"},
        {"suspect_id": "suspect-02", "claim": "motive"},
    ]
    find(c["suspects"], "suspect_id", "suspect-02")["capabilities"] += [
        "replica_making",
        "cctv_terminal_access",
    ]


def culprit_without_motive(c: dict) -> None:
    find(c["evidence"], "evidence_id", "rec-02")["implicates"] = []


def key_evidence_redundant(c: dict) -> None:
    find(c["evidence"], "evidence_id", "ev-05")["implicates"] = [
        {"suspect_id": "suspect-03", "claim": claim} for claim in ("opportunity", "means", "motive")
    ]


BROKEN: list[tuple[str, Callable[[dict], None]]] = [
    ("V01", missing_location),
    ("V02", key_evidence_unreachable),
    ("V03", puzzle_cycle),
    ("V04", code_two_answers),
    ("V04", order_two_answers),
    ("V04", answer_mismatch),
    ("V05", solvable_without_puzzles),
    ("V05", briefing_leaks_answer),
    ("V06", lie_unbreakable),
    ("V07", secret_never_revealed),
    ("T01", double_presence),
    ("T02", evidence_time_mismatch),
    ("T03", impossible_travel),
    ("U01", second_full_suspect),
    ("U01", culprit_without_motive),
    ("U02", key_evidence_redundant),
]


@pytest.mark.parametrize(("rule_id", "breaker"), BROKEN, ids=[b.__name__ for _, b in BROKEN])
def test_broken_case_fails_on_rule(museum: dict, rule_id: str, breaker) -> None:
    breaker(museum)
    report = run(museum)
    assert not report.ok
    assert rule_id in {i.rule_id for i in report.errors}, [str(i) for i in report.errors]


def test_other_suspect_with_opportunity_and_means_warns(museum: dict) -> None:
    # 박도현에게 기회와 수단만 주고 증거는 주지 않으면 경고만 난다
    find(museum["timeline"], "event_id", "e-s02-4")["location_id"] = "loc-hall"
    find(museum["evidence"], "evidence_id", "ev-02").pop("attests")
    find(museum["suspects"], "suspect_id", "suspect-02")["capabilities"] += [
        "replica_making",
        "cctv_terminal_access",
    ]
    report = run(museum)
    assert report.ok, [str(i) for i in report.errors]
    assert any(i.rule_id == "U01" and "suspect-02" in i.refs for i in report.warnings)


def test_reference_errors_stop_further_checks(museum: dict) -> None:
    missing_location(museum)
    double_presence(museum)
    report = run(museum)
    assert {i.rule_id for i in report.errors} == {"V01"}


def test_critic_only_adds_warnings(museum: dict) -> None:
    from case_validator import Issue

    class NoisyCritic:
        def critique(self, bible):
            return [Issue("X", "error", "동기가 약하다")]

    report = validate(CaseBible.model_validate(museum), critic=NoisyCritic())
    assert report.ok
    assert [i.rule_id for i in report.warnings] == ["L01"]
