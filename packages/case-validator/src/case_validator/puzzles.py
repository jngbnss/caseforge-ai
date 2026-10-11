"""Exhaustive solution search for puzzles (V04).

Sequence/arrangement puzzles enumerate every permutation of their items; code puzzles
enumerate every string over the alphabet. Only the clue constraints written in the case
decide which candidates are valid, so the stored answer is never consulted here.
"""

from __future__ import annotations

from collections.abc import Iterator
from itertools import permutations, product

from case_validator.schema import (
    Before,
    ImmediatelyBefore,
    Puzzle,
    SegmentIn,
    SegmentNotIn,
    SegmentsAscending,
)

MAX_PERMUTATION_ITEMS = 9  # 9! = 362,880 candidates
MAX_CODE_SPACE = 1_000_000

ORDER_CONSTRAINTS = (Before, ImmediatelyBefore)
CODE_CONSTRAINTS = (SegmentIn, SegmentNotIn, SegmentsAscending)


class PuzzleSpaceError(ValueError):
    """The puzzle cannot be searched (too large or inconsistent definition)."""


def _check_order(candidate: tuple[str, ...], puzzle: Puzzle) -> bool:
    index = {item: i for i, item in enumerate(candidate)}
    for c in puzzle.constraints:
        if isinstance(c, Before) and not index[c.first] < index[c.then]:
            return False
        if isinstance(c, ImmediatelyBefore) and index[c.then] != index[c.first] + 1:
            return False
    return True


def _check_code(candidate: str, puzzle: Puzzle) -> bool:
    for c in puzzle.constraints:
        if isinstance(c, SegmentIn | SegmentNotIn):
            segment = candidate[c.start : c.start + c.length]
            inside = segment in c.values
            if inside != isinstance(c, SegmentIn):
                return False
        elif isinstance(c, SegmentsAscending):
            parts = [candidate[i : i + c.length] for i in range(0, len(candidate), c.length)]
            if any(a >= b for a, b in zip(parts, parts[1:], strict=False)):
                return False
    return True


def _iter_candidates(puzzle: Puzzle) -> Iterator[str | tuple[str, ...]]:
    if puzzle.input_type in ("sequence", "arrangement"):
        ids = [item.item_id for item in puzzle.items]
        if not ids:
            raise PuzzleSpaceError("ordering puzzle has no items")
        if len(ids) > MAX_PERMUTATION_ITEMS:
            raise PuzzleSpaceError(f"{len(ids)} items exceed the search limit")
        for c in puzzle.constraints:
            if not isinstance(c, ORDER_CONSTRAINTS):
                raise PuzzleSpaceError(f"constraint {c.kind!r} does not apply to ordering puzzles")
            if c.first not in ids or c.then not in ids:
                raise PuzzleSpaceError(f"constraint references unknown item: {c.first}/{c.then}")
        for perm in permutations(ids):
            if _check_order(perm, puzzle):
                yield perm
        return

    if puzzle.code_length is None:
        raise PuzzleSpaceError("code puzzle needs code_length")
    if len(puzzle.code_alphabet) ** puzzle.code_length > MAX_CODE_SPACE:
        raise PuzzleSpaceError("code space exceeds the search limit")
    for c in puzzle.constraints:
        if not isinstance(c, CODE_CONSTRAINTS):
            raise PuzzleSpaceError(f"constraint {c.kind!r} does not apply to code puzzles")
    for chars in product(puzzle.code_alphabet, repeat=puzzle.code_length):
        code = "".join(chars)
        if _check_code(code, puzzle):
            yield code


def solve(puzzle: Puzzle, limit: int = 20) -> list[str | tuple[str, ...]]:
    """Return up to `limit` candidate answers that satisfy every clue constraint."""
    found: list[str | tuple[str, ...]] = []
    for candidate in _iter_candidates(puzzle):
        found.append(candidate)
        if len(found) >= limit:
            break
    return found


def normalize_answer(puzzle: Puzzle) -> str | tuple[str, ...]:
    answer = puzzle.answer
    if puzzle.input_type == "code":
        return answer if isinstance(answer, str) else "".join(answer)
    return (answer,) if isinstance(answer, str) else tuple(answer)
