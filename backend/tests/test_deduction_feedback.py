"""추리 서술 LLM 피드백 (4-6): 원문 인용 검증, 정답 미제공, 비동기 생성, 점수와 분리."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.cases.registry import get_case
from app.core.llm.ports import LLMRaw
from app.core.session import DeductionRecord
from app.deduction.feedback import (
    DeductionFeedback,
    EvidenceLink,
    build_feedback_messages,
    ground,
    make_feedback,
)
from app.main import create_app

BIBLE = get_case("museum-001").bible
NARRATIVE = (
    "윤재민이 범인이다. 복원된 메모에 21:10 휴게실이라고 적혀 있다. "
    "그는 틀림없이 처음부터 보석을 노렸다. 그는 수집가와 미리 짜고 있었다."
)


class FakeLLM:
    model_id = "fake"

    def __init__(self, replies: list[Any]) -> None:
        self.replies = list(replies)
        self.prompts: list[Any] = []

    async def complete(self, messages, **_: Any) -> LLMRaw:
        self.prompts.append(messages)
        r = self.replies.pop(0)
        return LLMRaw(r if isinstance(r, str) else json.dumps(r, ensure_ascii=False), "fake")

    async def stream(self, messages, **_: Any):  # pragma: no cover
        yield ""


def record(narrative: str = NARRATIVE, evidence: list[str] | None = None) -> DeductionRecord:
    return DeductionRecord(
        culprit_id="suspect-03",
        motive_id=BIBLE.deduction_options.motives[0].id,
        method_id=BIBLE.deduction_options.methods[0].id,
        evidence_ids=evidence if evidence is not None else ["rec-03"],
        narrative=narrative,
        scores={"culprit": 40, "motive": 0, "method": 0, "evidence": 5},
        total=45,
        flags={},
    )


def test_ground_keeps_only_verbatim_quotes_and_submitted_evidence() -> None:
    fb = DeductionFeedback(
        unsupported_claims=["그는 수집가와 미리 짜고 있었다.", "윤재민은 돈이 필요했다"],
        logical_leaps=["그는  틀림없이 처음부터 보석을 노렸다"],  # 공백 차이는 허용
        evidence_links=[
            EvidenceLink(claim="복원된 메모에 21:10 휴게실이라고 적혀 있다", evidence_id="rec-03"),
            EvidenceLink(claim="윤재민이 범인이다", evidence_id="ev-04"),  # 제출하지 않은 증거
        ],
    )
    out = ground(fb, NARRATIVE, ["rec-03"])
    assert out["unsupported_claims"] == ["그는 수집가와 미리 짜고 있었다."]
    assert out["logical_leaps"] == ["그는  틀림없이 처음부터 보석을 노렸다"]
    assert out["evidence_links"] == [
        {"claim": "복원된 메모에 21:10 휴게실이라고 적혀 있다", "evidence_id": "rec-03"}
    ]


def test_feedback_prompt_has_no_solution() -> None:
    msgs = build_feedback_messages(BIBLE, record())
    prompt = "\n".join(m.content for m in msgs)
    sol = BIBLE.solution
    for fid in sol.method_steps:
        fact = BIBLE.fact(fid)
        assert fact is not None and fact.content not in prompt
    assert "key" not in prompt.lower().split("json")[0]  # 증거 역할 표기 없음
    assert "red_herring" not in prompt
    motives = {o.id: o.text for o in BIBLE.deduction_options.motives}
    if record().motive_id != sol.motive_id:
        assert motives[sol.motive_id] not in prompt
    assert NARRATIVE in prompt


def test_empty_narrative_skips_the_model() -> None:
    llm = FakeLLM([])
    out = asyncio.run(make_feedback(llm, BIBLE, record(narrative="  ")))
    assert out.status == "skipped" and llm.prompts == []


def test_invalid_output_twice_is_unavailable() -> None:
    llm = FakeLLM(["nope", '{"logical_leaps": 3}'])
    out = asyncio.run(make_feedback(llm, BIBLE, record()))
    assert out.status == "unavailable" and len(llm.prompts) == 2


def test_dropped_items_are_counted() -> None:
    llm = FakeLLM(
        [{"unsupported_claims": ["지어낸 문장"], "logical_leaps": [], "evidence_links": []}]
    )
    out = asyncio.run(make_feedback(llm, BIBLE, record()))
    assert out.status == "ready" and out.dropped == 1 and out.unsupported_claims == []


# ---------- API ----------


def play_and_submit(client: TestClient, narrative: str) -> tuple[str, dict]:
    sid = client.post("/sessions", json={}).json()["session_id"]
    for eid in ("ev-03", "ev-04"):
        assert client.post(f"/sessions/{sid}/evidence/{eid}/collect").status_code == 200
    r = client.post(
        f"/sessions/{sid}/puzzles/pz-03/attempt", json={"answer": ["p-time", "p-room", "p-locker"]}
    )
    assert r.json()["correct"]
    sub = {
        "culprit_id": BIBLE.solution.culprit_id,
        "motive_id": BIBLE.solution.motive_id,
        "method_id": BIBLE.solution.method_id,
        "evidence_ids": ["ev-03", "ev-04", "rec-03"],
        "narrative": narrative,
    }
    result = client.post(f"/sessions/{sid}/deduction", json=sub)
    assert result.status_code == 200, result.text
    return sid, result.json()


@pytest.fixture
def client(tmp_path) -> TestClient:
    return TestClient(create_app(f"sqlite:///{tmp_path / 'fb.db'}"))


def test_debrief_shows_feedback_without_changing_the_score(client: TestClient) -> None:
    sid, result = play_and_submit(client, NARRATIVE)
    debrief = client.get(f"/sessions/{sid}/debrief").json()
    fb = debrief["feedback"]
    assert fb["status"] == "ready"
    assert fb["evidence_links"] == [
        {
            "claim": "복원된 메모에 21:10 휴게실이라고 적혀 있다.",
            "evidence_id": "rec-03",
            "evidence_name": BIBLE.evidence_by_id("rec-03").name,
        }
    ]
    assert fb["logical_leaps"] == ["그는 틀림없이 처음부터 보석을 노렸다."]
    assert "그는 수집가와 미리 짜고 있었다." in fb["unsupported_claims"]
    assert debrief["narrative"] == NARRATIVE
    assert debrief["result"]["total"] == result["total"]  # 피드백은 점수를 바꾸지 않는다


def test_no_narrative_means_no_feedback(client: TestClient) -> None:
    sid, _ = play_and_submit(client, "")
    assert client.get(f"/sessions/{sid}/debrief").json()["feedback"]["status"] == "skipped"


def test_feedback_can_be_turned_off(tmp_path) -> None:
    client = TestClient(create_app(f"sqlite:///{tmp_path / 'off.db'}", deduction_feedback=False))
    sid, _ = play_and_submit(client, NARRATIVE)
    assert client.get(f"/sessions/{sid}/debrief").json()["feedback"]["status"] == "off"
