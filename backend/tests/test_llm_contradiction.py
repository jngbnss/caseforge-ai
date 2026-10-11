"""LLM 모순 판정 (4-5): 검증·필터, 공개 정보만 쓰는 프롬프트, 비동기 실행, 보드의 rule/llm 구분."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.cases.registry import get_case
from app.core.db import DialogueRow, LlmContradictionRow
from app.core.llm.ports import LLMRaw, Message
from app.core.session import SessionStore
from app.evidence.llm_contradiction import (
    ContradictionFinding,
    accept,
    build_judge_messages,
    judge_turn,
    resolve_evidence,
)
from app.main import create_app

BIBLE = get_case("museum-001").bible


class FakeLLM:
    """정해진 원문을 돌려주고 받은 프롬프트를 기록한다."""

    model_id = "fake"

    def __init__(self, replies: list[dict[str, Any] | str]) -> None:
        self.replies = list(replies)
        self.prompts: list[list[Message]] = []

    async def complete(self, messages, **_: Any) -> LLMRaw:
        self.prompts.append(messages)
        reply = self.replies.pop(0)
        return LLMRaw(reply if isinstance(reply, str) else json.dumps(reply), self.model_id)

    async def stream(self, messages, **_: Any):  # pragma: no cover - not used here
        yield ""


def finding(**kw: Any) -> ContradictionFinding:
    base = {
        "type": "time",
        "statement_turns": [2],
        "evidence_ids": [],
        "confidence": 0.8,
        "quotes": ["담배는 안 피웁니다", "흡연 구역의 꽁초"],
        "explanation": "맞지 않는다.",
    }
    return ContradictionFinding(**{**base, **kw})


TEXTS = {1: "21시 순찰 뒤로는 계속 보안실에 있었습니다.", 2: "담배는 안 피웁니다."}
SHOWN = {"ev-02": "꽁초와 자판기 영수증 옥외 흡연 구역의 꽁초 몇 개, 21:08에 발행된 자판기 영수증"}
STMT_QUOTES = ["담배는 안 피웁니다", "계속 보안실에 있었습니다"]


def test_accept_rejects_made_up_or_weak_findings() -> None:
    ok = lambda f: accept(f, 2, TEXTS, SHOWN)  # noqa: E731
    assert ok(finding(evidence_ids=["ev-02"]))
    assert ok(finding(statement_turns=[1, 2], quotes=STMT_QUOTES))
    assert not ok(finding(statement_turns=[2]))  # 비교 대상 없음
    assert not ok(finding(statement_turns=[1, 9], quotes=STMT_QUOTES))  # 없는 턴
    assert not ok(finding(statement_turns=[1], quotes=STMT_QUOTES))  # 새 진술이 빠짐
    assert not ok(finding(evidence_ids=["ev-04"]))  # 제시 안 한 증거
    assert not ok(finding(evidence_ids=["ev-02"], confidence=0.4))


def test_accept_requires_verbatim_quotes_from_both_sides() -> None:
    ok = lambda f: accept(f, 2, TEXTS, SHOWN)  # noqa: E731
    assert not ok(finding(evidence_ids=["ev-02"], quotes=["담배는 안 피웁니다", "CCTV에 찍혔다"]))
    assert not ok(finding(evidence_ids=["ev-02"], quotes=["담배는 안 피웁니다", "안 피웁니다"]))
    assert not ok(finding(statement_turns=[1, 2], quotes=["계속 보안실에", "순찰 뒤로는"]))
    assert ok(finding(evidence_ids=["ev-02"], quotes=["“담배는 안 피웁니다.”", "21:08에 발행된"]))


@pytest.fixture
def judged_session(tmp_path):
    """박도현에게 영수증을 제시하고 진술 2개를 남긴 세션."""
    app = create_app(f"sqlite:///{tmp_path / 'j.db'}", llm_contradictions=False)
    with app.state.sessionmaker() as db:
        store = SessionStore(db)
        session = store.create("museum-001")
        session.state.collected += ["ev-01", "ev-02"]
        session.state.presented["suspect-02"] = ["ev-02"]
        store.save(session)
        for turn, text in (
            (1, "21시 순찰 뒤로는 계속 보안실에 있었습니다."),
            (2, "담배는 안 피웁니다."),
        ):
            db.add_all(
                [
                    DialogueRow(
                        session_id=session.id,
                        npc_id="suspect-02",
                        turn=turn,
                        role="player",
                        text="어디 있었어요?",
                    ),
                    DialogueRow(
                        session_id=session.id, npc_id="suspect-02", turn=turn, role="npc", text=text
                    ),
                ]
            )
        db.commit()
        yield db, session


def test_judge_keeps_only_grounded_findings_and_dedupes(judged_session) -> None:
    db, session = judged_session
    reply = {
        "findings": [
            finding(statement_turns=[1, 2], type="statement", quotes=STMT_QUOTES).model_dump(),
            finding(evidence_ids=["ev-02"]).model_dump(),
            finding(evidence_ids=["ev-01"]).model_dump(),  # 이 NPC에게 제시하지 않은 증거
            finding(statement_turns=[2, 7], quotes=STMT_QUOTES).model_dump(),  # 없는 턴
        ]
    }
    llm = FakeLLM([reply, reply])
    saved = asyncio.run(judge_turn(llm, db, session, "suspect-02", 2, verify=False))
    assert [(r.statement_turns, r.evidence_ids, r.type) for r in saved] == [
        ([1, 2], [], "statement"),
        ([2], ["ev-02"], "time"),
    ]
    assert all(r.confidence == 0.8 and r.model_id == "fake" for r in saved)
    again = asyncio.run(judge_turn(llm, db, session, "suspect-02", 2, verify=False))
    assert again == []  # 같은 판정은 1번만


def test_judge_drops_findings_the_check_can_explain(judged_session) -> None:
    db, session = judged_session
    reply = {
        "findings": [
            finding(statement_turns=[1, 2], type="statement", quotes=STMT_QUOTES).model_dump(),
            finding(evidence_ids=["ev-02"]).model_dump(),
        ]
    }
    base = {"claim_a": "계속 보안실", "claim_b": "21:08 흡연 구역", "same_person_time_place": True}
    explained = {**base, "contradiction": False}
    confirmed = {**base, "contradiction": True}
    llm = FakeLLM([reply, explained, confirmed])
    saved = asyncio.run(judge_turn(llm, db, session, "suspect-02", 2, verify=True))
    assert [(r.statement_turns, r.evidence_ids) for r in saved] == [([2], ["ev-02"])]
    check = "\n".join(m.content for m in llm.prompts[1])
    assert "21시 순찰 뒤로는 계속 보안실에 있었습니다." in check
    assert "fact-" not in check and "lie-" not in check


def test_judge_drops_finding_when_check_output_is_invalid(judged_session) -> None:
    db, session = judged_session
    reply = {"findings": [finding(evidence_ids=["ev-02"]).model_dump()]}
    llm = FakeLLM([reply, "not json", "still not json"])
    assert asyncio.run(judge_turn(llm, db, session, "suspect-02", 2, verify=True)) == []


def test_invalid_judge_output_is_retried_then_dropped(judged_session) -> None:
    db, session = judged_session
    llm = FakeLLM(["not json", '{"findings": [{"type": "weird"}]}'])
    assert asyncio.run(judge_turn(llm, db, session, "suspect-02", 2, verify=True)) == []
    assert len(llm.prompts) == 2  # 1회 재요청 후 기본값(판정 없음)


def test_judge_prompt_contains_only_public_information(judged_session) -> None:
    db, session = judged_session
    llm = FakeLLM([{"findings": []}])
    asyncio.run(judge_turn(llm, db, session, "suspect-02", 2))
    prompt = "\n".join(m.content for m in llm.prompts[0])
    assert "fact-" not in prompt and "lie-" not in prompt
    for fact in BIBLE.facts:
        assert fact.content not in prompt
    for lie in BIBLE.lies:
        assert lie.claim not in prompt
    assert BIBLE.suspect(BIBLE.solution.culprit_id).name not in prompt
    ev = BIBLE.evidence_by_id("ev-02")
    assert ev.description in prompt  # 제시한 증거의 공개 설명은 들어간다
    assert "ev-01" not in prompt  # 수집했지만 이 NPC에게 보여 주지 않은 증거는 빠진다


def test_judge_skips_model_when_nothing_to_compare(judged_session) -> None:
    db, session = judged_session
    session.state.presented["suspect-02"] = []
    llm = FakeLLM([])
    assert asyncio.run(judge_turn(llm, db, session, "suspect-02", 1)) == []
    assert llm.prompts == []


def test_judge_prompt_names_the_npc() -> None:
    msgs = build_judge_messages("suspect-01", "한서윤", (1, "a"), [], [])
    assert "NPC_ID: suspect-01" in msgs[1].content


# ---------- API: 비동기 실행과 보드 표시 ----------


@pytest.fixture
def client(tmp_path) -> TestClient:
    return TestClient(create_app(f"sqlite:///{tmp_path / 'api.db'}"))


def test_board_shows_llm_findings_after_rule_findings(client: TestClient) -> None:
    sid = client.post("/sessions", json={}).json()["session_id"]

    def ok(method: str, url: str, **kw: Any) -> Any:
        r = client.request(method, f"/sessions/{sid}{url}", **kw)
        assert r.status_code == 200, (url, r.text)
        return r.json()

    for eid in ("ev-01", "ev-02", "ev-03"):
        ok("POST", f"/evidence/{eid}/collect")
    ok("POST", "/puzzles/pz-03/attempt", json={"answer": ["p-time", "p-room", "p-locker"]})

    # 박도현: 출입 로그를 보여 준 뒤 거짓말 → 규칙에는 없는 '소지품' 모순 (LLM)
    ok("POST", "/npcs/suspect-02/present", json={"evidence_id": "ev-01"})
    card = ok("POST", "/npcs/suspect-02/ask", json={"question": "카드는 어디 있었어요?"})
    assert "보안실에 있었" in card["answer"]

    # 윤재민: 앞뒤 진술 불일치 (LLM) + 메모로 거짓말이 깨짐 (규칙)
    ok("POST", "/npcs/suspect-03/ask", json={"question": "21시에 어디 있었어요?"})
    ok("POST", "/npcs/suspect-03/present", json={"evidence_id": "rec-03"})
    later = ok("POST", "/npcs/suspect-03/ask", json={"question": "21시에 어디 있었어요?"})
    assert "휴게실" in later["answer"]

    board = ok("GET", "/board")
    sources = [c["source"] for c in board["contradictions"]]
    assert "llm" in sources and "rule" in sources
    assert sources == sorted(sources, key=lambda s: s != "rule")  # 규칙 판정이 먼저

    llm = [c for c in board["contradictions"] if c["source"] == "llm"]
    by_npc = {c["npc_id"]: c for c in llm}
    assert by_npc["suspect-02"]["type"] == "possession"
    assert by_npc["suspect-02"]["evidence_id"] == "ev-01"
    assert by_npc["suspect-02"]["confidence"] == pytest.approx(0.74)
    assert by_npc["suspect-03"]["type"] == "statement"
    assert by_npc["suspect-03"]["evidence_id"] is None
    assert "한 번도 안 나갔" in by_npc["suspect-03"]["other_statements"][0]
    assert all(c["explanation"] for c in llm)
    rule = [c for c in board["contradictions"] if c["source"] == "rule"]
    assert all(c["confidence"] is None for c in rule)


def test_llm_duplicate_of_a_rule_finding_is_hidden(client: TestClient) -> None:
    sid = client.post("/sessions", json={}).json()["session_id"]
    client.post(f"/sessions/{sid}/evidence/ev-01/collect")
    client.post(f"/sessions/{sid}/npcs/suspect-01/ask", json={"question": "21시에 어디 있었어요?"})
    with client.app.state.sessionmaker() as db:
        db.add(
            LlmContradictionRow(
                session_id=sid,
                npc_id="suspect-01",
                statement_turn=1,
                statement_turns=[1],
                evidence_ids=["ev-01"],
                type="location",
                confidence=0.9,
                explanation="중복",
                model_id="fake",
            )
        )
        db.commit()
    board = client.get(f"/sessions/{sid}/board").json()
    pairs = [(c["npc_id"], c["evidence_id"], c["source"]) for c in board["contradictions"]]
    assert ("suspect-01", "ev-01", "rule") in pairs
    assert ("suspect-01", "ev-01", "llm") not in pairs


def test_judgement_runs_after_the_websocket_reply(client: TestClient) -> None:
    sid = client.post("/sessions", json={}).json()["session_id"]
    client.post(f"/sessions/{sid}/evidence/ev-01/collect")
    client.post(f"/sessions/{sid}/npcs/suspect-02/present", json={"evidence_id": "ev-01"})
    with client.websocket_connect(f"/ws/interrogation/{sid}/suspect-02") as ws:
        ws.send_json({"question": "카드는 어디 있었어요?"})
        while (msg := ws.receive_json())["type"] != "final":
            assert msg["type"] == "delta"
    with client.app.state.sessionmaker() as db:
        for _ in range(100):  # 백그라운드 작업이 끝날 때까지 잠깐 기다린다
            rows = db.scalars(
                select(LlmContradictionRow).where(LlmContradictionRow.session_id == sid)
            ).all()
            if rows:
                break
            time.sleep(0.02)
    assert [(r.npc_id, r.type) for r in rows] == [("suspect-02", "possession")]


def test_evasion_lines_and_disabled_setting_are_not_judged(tmp_path) -> None:
    client = TestClient(create_app(f"sqlite:///{tmp_path / 'off.db'}", llm_contradictions=False))
    sid = client.post("/sessions", json={}).json()["session_id"]
    client.post(f"/sessions/{sid}/evidence/ev-01/collect")
    client.post(f"/sessions/{sid}/npcs/suspect-02/present", json={"evidence_id": "ev-01"})
    client.post(f"/sessions/{sid}/npcs/suspect-02/ask", json={"question": "카드는 어디 있었어요?"})
    board = client.get(f"/sessions/{sid}/board").json()
    assert all(c["source"] == "rule" for c in board["contradictions"])


def test_quoted_evidence_is_resolved_to_its_id() -> None:
    """EXP-001: 모델이 증거를 그대로 인용하고 evidence_ids를 비운 경우."""
    f = finding(evidence_ids=[], quotes=["담배는 안 피웁니다", "21:08에 발행된 자판기 영수증"])
    assert not accept(f, 2, TEXTS, SHOWN)
    resolved = resolve_evidence(f, 2, TEXTS, SHOWN)
    assert resolved.evidence_ids == ["ev-02"]
    assert accept(resolved, 2, TEXTS, SHOWN)
    # 진술 쪽 인용만 있으면 증거를 붙이지 않는다
    same = finding(statement_turns=[1, 2], evidence_ids=[], quotes=STMT_QUOTES)
    assert resolve_evidence(same, 2, TEXTS, SHOWN).evidence_ids == []
    # 아무 원문에도 없는 인용은 증거로 바뀌지 않는다
    made_up = finding(evidence_ids=[], quotes=["담배는 안 피웁니다", "CCTV에 찍혔다"])
    assert resolve_evidence(made_up, 2, TEXTS, SHOWN).evidence_ids == []
