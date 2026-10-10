from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.agents.streaming import AnswerExtractor
from app.core.llm.ports import LLMRaw
from app.main import create_app


@pytest.mark.parametrize("size", [1, 2, 3, 7, 1000])
def test_extractor_handles_any_chunk_boundary(size: int) -> None:
    answer = '줄바꿈\n과 "따옴표", 역슬래시\\ 그리고 é 유니코드'
    raw = json.dumps({"emotion": "calm", "answer": answer, "trust_delta": 0})
    raw = raw.replace("é", "\\u00e9")
    ex = AnswerExtractor()
    out = "".join(ex.feed(raw[i : i + size]) for i in range(0, len(raw), size))
    assert out == answer
    assert ex.done
    assert ex.raw == raw


def test_extractor_waits_for_answer_key() -> None:
    ex = AnswerExtractor()
    assert ex.feed('{"emotion": "calm", "ans') == ""
    assert ex.feed('wer": "안') == "안"
    assert ex.feed('녕"}') == "녕"


@pytest.fixture
def client(tmp_path) -> TestClient:
    return TestClient(create_app(f"sqlite:///{tmp_path / 'ws.db'}", debug_api=True))


def test_websocket_streams_deltas_then_final(client: TestClient) -> None:
    sid = client.post("/sessions", json={}).json()["session_id"]
    with client.websocket_connect(f"/ws/interrogation/{sid}/suspect-02") as ws:
        ws.send_json({"question": "21시 이후에 어디 있었어요?"})
        deltas = []
        while True:
            msg = ws.receive_json()
            if msg["type"] == "delta":
                deltas.append(msg["text"])
            else:
                break
        assert msg["type"] == "final"
        assert len(deltas) > 1
        assert "".join(deltas) == msg["answer"]
        assert msg["debug"]["used_lie_ids"] == ["lie-02"]

        ws.send_json({"question": ""})
        assert ws.receive_json()["type"] == "error"

    # 스트리밍으로 진행한 턴도 세션 상태에 저장된다
    board = client.get(f"/sessions/{sid}/board").json()
    assert board["statements"][0]["question"] == "21시 이후에 어디 있었어요?"


def test_websocket_unknown_npc_reports_error(client: TestClient) -> None:
    sid = client.post("/sessions", json={}).json()["session_id"]
    with client.websocket_connect(f"/ws/interrogation/{sid}/suspect-99") as ws:
        ws.send_json({"question": "누구세요?"})
        msg = ws.receive_json()
        assert msg == {"type": "error", "detail": "용의자 suspect-99가 없다"}


class LeakyStreamLLM:
    """스트리밍 답변에서 범인 전용 사실을 흘리고, 재생성 때는 깨끗한 답을 낸다."""

    model_id = "leaky-stream"

    async def stream(self, messages, **_):
        body = json.dumps(
            {"revealed_fact_ids": ["fact-042"], "answer": "제가 바꿔치기했어요."},
            ensure_ascii=False,
        )
        for i in range(0, len(body), 5):
            yield body[i : i + 5]

    async def complete(self, messages, **_) -> LLMRaw:
        return LLMRaw(
            json.dumps({"answer": "복원실에 있었어요."}, ensure_ascii=False), self.model_id
        )


def test_websocket_final_replaces_blocked_stream(tmp_path) -> None:
    llm = LeakyStreamLLM()
    client = TestClient(create_app(f"sqlite:///{tmp_path / 'leak.db'}", llm_for_case=lambda _: llm))
    sid = client.post("/sessions", json={}).json()["session_id"]
    with client.websocket_connect(f"/ws/interrogation/{sid}/suspect-03") as ws:
        ws.send_json({"question": "뭐 했어요?"})
        streamed = ""
        while (msg := ws.receive_json())["type"] == "delta":
            streamed += msg["text"]
    assert "바꿔치기" not in streamed  # 범위 밖 ID가 먼저 나와 스트리밍 자체를 막는다
    assert msg["answer"] == "복원실에 있었어요."  # 최종 답변은 가드를 통과한 것
    assert msg["revealed_fact_ids"] == []


class CanaryStreamLLM(LeakyStreamLLM):
    """ID는 깨끗하지만 답변 글자에 범인 전용 키워드를 흘린다."""

    async def stream(self, messages, **_):
        body = json.dumps(
            {
                "revealed_fact_ids": [],
                "answer": "그날 밤 제가 진열장에서 바꿔치기했어요. 죄송해요.",
            },
            ensure_ascii=False,
        )
        for i in range(0, len(body), 3):
            yield body[i : i + 3]


def test_stream_stops_before_canary_keyword_is_shown(tmp_path) -> None:
    llm = CanaryStreamLLM()
    client = TestClient(create_app(f"sqlite:///{tmp_path / 'c.db'}", llm_for_case=lambda _: llm))
    sid = client.post("/sessions", json={}).json()["session_id"]
    with client.websocket_connect(f"/ws/interrogation/{sid}/suspect-03") as ws:
        ws.send_json({"question": "뭐 했어요?"})
        streamed = ""
        while (msg := ws.receive_json())["type"] == "delta":
            streamed += msg["text"]
    assert "바꿔" not in streamed  # 키워드 앞부분도 나가지 않는다
    assert streamed.startswith("그날 밤")
    assert msg["answer"] == "복원실에 있었어요."
