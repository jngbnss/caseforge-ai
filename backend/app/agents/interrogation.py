"""Interrogation turn: scope → retrieve → generate → guard → update_state.

Each step is a function over a shared TurnContext so the pipeline maps 1:1 onto graph nodes.
One turn = one LLM call; a guard violation allows exactly one regeneration.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from case_validator import CaseBible
from pydantic import BaseModel, Field, field_validator

from app.agents import leak_guard
from app.agents.knowledge_scope import KnowledgeScope
from app.agents.prompting import RetrievedFact, build_messages
from app.agents.retrieval import IndexRegistry, retrieve
from app.core.llm.ports import LLMPort, LLMResult, Message
from app.core.session import Emotion, GameState, Turn
from app.evidence.contradiction import refresh_rule_contradictions

MAX_TRUST = 5


class InterrogationOutput(BaseModel):
    answer: str = Field(min_length=1, max_length=800)
    emotion: Emotion = "calm"
    revealed_fact_ids: list[str] = Field(default_factory=list)
    asserted_lie_ids: list[str] = Field(default_factory=list)
    contradiction_detected: bool = False
    trust_delta: int = 0

    @field_validator("trust_delta", mode="before")
    @classmethod
    def _clamp(cls, value: object) -> int:
        try:
            return max(-1, min(1, int(value)))  # type: ignore[call-overload]
        except (TypeError, ValueError):
            return 0


@dataclass
class TurnContext:
    state: GameState
    bible: CaseBible
    npc_id: str
    question: str
    scope: KnowledgeScope | None = None
    retrieved: list[RetrievedFact] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)
    output: InterrogationOutput | None = None
    guard_blocked: bool = False
    violations: list[str] = field(default_factory=list)
    llm_calls: int = 0
    latency_ms: float = 0.0
    model_id: str = ""
    turn: Turn | None = None


REGENERATE_NOTE = (
    "이전 답변은 이 인물이 말할 수 없는 정보나 형식을 포함해 폐기되었다. "
    "<evidence_facts> 안의 사실만 사용해 캐릭터의 말투로 다시 답하라."
)


class Interrogator:
    def __init__(self, llm: LLMPort, indexes: IndexRegistry) -> None:
        self.llm = llm
        self.indexes = indexes

    # -- nodes -------------------------------------------------------------------------

    def scope(self, ctx: TurnContext) -> None:
        ctx.scope = KnowledgeScope.build(ctx.state, ctx.bible, ctx.npc_id)

    def retrieve(self, ctx: TurnContext) -> None:
        assert ctx.scope is not None
        ctx.retrieved = retrieve(
            self.indexes, ctx.bible, ctx.state.case_sha256, ctx.scope, ctx.question
        )
        ctx.messages = build_messages(ctx.bible, ctx.scope, ctx.retrieved, ctx.question)

    async def generate(self, ctx: TurnContext) -> None:
        result = await self._call(ctx, ctx.messages)
        ctx.output = result.parsed

    async def guard(self, ctx: TurnContext) -> None:
        assert ctx.scope is not None and ctx.output is not None
        verdict = self._check(ctx)
        if verdict.ok:
            return
        ctx.violations.extend(verdict.violations)
        retry = [*ctx.messages, Message(role="user", content=REGENERATE_NOTE)]
        result = await self._call(ctx, retry)
        ctx.output = result.parsed
        verdict = self._check(ctx)
        if verdict.ok:
            return
        ctx.violations.extend(verdict.violations)
        ctx.guard_blocked = True
        ctx.output = self.evasion(ctx)

    def update_state(self, ctx: TurnContext) -> None:
        assert ctx.scope is not None and ctx.output is not None
        out = ctx.output
        npc = ctx.state.npcs[ctx.npc_id]
        active = {lie.lie_id for lie in ctx.scope.active_lies}
        asserted = [lie for lie in out.asserted_lie_ids if lie in active]
        revealed = [f for f in out.revealed_fact_ids if f in ctx.scope.allowed_fact_ids]
        delta = 0 if ctx.guard_blocked else out.trust_delta
        npc.trust = max(0, min(MAX_TRUST, npc.trust + delta))
        npc.emotion = out.emotion
        collected = set(ctx.state.collected)
        lies = {lie.lie_id: lie for lie in ctx.bible.lies}
        contradiction = any(collected & set(lies[lid].breaks_on) for lid in asserted)
        ctx.turn = Turn(
            turn_id=ctx.state.next_turn_id(),
            npc_id=ctx.npc_id,
            question=ctx.question,
            answer=out.answer,
            emotion=out.emotion,
            revealed_fact_ids=revealed,
            asserted_lie_ids=asserted,
            used_fact_ids=[r.fact.fact_id for r in ctx.retrieved],
            trust_delta=delta,
            guard_blocked=ctx.guard_blocked,
            contradiction_detected=contradiction,
        )
        ctx.state.turns.append(ctx.turn)
        refresh_rule_contradictions(ctx.bible, ctx.state)

    # -- pipeline ----------------------------------------------------------------------

    async def run(
        self, state: GameState, bible: CaseBible, npc_id: str, question: str
    ) -> TurnContext:
        ctx = TurnContext(state=state, bible=bible, npc_id=npc_id, question=question)
        self.scope(ctx)
        self.retrieve(ctx)
        await self.generate(ctx)
        await self.guard(ctx)
        self.update_state(ctx)
        return ctx

    # -- helpers -----------------------------------------------------------------------

    async def _call(
        self, ctx: TurnContext, messages: list[Message]
    ) -> LLMResult[InterrogationOutput]:
        result = await self.llm.generate(messages, InterrogationOutput, default=self.evasion(ctx))
        ctx.llm_calls += result.calls
        ctx.latency_ms += result.latency_ms
        ctx.model_id = result.model_id
        if result.fallback_used:
            ctx.violations.append("invalid_output")
        return result

    def _check(self, ctx: TurnContext) -> leak_guard.GuardVerdict:
        assert ctx.scope is not None and ctx.output is not None
        return leak_guard.check(
            ctx.output.answer, ctx.output.revealed_fact_ids, ctx.scope, ctx.bible
        )

    def evasion(self, ctx: TurnContext) -> InterrogationOutput:
        suspect = next(s for s in ctx.bible.suspects if s.suspect_id == ctx.npc_id)
        lines = suspect.dialogue.evasion_lines
        line = lines[len(ctx.state.turns_with(ctx.npc_id)) % len(lines)]
        emotion = ctx.state.npcs[ctx.npc_id].emotion
        return InterrogationOutput(answer=line, emotion=emotion)
