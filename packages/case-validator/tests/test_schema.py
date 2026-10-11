import shutil

import pytest
from materialize import MUSEUM_001
from pydantic import ValidationError

from case_validator import CaseBible, CaseLoadError, load_case
from case_validator.schema import AllOf, EvidencePresented, Fact, TimeRange, TrustGte


def test_museum_loads_with_expected_shape(museum):
    bible = museum.bible
    assert bible.case_id == "museum-001"
    assert [s.suspect_id for s in bible.suspects] == ["suspect-01", "suspect-02", "suspect-03"]
    assert {e.evidence_id for e in bible.evidence} == {
        "ev-01",
        "ev-02",
        "ev-03",
        "ev-04",
        "ev-05",
        "rec-01",
        "rec-02",
        "rec-03",
    }
    assert [p.puzzle_id for p in bible.puzzles] == ["pz-01", "pz-02", "pz-03"]
    assert len(bible.lies) == 3
    assert bible.solution.culprit_id == "suspect-03"


def test_puzzle_answers_match_proposal(museum):
    puzzles = {p.puzzle_id: p for p in museum.bible.puzzles}
    assert puzzles["pz-02"].answer == "0784"
    memo = puzzles["pz-03"]
    labels = {item.item_id: item.label for item in memo.items}
    assert " ".join(labels[i] for i in memo.answer) == "21:10 휴게실 — 사물함 3번"
    assert len(puzzles["pz-01"].answer) == 4


def test_every_fact_has_provenance_and_culprit_facts_are_forbidden(museum):
    facts = {f.fact_id: f for f in museum.bible.facts}
    for fact in facts.values():
        assert fact.source
    for fid in ("fact-011", "fact-012"):  # 21:12 entry, 21:14 swap
        assert facts[fid].known_by == ("suspect-03",)
        assert facts[fid].leak_forbidden


def test_dialogues_are_merged(museum):
    for suspect in museum.bible.suspects:
        assert len(suspect.dialogue.sample_lines) == 5
        assert len(suspect.dialogue.evasion_lines) == 3


def test_bible_is_frozen(museum):
    with pytest.raises(ValidationError):
        museum.bible.title = "changed"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        museum.bible.suspects.append(None)  # type: ignore[attr-defined]


def test_hash_is_stable_and_content_sensitive(museum, tmp_path):
    assert len(museum.sha256) == 64
    assert load_case(MUSEUM_001).sha256 == museum.sha256

    copy = shutil.copytree(MUSEUM_001, tmp_path / "case")
    solution = copy / "solution.yaml"
    solution.write_text(
        solution.read_text(encoding="utf-8").replace(
            "culprit_id: suspect-03", "culprit_id: suspect-02"
        ),
        encoding="utf-8",
    )
    assert load_case(copy).sha256 != museum.sha256


def test_time_range_parsing():
    assert TimeRange.model_validate("21:12").is_instant
    span = TimeRange.model_validate({"start": "21:04", "end": "21:07"})
    assert (span.start_min, span.end_min) == (21 * 60 + 4, 21 * 60 + 7)
    assert not span.overlaps(TimeRange.model_validate("21:07"))  # half-open
    assert span.touches(TimeRange.model_validate("21:07"))  # closed
    with pytest.raises(ValidationError):
        TimeRange.model_validate("25:00")
    with pytest.raises(ValidationError):
        TimeRange.model_validate({"start": "21:10", "end": "21:00"})


def test_condition_dsl_parses_to_typed_atoms():
    fact = Fact.model_validate(
        {
            "fact_id": "f",
            "content": "c",
            "kind": "truth",
            "source": "s",
            "known_by": [],
            "unlock_condition": {"all": [{"evidence_presented": "ev-03"}, {"trust_gte": 2}]},
        }
    )
    cond = fact.unlock_condition
    assert isinstance(cond, AllOf)
    assert isinstance(cond.all[0], EvidencePresented)
    assert isinstance(cond.all[1], TrustGte)
    with pytest.raises(ValidationError):
        Fact.model_validate({**fact.model_dump(), "unlock_condition": {"bogus": 1}})


def test_unknown_fields_are_rejected(museum):
    data = museum.bible.model_dump()
    data["solution"]["answer_leak"] = True
    with pytest.raises(ValidationError):
        CaseBible.model_validate(data)


def test_missing_file_and_missing_dialogue(tmp_path):
    copy = shutil.copytree(MUSEUM_001, tmp_path / "case")
    (copy / "dialogues" / "suspect-02.yaml").unlink()
    with pytest.raises(CaseLoadError, match="suspect-02"):
        load_case(copy)
    (copy / "puzzles.yaml").unlink()
    with pytest.raises(CaseLoadError, match="puzzles.yaml"):
        load_case(copy)
