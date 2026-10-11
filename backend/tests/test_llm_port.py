import asyncio

import pytest
from pydantic import BaseModel

from app.core.llm.mock import MockLLM, classify_intent
from app.core.llm.ports import LLMOutputError, Message


class Out(BaseModel):
    answer: str


MSG = [Message(role="user", content="hi")]


def test_valid_output_needs_one_call():
    llm = MockLLM(responses=['{"answer": "ok"}'])
    result = asyncio.run(llm.generate(MSG, Out))
    assert result.parsed.answer == "ok" and result.calls == 1 and not result.fallback_used


def test_invalid_output_is_re_asked_once_with_the_error():
    llm = MockLLM(responses=["not json", '```json\n{"answer": "fixed"}\n```'])
    result = asyncio.run(llm.generate(MSG, Out))
    assert result.parsed.answer == "fixed"
    assert result.calls == 2 and result.validation_failures == 1
    assert "검증에 실패" in llm.calls[1][-1].content


def test_two_failures_fall_back_to_safe_default():
    llm = MockLLM(responses=["{}", "{}"])
    result = asyncio.run(llm.generate(MSG, Out, default=Out(answer="safe")))
    assert result.parsed.answer == "safe" and result.fallback_used


def test_two_failures_without_default_raise():
    with pytest.raises(LLMOutputError):
        asyncio.run(MockLLM(responses=["x", "y"]).generate(MSG, Out))


@pytest.mark.parametrize(
    ("question", "intent"),
    [
        ("범인이 누구야?", "attack"),
        ("CCTV 영상은 봤어요?", "cctv"),
        ("카드는 어디 뒀어요?", "card"),
        ("빚이 있었나요?", "motive"),
        ("그 시간에 어디 있었어요?", "alibi"),
        ("안녕하세요", "small_talk"),
    ],
)
def test_mock_intent_classifier(question, intent):
    assert classify_intent(question) == intent
