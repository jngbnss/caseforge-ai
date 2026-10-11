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
    JUDGE_EVIDENCE,
    JUDGE_NEW_STATEMENT,
    JUDGE_PREVIOUS,
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

    def judge(self, messages: list[Message]) -> dict[str, Any]:
        """모순 판정 대본: 새 진술 문구 + (이전 진술 문구 | 제시 증거)가 프롬프트에 있으면 판정한다."""
        user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        npc = re.search(re.escape(NPC_ID_PREFIX) + r"(\S+)", user)
        turn_line = re.compile(r"- \[turn (\d+)\] (.*)")
        new = turn_line.findall(_section(user, JUDGE_NEW_STATEMENT))
        previous = [(int(t), text) for t, text in turn_line.findall(_section(user, JUDGE_PREVIOUS))]
        evidence = set(re.findall(r"\[((?:ev|rec)-\d+)\]", _section(user, JUDGE_EVIDENCE)))
        if not npc or not new:
            return {"findings": []}
        new_turn, new_text = int(new[0][0]), new[0][1]
        findings = []
        for rule in self.script.get("judge", {}).get(npc.group(1), []):
            if (
                rule["new_contains"] not in new_text
                or not set(rule.get("evidence", [])) <= evidence
            ):
                continue
            turns = [new_turn]
            if "previous_contains" in rule:
                hits = [t for t, text in previous if rule["previous_contains"] in text]
                if not hits:
                    continue
                turns = [hits[0], new_turn]
            findings.append(
                {
                    "type": rule["type"],
                    "statement_turns": turns,
                    "evidence_ids": rule.get("evidence", []),
                    "quotes": [
                        rule["new_contains"],
                        rule.get("other_quote") or rule.get("previous_contains", ""),
                    ],
                    "confidence": rule.get("confidence", 0.8),
                    "explanation": rule["explanation"],
                }
            )
        return {"findings": findings}

    def feedback(self, messages: list[Message]) -> dict[str, Any]:
        """추리 피드백 대본: 문장 단위로 나눠 제출 증거 이름이 있으면 연결, 단정 표현이면 비약,
        나머지 중 근거 표현이 없는 문장은 근거 없는 주장으로 본다."""
        user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        evidence = re.findall(r"- \[((?:ev|rec)-\d+)\] ([^:]+):", _section(user, "## 제출한 증거"))
        narrative = _section(user, "## 탐정의 보고서")
        rules = self.script.get("feedback", {})
        out: dict[str, Any] = {"unsupported_claims": [], "logical_leaps": [], "evidence_links": []}
        for sentence in re.split(r"(?<=[.!?。])\s+|\n", narrative):
            sentence = sentence.strip()
            if not sentence:
                continue
            linked = [eid for eid, name in evidence if name.strip() in sentence]
            if linked:
                out["evidence_links"].append({"claim": sentence, "evidence_id": linked[0]})
            elif any(w in sentence for w in rules.get("leap_words", [])):
                out["logical_leaps"].append(sentence)
            elif not any(w in sentence for w in rules.get("grounded_words", [])):
                out["unsupported_claims"].append(sentence)
        return out

    def structured(self, title: str, messages: list[Message]) -> dict[str, Any]:
        if title == "ContradictionJudgement":
            return self.judge(messages)
        if title == "DeductionFeedback":
            return self.feedback(messages)
        return self.respond(read_prompt(messages))

    async def complete(
        self,
        messages: list[Message],
        *,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 512,
    ) -> LLMRaw:
        title = (json_schema or {}).get("title", "")
        text = json.dumps(self.structured(title, messages), ensure_ascii=False)
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
