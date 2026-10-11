"""Rule-based contradiction detection.

A contradiction is recorded when an NPC has asserted a Lie and the player holds evidence
listed in that Lie's breaks_on. Rule results replace older rule results on every refresh;
LLM results (source="llm") are kept as they are.
"""

from __future__ import annotations

from case_validator import CaseBible

from app.core.session import Contradiction, GameState


def detect_rule_contradictions(bible: CaseBible, state: GameState) -> list[Contradiction]:
    lies = {lie.lie_id: lie for lie in bible.lies}
    collected = set(state.collected)
    found: dict[tuple[str, str], Contradiction] = {}
    for turn in state.turns:
        for lie_id in turn.asserted_lie_ids:
            lie = lies.get(lie_id)
            if lie is None:
                continue
            breakers = [ev for ev in lie.breaks_on if ev in collected]
            if not breakers:
                continue
            key = (turn.npc_id, lie_id)
            if key in found:
                found[key].statement_ids.append(turn.turn_id)
                continue
            found[key] = Contradiction(
                contradiction_id=f"c-{lie_id}",
                npc_id=turn.npc_id,
                type=lie.contradiction_type,
                statement_ids=[turn.turn_id],
                evidence_ids=breakers,
                source="rule",
                confidence=1.0,
                explanation="진술이 수집한 증거와 맞지 않는다.",
                lie_id=lie_id,
            )
    return list(found.values())


def refresh_rule_contradictions(bible: CaseBible, state: GameState) -> list[Contradiction]:
    """Recompute rule contradictions; return the ones that are new since the last refresh."""
    before = {c.contradiction_id for c in state.contradictions if c.source == "rule"}
    rule = detect_rule_contradictions(bible, state)
    llm = [c for c in state.contradictions if c.source == "llm"]
    state.contradictions = rule + llm
    return [c for c in rule if c.contradiction_id not in before]
