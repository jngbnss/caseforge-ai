"""조건 DSL 평가. LLM 없이 코드로만 판정한다."""

from __future__ import annotations

from dataclasses import dataclass, field

from .schema import (
    AllOf,
    AnyOf,
    Condition,
    EvidenceCollected,
    EvidencePresented,
    PuzzleSolved,
    TrustGte,
)

MAX_TRUST = 3
"""게임에서 도달 가능한 최대 신뢰도. 낙관적 도달 가능성 분석에 쓴다."""


@dataclass
class PlayState:
    collected: set[str] = field(default_factory=set)
    solved: set[str] = field(default_factory=set)
    presented: dict[str, set[str]] = field(default_factory=dict)
    trust: dict[str, int] = field(default_factory=dict)


def evaluate(condition: Condition | None, state: PlayState) -> bool:
    """플레이 상태에서 조건이 참인지 평가한다. None은 항상 참이다."""
    match condition:
        case None:
            return True
        case AllOf(all=items):
            return all(evaluate(c, state) for c in items)
        case AnyOf(any=items):
            return any(evaluate(c, state) for c in items)
        case EvidenceCollected(evidence_collected=eid):
            return eid in state.collected
        case EvidencePresented(evidence_presented=p):
            return p.evidence_id in state.presented.get(p.npc_id, set())
        case PuzzleSolved(puzzle_solved=pid):
            return pid in state.solved
        case TrustGte(trust_gte=t):
            return state.trust.get(t.npc_id, 0) >= t.value
    raise TypeError(f"알 수 없는 조건: {condition!r}")


def satisfiable(condition: Condition | None, collected: set[str], solved: set[str]) -> bool:
    """플레이어가 최선을 다했을 때 충족 가능한지 (낙관적 판정).

    증거 제시는 그 증거를 수집할 수 있으면 가능하고, 신뢰도는 MAX_TRUST까지 오를 수 있다고 본다.
    """
    match condition:
        case None:
            return True
        case AllOf(all=items):
            return all(satisfiable(c, collected, solved) for c in items)
        case AnyOf(any=items):
            return any(satisfiable(c, collected, solved) for c in items)
        case EvidenceCollected(evidence_collected=eid):
            return eid in collected
        case EvidencePresented(evidence_presented=p):
            return p.evidence_id in collected
        case PuzzleSolved(puzzle_solved=pid):
            return pid in solved
        case TrustGte(trust_gte=t):
            return t.value <= MAX_TRUST
    raise TypeError(f"알 수 없는 조건: {condition!r}")


def referenced_ids(condition: Condition | None) -> list[tuple[str, str]]:
    """조건이 참조하는 (종류, ID) 목록. 종류는 evidence / puzzle / suspect."""
    match condition:
        case None:
            return []
        case AllOf(all=items) | AnyOf(any=items):
            return [r for c in items for r in referenced_ids(c)]
        case EvidenceCollected(evidence_collected=eid):
            return [("evidence", eid)]
        case EvidencePresented(evidence_presented=p):
            return [("evidence", p.evidence_id), ("suspect", p.npc_id)]
        case PuzzleSolved(puzzle_solved=pid):
            return [("puzzle", pid)]
        case TrustGte(trust_gte=t):
            return [("suspect", t.npc_id)]
    raise TypeError(f"알 수 없는 조건: {condition!r}")
