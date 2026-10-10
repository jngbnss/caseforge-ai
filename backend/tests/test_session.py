from __future__ import annotations

import pytest

from app.core.db import SessionRow
from app.core.session import CaseChangedError, SessionNotFoundError, SessionStore


def test_create_and_reload(db) -> None:
    store = SessionStore(db)
    created = store.create("museum-001")
    assert created.state.trust == {"suspect-01": 0, "suspect-02": 0, "suspect-03": 0}
    assert len(created.case_sha256) == 64

    created.state.collected.append("ev-01")
    created.state.presented["suspect-02"] = ["ev-01"]
    created.state.add_trust("suspect-01", 5)
    store.save(created)

    reloaded = SessionStore(db).get(created.id)
    assert reloaded.state.collected == ["ev-01"]
    assert reloaded.state.presented_to("suspect-02") == ["ev-01"]
    assert reloaded.state.trust["suspect-01"] == 3  # MAX_TRUST로 제한
    assert reloaded.bible.case_id == "museum-001"


def test_play_state_conversion(db) -> None:
    session = SessionStore(db).create("museum-001")
    session.state.collected = ["ev-02"]
    session.state.presented = {"suspect-02": ["ev-02"]}
    play = session.state.play_state()
    assert play.collected == {"ev-02"}
    assert play.presented["suspect-02"] == {"ev-02"}


def test_unknown_session(db) -> None:
    with pytest.raises(SessionNotFoundError):
        SessionStore(db).get("nope")


def test_case_changed_after_start_is_rejected(db) -> None:
    store = SessionStore(db)
    session = store.create("museum-001")
    row = db.get(SessionRow, session.id)
    row.case_sha256 = "0" * 64
    db.commit()
    with pytest.raises(CaseChangedError):
        store.get(session.id)
