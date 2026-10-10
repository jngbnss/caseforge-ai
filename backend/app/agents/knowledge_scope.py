"""NPC별 지식 범위. LLM 프롬프트에는 이 범위 안의 정보만 들어간다.

범위는 서버의 세션 상태와 Case Bible로만 계산한다. 플레이어 입력은 범위에 영향을 주지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.session import GameState
from case_validator import CaseBible, evaluate
from case_validator.schema import Dialogue, Evidence, Fact, Lie, Suspect


class UnknownNpcError(KeyError):
    pass


@dataclass(frozen=True)
class Scope:
    npc_id: str
    suspect: Suspect
    dialogue: Dialogue | None
    facts: tuple[Fact, ...]
    """NPC가 지금 말해도 되는 사실 (자기 지식 + 공개 조건 충족 비밀 + 제시받은 증거의 기록)."""
    presented: tuple[Evidence, ...]
    active_lies: tuple[Lie, ...]
    broken_lies: tuple[Lie, ...]
    withheld_fact_ids: frozenset[str]
    """NPC가 알지만 아직(또는 영원히) 말하면 안 되는 사실. 프롬프트에 넣지 않는다."""
    emotion: str
    trust: int

    @property
    def allowed_fact_ids(self) -> frozenset[str]:
        return frozenset(f.fact_id for f in self.facts)

    @property
    def active_lie_ids(self) -> frozenset[str]:
        return frozenset(lie.lie_id for lie in self.active_lies)

    def allowed_text(self) -> str:
        """이 범위 안에서 등장해도 되는 문장 전체 (누설 가드의 카나리 예외 판정용)."""
        parts = [f.content for f in self.facts]
        parts += [f"{e.name} {e.description}" for e in self.presented]
        parts += [lie.claim for lie in self.active_lies]
        return "\n".join(parts)


def build_scope(bible: CaseBible, state: GameState, npc_id: str) -> Scope:
    suspect = bible.suspect(npc_id)
    if suspect is None:
        raise UnknownNpcError(npc_id)
    play = state.play_state()
    presented_ids = state.presented_to(npc_id)

    secret_facts: set[str] = set()
    revealed_secret_facts: set[str] = set()
    for sec in bible.secrets:
        if sec.npc_id != npc_id:
            continue
        secret_facts |= set(sec.fact_ids)
        if evaluate(sec.reveal_when, play):
            revealed_secret_facts |= set(sec.fact_ids)

    facts: dict[str, Fact] = {}
    withheld: set[str] = set()
    for fact in bible.facts:
        if npc_id not in fact.known_by:
            continue
        hidden = (
            fact.forbidden
            or (fact.fact_id in secret_facts and fact.fact_id not in revealed_secret_facts)
            or not evaluate(fact.unlock_condition, play)
        )
        if hidden:
            withheld.add(fact.fact_id)
        else:
            facts[fact.fact_id] = fact

    presented = tuple(e for eid in presented_ids if (e := bible.evidence_by_id(eid)))
    for evidence in presented:
        for fid in evidence.proves_fact_ids:
            fact = bible.fact(fid)
            if fact is not None and not fact.forbidden:
                facts.setdefault(fid, fact)

    active, broken = [], []
    for lie in bible.lies:
        if lie.npc_id != npc_id:
            continue
        is_broken = bool(set(lie.breaks_on) & set(presented_ids)) or (
            lie.contradicts_fact_id in facts
        )
        (broken if is_broken else active).append(lie)

    dialogue = next((d for d in bible.dialogues if d.suspect_id == npc_id), None)
    return Scope(
        npc_id=npc_id,
        suspect=suspect,
        dialogue=dialogue,
        facts=tuple(facts.values()),
        presented=presented,
        active_lies=tuple(active),
        broken_lies=tuple(broken),
        withheld_fact_ids=frozenset(withheld - set(facts)),
        emotion=state.emotion.get(npc_id, "calm"),
        trust=state.trust.get(npc_id, 0),
    )
