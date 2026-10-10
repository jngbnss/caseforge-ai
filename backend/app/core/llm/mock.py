"""대본 기반 Mock LLM. CI와 LLM 없는 개발 환경에서 쓴다.

실제 모델처럼 **프롬프트에 들어 있는 정보만** 보고 답한다. 프롬프트에서 NPC ID, 사실·거짓말·제시 증거 ID,
플레이어 질문을 읽어 대본의 조건에 맞는 첫 항목을 고른다. 같은 입력에는 항상 같은 출력을 낸다.
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.core.llm.markers import (
    NPC_ID_PREFIX,
    QUESTION_CLOSE,
    QUESTION_OPEN,
    SECTION_EVIDENCE,
    SECTION_FACTS,
    SECTION_LIES,
)
from app.core.llm.ports import LLMRaw, Message, Usage

SCRIPTS_DIR = Path(__file__).parent / "scripts"


@dataclass(frozen=True)
class PromptView:
    npc_id: str
    fact_ids: frozenset[str]
    lie_ids: frozenset[str]
    evidence_ids: frozenset[str]
    question: str


def _section(text: str, header: str) -> str:
    start = text.find(header)
    if start < 0:
        return ""
    rest = text[start + len(header) :]
    end = rest.find("\n## ")
    return rest if end < 0 else rest[:end]


def read_prompt(messages: list[Message]) -> PromptView:
    system = "\n".join(m.content for m in messages if m.role == "system")
    user = next((m.content for m in reversed(messages) if m.role == "user"), "")
    npc = re.search(re.escape(NPC_ID_PREFIX) + r"(\S+)", system)
    q = re.search(re.escape(QUESTION_OPEN) + r"(.*?)" + re.escape(QUESTION_CLOSE), user, re.S)
    return PromptView(
        npc_id=npc.group(1) if npc else "",
        fact_ids=frozenset(re.findall(r"\[(fact-\d+)\]", _section(system, SECTION_FACTS))),
        lie_ids=frozenset(re.findall(r"\[(lie-\d+)\]", _section(system, SECTION_LIES))),
        evidence_ids=frozenset(
            re.findall(r"\[((?:ev|rec)-\d+)\]", _section(system, SECTION_EVIDENCE))
        ),
        question=(q.group(1) if q else user).strip(),
    )


class MockLLM:
    """대본 YAML을 따르는 결정론적 LLM."""

    def __init__(self, script: dict[str, Any], model_id: str = "mock") -> None:
        self.script = script
        self.model_id = model_id

    @classmethod
    def for_case(cls, case_id: str) -> MockLLM:
        path = SCRIPTS_DIR / f"{case_id}.yaml"
        return cls(yaml.safe_load(path.read_text(encoding="utf-8")), model_id=f"mock:{case_id}")

    def intent(self, question: str) -> str:
        q = question.lower()
        for item in self.script["intents"]:
            if any(k.lower() in q for k in item["keywords"]):
                return item["name"]
        return "default"

    def respond(self, view: PromptView) -> dict[str, Any]:
        npc = self.script["npcs"].get(view.npc_id, {})
        intent = self.intent(view.question)
        for entry in npc.get(intent, []) + npc.get("default", []):
            when = entry.get("when", {})
            if (
                set(when.get("facts", [])) <= view.fact_ids
                and set(when.get("lies", [])) <= view.lie_ids
                and set(when.get("evidence", [])) <= view.evidence_ids
                and not set(when.get("not_evidence", [])) & view.evidence_ids
            ):
                return {
                    "revealed_fact_ids": entry.get("revealed", []),
                    "used_lie_ids": entry.get("used_lies", []),
                    "emotion": entry.get("emotion", "calm"),
                    "trust_delta": entry.get("trust_delta", 0),
                    "contradiction_detected": False,
                    "answer": entry["answer"].strip(),
                }
        return {
            "revealed_fact_ids": [],
            "used_lie_ids": [],
            "emotion": "calm",
            "trust_delta": 0,
            "contradiction_detected": False,
            "answer": "…",
        }

    async def complete(
        self,
        messages: list[Message],
        *,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 512,
    ) -> LLMRaw:
        text = json.dumps(self.respond(read_prompt(messages)), ensure_ascii=False)
        prompt_chars = sum(len(m.content) for m in messages)
        return LLMRaw(text, self.model_id, 0.0, Usage(prompt_chars // 2, len(text) // 2))

    async def stream(
        self,
        messages: list[Message],
        *,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 512,
    ) -> AsyncIterator[str]:
        text = (await self.complete(messages, json_schema=json_schema)).text
        for i in range(0, len(text), 8):
            yield text[i : i + 8]
