"""Pure evaluation of the Condition DSL. No LLM is ever involved."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field

from case_validator.schema import (
    AllOf,
    Always,
    AnyOf,
    Condition,
    EvidenceCollected,
    EvidencePresented,
    PuzzleSolved,
    TrustGte,
)

MAX_TRUST = 5


@dataclass(frozen=True)
class ConditionState:
    """The parts of a game session that conditions can observe."""

    collected: frozenset[str] = frozenset()
    presented: Mapping[str, frozenset[str]] = field(default_factory=dict)  # npc -> evidence
    solved: frozenset[str] = frozenset()
    trust: Mapping[str, int] = field(default_factory=dict)  # npc -> trust level


def evaluate(condition: Condition, state: ConditionState, npc: str | None = None) -> bool:
    """Evaluate a condition. `npc` is the contextual NPC for atoms that omit `npc`."""
    match condition:
        case Always():
            return True
        case AllOf(all=children):
            return all(evaluate(c, state, npc) for c in children)
        case AnyOf(any=children):
            return any(evaluate(c, state, npc) for c in children)
        case EvidenceCollected(evidence_collected=ev):
            return ev in state.collected
        case EvidencePresented(evidence_presented=ev, npc=target):
            target = target or npc
            if target is None:
                return any(ev in shown for shown in state.presented.values())
            return ev in state.presented.get(target, frozenset())
        case PuzzleSolved(puzzle_solved=pz):
            return pz in state.solved
        case TrustGte(trust_gte=level, npc=target):
            target = target or npc
            if target is None:
                return any(t >= level for t in state.trust.values())
            return state.trust.get(target, 0) >= level
    raise TypeError(f"unknown condition: {condition!r}")


def iter_atoms(condition: Condition | None) -> Iterator[Condition]:
    """Yield every leaf atom of a condition tree."""
    if condition is None:
        return
    if isinstance(condition, AllOf | AnyOf):
        children = condition.all if isinstance(condition, AllOf) else condition.any
        for child in children:
            yield from iter_atoms(child)
    else:
        yield condition
