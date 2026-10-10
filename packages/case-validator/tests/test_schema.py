from __future__ import annotations

import pytest
from pydantic import ValidationError

from case_validator import CaseBible, PlayState, evaluate, load_case
from case_validator.loader import CaseLoadError, bible_hash
from case_validator.schema import OrderClue, TimeRange
from conftest import MUSEUM_DIR, find


def test_load_museum() -> None:
    loaded = load_case(MUSEUM_DIR)
    bible = loaded.bible
    assert bible.case_id == "museum-001"
    assert len(bible.suspects) == 3
    assert len([e for e in bible.evidence if e.source == "scene"]) == 5
    assert len(bible.puzzles) == 3
    assert len(bible.dialogues) == 3
    assert loaded.sha256 == bible_hash(bible)


def test_hash_is_stable_and_content_sensitive(museum: dict) -> None:
    a = bible_hash(CaseBible.model_validate(museum))
    b = bible_hash(CaseBible.model_validate(museum))
    assert a == b
    museum["title"] = "다른 제목"
    assert bible_hash(CaseBible.model_validate(museum)) != a


def test_bible_is_frozen() -> None:
    bible = load_case(MUSEUM_DIR).bible
    with pytest.raises(ValidationError):
        bible.title = "바뀐 제목"  # type: ignore[misc]
    assert isinstance(bible.suspects, tuple)
    assert isinstance(bible.solution.key_evidence, tuple)


def test_rejects_bad_clock() -> None:
    with pytest.raises(ValidationError):
        TimeRange(start="25:00", end="25:10")
    with pytest.raises(ValidationError):
        TimeRange(start="21:10", end="21:00")


def test_rejects_duplicate_ids(museum: dict) -> None:
    museum["evidence"].append(dict(find(museum["evidence"], "evidence_id", "ev-01")))
    with pytest.raises(ValidationError, match="중복된 evidence ID"):
        CaseBible.model_validate(museum)


def test_rejects_unknown_field(museum: dict) -> None:
    museum["solution"]["secret_note"] = "x"
    with pytest.raises(ValidationError):
        CaseBible.model_validate(museum)


def test_order_clue_shape() -> None:
    OrderClue(before="a", after="b")
    OrderClue(first="a")
    with pytest.raises(ValidationError):
        OrderClue(before="a")
    with pytest.raises(ValidationError):
        OrderClue(first="a", last="b")


def test_missing_file(tmp_path) -> None:
    with pytest.raises(CaseLoadError):
        load_case(tmp_path)


def test_condition_evaluate() -> None:
    bible = load_case(MUSEUM_DIR).bible
    sec02 = next(s for s in bible.secrets if s.secret_id == "sec-02")
    fact031 = bible.fact("fact-031")
    assert fact031 is not None

    state = PlayState(collected={"ev-02"})
    assert not evaluate(sec02.reveal_when, state)
    state.presented["suspect-01"] = {"ev-02"}
    assert not evaluate(sec02.reveal_when, state)  # 다른 NPC에게 제시함
    state.presented["suspect-02"] = {"ev-02"}
    assert evaluate(sec02.reveal_when, state)

    assert not evaluate(fact031.unlock_condition, state)
    state.trust["suspect-01"] = 1
    assert evaluate(fact031.unlock_condition, state)
    assert evaluate(None, state)
