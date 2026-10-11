"""What one NPC may know and say right now (proposal §3, request-time scope).

scope = own facts whose unlock condition holds
      ∪ facts proven by evidence the player presented to THIS npc
      ∪ own secrets whose reveal_when holds
      − leak_forbidden facts, − facts of any secret not yet revealed
The npc_id comes from the server route; the scope is computed only from server state.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from case_validator import CaseBible, evaluate
from case_validator.schema import Evidence, Fact, Lie

from app.core.session import GameState, Turn


@dataclass(frozen=True)
class KnowledgeScope:
    npc_id: str
    trust: int
    emotion: str
    facts: dict[str, Fact]
    presented_evidence: list[Evidence]
    active_lies: list[Lie]
    broken_lies: list[Lie]
    revealed_secret_ids: frozenset[str]
    history: list[Turn] = field(default_factory=list)

    @property
    def allowed_fact_ids(self) -> frozenset[str]:
        return frozenset(self.facts)

    @classmethod
    def build(cls, state: GameState, bible: CaseBible, npc_id: str) -> KnowledgeScope:
        if npc_id not in state.npcs:
            raise KeyError(npc_id)
        cs = state.condition_state()
        npc = state.npcs[npc_id]

        revealed = {
            sec.secret_id for sec in bible.secrets if evaluate(sec.reveal_when, cs, npc=sec.npc_id)
        }
        locked_secret_facts = {
            fid for sec in bible.secrets if sec.secret_id not in revealed for fid in sec.fact_ids
        }

        def allowed(fact: Fact) -> bool:
            if fact.leak_forbidden or fact.fact_id in locked_secret_facts:
                return False
            return fact.unlock_condition is None or evaluate(fact.unlock_condition, cs, npc=npc_id)

        facts = {f.fact_id: f for f in bible.facts if npc_id in f.known_by and allowed(f)}

        evidence_by_id = {e.evidence_id: e for e in bible.evidence}
        presented = [evidence_by_id[e] for e in npc.presented if e in evidence_by_id]
        fact_by_id = {f.fact_id: f for f in bible.facts}
        for item in presented:
            for fid in item.proves_fact_ids:
                fact = fact_by_id.get(fid)
                if fact and not fact.leak_forbidden and fid not in locked_secret_facts:
                    facts[fid] = fact

        own_lies = [lie for lie in bible.lies if lie.npc_id == npc_id]
        return cls(
            npc_id=npc_id,
            trust=npc.trust,
            emotion=npc.emotion,
            facts=facts,
            presented_evidence=presented,
            active_lies=[lie for lie in own_lies if lie.lie_id not in npc.broken_lies],
            broken_lies=[lie for lie in own_lies if lie.lie_id in npc.broken_lies],
            revealed_secret_ids=frozenset(s for s in revealed if _secret_npc(bible, s) == npc_id),
            history=state.turns_with(npc_id),
        )


def _secret_npc(bible: CaseBible, secret_id: str) -> str:
    return next(s.npc_id for s in bible.secrets if s.secret_id == secret_id)
