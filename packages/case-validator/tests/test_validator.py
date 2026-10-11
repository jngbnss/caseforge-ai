import json

import pytest
from materialize import MUSEUM_001, fixture_names, load_patch, materialize

from case_validator import load_case, validate
from case_validator.cli import main
from case_validator.puzzles import solve


def test_museum_passes_every_rule(museum):
    report = validate(museum.bible, sha256=museum.sha256)
    assert report.errors == [], report.errors
    suspects = report.metrics["suspects"]
    assert suspects["suspect-03"] == {"opportunity": True, "means": True, "evidence_chain": True}
    assert not suspects["suspect-01"]["opportunity"]
    assert not suspects["suspect-02"]["opportunity"]
    assert report.metrics["puzzle_solution_counts"] == {"pz-01": 1, "pz-02": 1, "pz-03": 1}
    assert set(report.metrics["reachable_evidence"]) >= set(museum.bible.solution.key_evidence)


def test_puzzle_search_finds_exactly_the_stored_answers(museum):
    for puzzle in museum.bible.puzzles:
        solutions = solve(puzzle)
        assert len(solutions) == 1
        expected = puzzle.answer if isinstance(puzzle.answer, str) else tuple(puzzle.answer)
        assert solutions[0] == expected


def test_fixture_set_covers_every_deterministic_rule():
    covered = {rule for name in fixture_names() for rule in load_patch(name)["expect"]}
    expected = {f"V0{i}" for i in range(1, 8)} | {"T01", "T02", "T03", "U01", "U02"}
    assert expected <= covered


@pytest.mark.parametrize("name", fixture_names())
def test_broken_fixture_fails_exactly_the_expected_rules(name, tmp_path):
    case_dir = materialize(name, tmp_path)
    report = validate(load_case(case_dir).bible)
    assert report.failed_rules() == set(load_patch(name)["expect"]), [
        f"{e.rule_id}: {e.message}" for e in report.errors
    ]


def test_cli_exit_codes(tmp_path, capsys):
    assert main(["check", str(MUSEUM_001)]) == 0
    assert "[PASS] museum-001" in capsys.readouterr().out

    broken = materialize("broken-t01", tmp_path)
    assert main(["check", str(broken), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert {e["rule_id"] for e in payload["errors"]} == {"T01"}


def test_cli_reports_load_and_schema_errors(tmp_path, capsys):
    assert main(["check", str(tmp_path / "missing")]) == 1
    assert "LOAD" in capsys.readouterr().out

    broken = materialize("broken-v01", tmp_path)
    (broken / "solution.yaml").write_text("solution: {culprit_id: x}\n", encoding="utf-8")
    assert main(["check", str(broken)]) == 1
    assert "SCHEMA" in capsys.readouterr().out
