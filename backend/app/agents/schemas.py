from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Emotion = Literal["calm", "nervous", "defensive", "angry", "sad", "shaken"]


class NpcReply(BaseModel):
    """LLM이 내야 하는 심문 응답. 기획서의 Interrogation 출력에 used_lie_ids를 더했다."""

    answer: str = Field(min_length=1, max_length=600)
    emotion: Emotion = "calm"
    revealed_fact_ids: list[str] = Field(default_factory=list)
    used_lie_ids: list[str] = Field(default_factory=list)
    """Case Bible에 정의된 거짓말 중 이번 답변에 쓴 것. 모순 탐지에 쓴다."""
    contradiction_detected: bool = False
    trust_delta: int = Field(default=0, ge=-1, le=1)
