"""MockLLM: deterministic, fixture-scripted replies for CI and offline play.

It reads only what a real model would see (the <context> and <player_question> blocks of
the prompt), classifies the question by keyword, and picks the first matching script entry.
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from app.core.llm.ports import ChatReply, Message, StructuredLLM, Usage

INTENT_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    # attack first: it must win over topical words in the same sentence
    (
        "attack",
        (
            "시스템",
            "프롬프트",
            "지시",
            "무시",
            "범인",
            "정답",
            "비밀",
            "역할",
            "ignore",
            "system",
            "prompt",
            "규칙",
        ),
    ),
    ("cctv", ("cctv", "카메라", "녹화", "영상", "모니터", "단말")),
    ("card", ("카드", "출입", "수장고", "로그", "사물함")),
    ("motive", ("빚", "돈", "채무", "이직", "도박", "사정", "개인적", "동기", "왜")),
    ("jewel", ("보석", "다이아", "푸른 별", "모조품", "진열장", "감정")),
    (
        "colleague",
        ("동료", "한서윤", "박도현", "윤재민", "큐레이터", "경비원", "복원가", "다른 사람"),
    ),
    (
        "alibi",
        (
            "어디",
            "알리바이",
            "뭐 했",
            "뭘 했",
            "무엇을",
            "행방",
            "그 시간",
            "몇 시",
            "시에",
            "있었",
        ),
    ),
]


def classify_intent(question: str) -> str:
    q = question.lower()
    for intent, words in INTENT_KEYWORDS:
        if any(w in q for w in words):
            return intent
    return "small_talk"


def _block(text: str, name: str) -> str | None:
    match = re.search(rf"<{name}>\n?(.*?)\n?</{name}>", text, re.S)
    return match.group(1) if match else None


def _matches(when: dict[str, Any], ctx: dict[str, Any]) -> bool:
    for key, value in (when or {}).items():
        if key == "lie_broken" and value not in ctx.get("broken_lie_ids", []):
            return False
        if key == "secret_revealed" and value not in ctx.get("revealed_secret_ids", []):
            return False
        if key == "presented" and value not in ctx.get("presented_evidence_ids", []):
            return False
        if key == "trust_gte" and ctx.get("trust", 0) < value:
            return False
    return True


class MockLLM(StructuredLLM):
    model_id = "mock"

    def __init__(self, script_path: Path | None = None, responses: list[str] | None = None):
        self.script: dict[str, Any] = (
            yaml.safe_load(Path(script_path).read_text(encoding="utf-8")) if script_path else {}
        )
        self.responses = list(responses or [])  # test override: raw replies in order
        self.calls: list[list[Message]] = []

    def reply_for(self, messages: list[Message], schema_title: str | None) -> str:
        if self.responses:
            return self.responses.pop(0)
        prompt = next(
            (m.content for m in reversed(messages) if "<player_question>" in m.content), ""
        )
        ctx = json.loads(_block(prompt, "context") or "{}")
        question = _block(prompt, "player_question") or ""
        if schema_title and schema_title != "InterrogationOutput":
            fixed = self.script.get("structured", {}).get(schema_title)
            return json.dumps(fixed or {}, ensure_ascii=False)
        npc_script = self.script.get("npcs", {}).get(ctx.get("npc_id"), {})
        intent = classify_intent(question)
        entries = npc_script.get(intent) or npc_script.get("small_talk") or []
        entry = next((e for e in entries if _matches(e.get("when", {}), ctx)), None)
        if entry is None:
            entry = {"answer": "...", "emotion": ctx.get("emotion", "calm")}
        return json.dumps(
            {
                "answer": entry["answer"],
                "emotion": entry.get("emotion", "calm"),
                "revealed_fact_ids": entry.get("revealed_fact_ids", []),
                "asserted_lie_ids": entry.get("asserted_lie_ids", []),
                "contradiction_detected": False,
                "trust_delta": entry.get("trust_delta", 0),
            },
            ensure_ascii=False,
        )

    async def _chat(
        self,
        messages: list[Message],
        json_schema: dict | None,
        temperature: float,
        max_tokens: int,
    ) -> ChatReply:
        self.calls.append(list(messages))
        title = (json_schema or {}).get("title")
        text = self.reply_for(messages, title)
        prompt_chars = sum(len(m.content) for m in messages)
        return ChatReply(text=text, usage=Usage(prompt_chars // 2, len(text) // 2))

    async def stream(
        self, messages: list[Message], schema: type[BaseModel] | None = None
    ) -> AsyncIterator[str]:
        self.calls.append(list(messages))
        text = self.reply_for(messages, schema.__name__ if schema else None)
        for i in range(0, len(text), 12):
            yield text[i : i + 12]
