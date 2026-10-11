"""Game rules: collecting, puzzles, presenting evidence, deduction. Pure state transitions,
no HTTP and no LLM. Every decision uses case_validator.evaluate on server state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from case_validator import CaseBible, evaluate
from case_validator.schema import Evidence, Puzzle

from app.core.session import Contradiction, DeductionResult, DeductionSubmission, GameState
from app.deduction.scoring import score_deduction
from app.evidence.contradiction import refresh_rule_contradictions

MAX_TRUST = 5


class GameError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def _evidence(bible: CaseBible, evidence_id: str) -> Evidence:
    item = next((e for e in bible.evidence if e.evidence_id == evidence_id), None)
    if item is None:
        raise GameError(404, f"unknown evidence {evidence_id}")
    return item


def _puzzle(bible: CaseBible, puzzle_id: str) -> Puzzle:
    item = next((p for p in bible.puzzles if p.puzzle_id == puzzle_id), None)
    if item is None:
        raise GameError(404, f"unknown puzzle {puzzle_id}")
    return item


def require_npc(state: GameState, npc_id: str) -> None:
    if npc_id not in state.npcs:
        raise GameError(404, f"unknown npc {npc_id}")


def is_discoverable(state: GameState, item: Evidence) -> bool:
    return evaluate(item.discoverable, state.condition_state())


def puzzle_status(state: GameState, puzzle: Puzzle) -> str:
    if puzzle.puzzle_id in state.solved:
        return "solved"
    if puzzle.requires is None or evaluate(puzzle.requires, state.condition_state()):
        return "available"
    return "locked"


# --------------------------------------------------------------------------- evidence


def collect(
    state: GameState, bible: CaseBible, evidence_id: str
) -> tuple[Evidence, list[Contradiction]]:
    item = _evidence(bible, evidence_id)
    if evidence_id in state.collected:
        return item, []
    if not is_discoverable(state, item):
        raise GameError(403, "this evidence cannot be found yet")
    state.collected.append(evidence_id)
    return item, refresh_rule_contradictions(bible, state)


# ---------------------------------------------------------------------------- puzzles


def _normalize(puzzle: Puzzle, answer: str | list[str]) -> str | tuple[str, ...]:
    if puzzle.input_type == "code":
        text = answer if isinstance(answer, str) else "".join(answer)
        return "".join(text.split())
    return tuple(answer) if isinstance(answer, list) else tuple(answer.split(","))


def attempt_puzzle(
    state: GameState, bible: CaseBible, puzzle_id: str, answer: str | list[str]
) -> tuple[bool, list[Evidence]]:
    puzzle = _puzzle(bible, puzzle_id)
    status = puzzle_status(state, puzzle)
    if status == "locked":
        raise GameError(403, "this puzzle is not available yet")
    if status == "solved":
        return True, []
    state.puzzle_attempts[puzzle_id] = state.puzzle_attempts.get(puzzle_id, 0) + 1
    expected = puzzle.answer if isinstance(puzzle.answer, str) else tuple(puzzle.answer)
    if _normalize(puzzle, answer) != expected:
        return False, []
    state.solved.append(puzzle_id)
    unlocked: list[Evidence] = []
    for evidence_id in puzzle.unlocks_evidence:
        item = _evidence(bible, evidence_id)
        if evidence_id not in state.collected and is_discoverable(state, item):
            state.collected.append(evidence_id)
            unlocked.append(item)
    refresh_rule_contradictions(bible, state)
    return True, unlocked


def next_hint(state: GameState, bible: CaseBible, puzzle_id: str) -> tuple[str, int, int]:
    puzzle = _puzzle(bible, puzzle_id)
    if puzzle_status(state, puzzle) == "locked":
        raise GameError(403, "this puzzle is not available yet")
    if not puzzle.hints:
        raise GameError(404, "this puzzle has no hints")
    used = state.hints_used.get(puzzle_id, 0)
    index = min(used, len(puzzle.hints) - 1)
    state.hints_used[puzzle_id] = min(used + 1, len(puzzle.hints))
    used = state.hints_used[puzzle_id]
    return puzzle.hints[index], used, len(puzzle.hints) - used


# --------------------------------------------------------------------------- present


@dataclass
class PresentOutcome:
    reaction: str
    emotion: str
    trust: int
    trust_delta: int
    lie_broken: bool


def present(state: GameState, bible: CaseBible, npc_id: str, evidence_id: str) -> PresentOutcome:
    require_npc(state, npc_id)
    item = _evidence(bible, evidence_id)
    if evidence_id not in state.collected:
        raise GameError(403, "you can only present evidence you have collected")
    npc = state.npcs[npc_id]
    suspect = next(s for s in bible.suspects if s.suspect_id == npc_id)
    lines = suspect.dialogue.reaction_lines

    if evidence_id not in npc.presented:
        npc.presented.append(evidence_id)

    breaks = [
        lie.lie_id
        for lie in bible.lies
        if lie.npc_id == npc_id
        and evidence_id in lie.breaks_on
        and lie.lie_id not in npc.broken_lies
    ]
    known = {f.fact_id for f in bible.facts if npc_id in f.known_by}
    if breaks:
        npc.broken_lies.extend(breaks)
        delta = 1
        npc.emotion = "defensive" if npc_id == bible.solution.culprit_id else "nervous"
        reaction = lines.lie_broken if lines else "……"
    elif known & set(item.proves_fact_ids):
        delta = 0
        npc.emotion = "nervous" if npc.emotion == "calm" else npc.emotion
        reaction = lines.relevant if lines else "……"
    else:
        delta = 0
        reaction = lines.unrelated if lines else "……"
    npc.trust = max(0, min(MAX_TRUST, npc.trust + delta))
    return PresentOutcome(reaction, npc.emotion, npc.trust, delta, bool(breaks))


# -------------------------------------------------------------------------- deduction


def submit_deduction(
    state: GameState, bible: CaseBible, submission: DeductionSubmission
) -> DeductionResult:
    if state.deduction is not None:
        raise GameError(409, "a deduction was already submitted for this session")
    if submission.culprit_id not in state.npcs:
        raise GameError(400, "unknown suspect")
    if submission.motive_id not in {m.motive_id for m in bible.briefing.motive_options}:
        raise GameError(400, "unknown motive")
    if submission.method_id not in {m.method_id for m in bible.briefing.method_options}:
        raise GameError(400, "unknown method")
    missing = [e for e in submission.evidence_ids if e not in state.collected]
    if missing:
        raise GameError(400, f"evidence not collected: {missing}")
    score, flags, wrong_links = score_deduction(bible, submission)
    state.deduction = DeductionResult(
        submission=submission,
        score=score,
        flags=flags,
        wrong_links=wrong_links,
        submitted_at=datetime.now(UTC),
    )
    return state.deduction
