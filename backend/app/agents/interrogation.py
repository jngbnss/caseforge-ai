"""심문 파이프라인: scope → retrieve → generate → guard → update_state.

노드마다 함수 하나로 나눠 두었다. 4단계에서 각 함수를 LangGraph 노드로 옮긴다.
심문 1턴에 LLM 호출은 1회이며, 누설 가드가 막았을 때만 1회 더 호출한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.agents.knowledge_scope import Scope, build_scope
from app.agents.leak_guard import GuardResult, check_reply
from app.agents.prompts import build_messages, sanitize_question
from app.agents.schemas import NpcReply
from app.core.db import DialogueRow
from app.core.embedding.index import VectorIndex
from app.core.embedding.ports import EmbeddingPort
from app.core.llm.ports import LLMPort
from app.core.llm.structured import generate_structured
from app.core.session import GameSession
from case_validator.schema import Fact

HISTORY_TURNS = 6
TOP_K = 8


@dataclass
class Turn:
    session: GameSession
    npc_id: str
    question: str
    scope: Scope | None = None
    grounding: list[Fact] = field(default_factory=list)
    history: list[tuple[str, str]] = field(default_factory=list)
    reply: NpcReply | None = None
    guard: GuardResult | None = None
    llm_calls: int = 0
    regenerated: bool = False
    fallback_used: bool = False
    turn_no: int = 0


def evasion(scope: Scope, turn_no: int) -> NpcReply:
    lines = scope.dialogue.evasions if scope.dialogue else ("말씀드릴 수 있는 게 없네요.",)
    return NpcReply(answer=lines[turn_no % len(lines)], emotion="defensive")


class Interrogator:
    def __init__(self, llm: LLMPort, embedder: EmbeddingPort, db: DbSession) -> None:
        self.llm = llm
        self.embedder = embedder
        self.db = db

    async def ask(self, session: GameSession, npc_id: str, question: str) -> Turn:
        turn = Turn(session, npc_id, sanitize_question(question))
        self.scope_node(turn)
        self.retrieve_node(turn)
        await self.generate_node(turn)
        await self.guard_node(turn)
        self.update_state_node(turn)
        return turn

    # ---------- 노드 ----------

    def scope_node(self, turn: Turn) -> None:
        turn.scope = build_scope(turn.session.bible, turn.session.state, turn.npc_id)
        rows = self.db.scalars(
            select(DialogueRow)
            .where(DialogueRow.session_id == turn.session.id, DialogueRow.npc_id == turn.npc_id)
            .order_by(DialogueRow.id)
        ).all()
        pairs: list[tuple[str, str]] = []
        for row in rows:
            if row.role == "player":
                pairs.append((row.text, ""))
            elif pairs:
                pairs[-1] = (pairs[-1][0], row.text)
        turn.history = pairs[-HISTORY_TURNS:]

    def retrieve_node(self, turn: Turn) -> None:
        """이 NPC의 범위 안에서만 검색한다. 범위 밖 사실은 인덱스에 들어가지 않는다."""
        assert turn.scope is not None
        facts = {f.fact_id: f for f in turn.scope.facts}
        index = VectorIndex(self.embedder, {fid: f.content for fid, f in facts.items()})
        hits = index.search(turn.question, k=TOP_K)
        turn.grounding = [facts[h.id] for h in hits]

    async def _generate(self, turn: Turn, *, retry: bool) -> NpcReply:
        assert turn.scope is not None
        messages = build_messages(
            turn.scope, turn.grounding, turn.history, turn.question, retry=retry
        )
        result = await generate_structured(
            self.llm, messages, NpcReply, fallback=evasion(turn.scope, len(turn.history))
        )
        turn.llm_calls += result.attempts
        turn.fallback_used = turn.fallback_used or result.fallback_used
        return result.value

    async def generate_node(self, turn: Turn) -> None:
        turn.reply = await self._generate(turn, retry=False)

    async def guard_node(self, turn: Turn) -> None:
        assert turn.scope is not None and turn.reply is not None
        bible = turn.session.bible
        turn.guard = check_reply(turn.reply, turn.scope, bible, turn.question)
        if turn.guard.ok:
            return
        turn.regenerated = True
        second = await self._generate(turn, retry=True)
        second_guard = check_reply(second, turn.scope, bible, turn.question)
        turn.guard.violations += [f"retry:{v}" for v in second_guard.violations]
        if second_guard.ok:
            turn.reply = second
        else:
            turn.reply = evasion(turn.scope, len(turn.history))
            turn.fallback_used = True

    def update_state_node(self, turn: Turn) -> None:
        assert turn.reply is not None and turn.guard is not None
        state = turn.session.state
        reply = turn.reply
        state.emotion[turn.npc_id] = reply.emotion
        state.add_trust(turn.npc_id, reply.trust_delta)
        turn.turn_no = state.next_turn(turn.npc_id)
        guard_info = {
            "violations": turn.guard.violations,
            "regenerated": turn.regenerated,
            "fallback": turn.fallback_used,
            "llm_calls": turn.llm_calls,
        }
        self.db.add_all(
            [
                DialogueRow(
                    session_id=turn.session.id,
                    npc_id=turn.npc_id,
                    turn=turn.turn_no,
                    role="player",
                    text=turn.question,
                ),
                DialogueRow(
                    session_id=turn.session.id,
                    npc_id=turn.npc_id,
                    turn=turn.turn_no,
                    role="npc",
                    text=reply.answer,
                    emotion=reply.emotion,
                    revealed_fact_ids=reply.revealed_fact_ids,
                    grounding_fact_ids=[f.fact_id for f in turn.grounding],
                    used_lie_ids=reply.used_lie_ids,
                    guard=guard_info,
                ),
            ]
        )
        self.db.commit()
