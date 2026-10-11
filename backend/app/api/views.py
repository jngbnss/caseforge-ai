"""Projection of server state onto the public API models."""

from __future__ import annotations

import random

from case_validator import CaseBible
from case_validator.schema import Evidence, Puzzle, TimeRange

from app.api import schemas as s
from app.core import game
from app.core.session import Contradiction, GameState, Turn


def _hotspot(h) -> s.Hotspot | None:
    return s.Hotspot(x=h.x, y=h.y) if h else None


def evidence_out(item: Evidence) -> s.EvidenceOut:
    return s.EvidenceOut(
        evidence_id=item.evidence_id,
        name=item.name,
        description=item.description,
        location_id=item.location_id,
        hotspot=_hotspot(item.hotspot),
    )


def contradiction_out(c: Contradiction) -> s.ContradictionOut:
    return s.ContradictionOut(**c.model_dump(exclude={"lie_id"}))


def shuffled_items(state: GameState, puzzle: Puzzle) -> list[s.PuzzleItemOut]:
    items = list(puzzle.items)
    rng = random.Random(f"{state.session_id}:{puzzle.puzzle_id}")
    rng.shuffle(items)
    answer = list(puzzle.answer) if not isinstance(puzzle.answer, str) else []
    if len(items) > 1 and [i.item_id for i in items] == answer:
        items = items[1:] + items[:1]
    return [s.PuzzleItemOut(item_id=i.item_id, label=i.label) for i in items]


def puzzle_out(state: GameState, puzzle: Puzzle) -> s.PuzzleOut:
    status = game.puzzle_status(state, puzzle)
    return s.PuzzleOut(
        puzzle_id=puzzle.puzzle_id,
        title=puzzle.title,
        prompt=puzzle.prompt,
        location_id=puzzle.location_id,
        input_type=puzzle.input_type,
        items=shuffled_items(state, puzzle),
        code_length=puzzle.code_length,
        status=status,  # type: ignore[arg-type]
        attempts=state.puzzle_attempts.get(puzzle.puzzle_id, 0),
        hints_used=state.hints_used.get(puzzle.puzzle_id, 0),
        hints_total=len(puzzle.hints),
        hotspot=_hotspot(puzzle.hotspot),
    )


def suspects_out(state: GameState, bible: CaseBible) -> list[s.SuspectOut]:
    return [
        s.SuspectOut(
            suspect_id=x.suspect_id,
            name=x.name,
            role=x.role,
            public_profile=x.public_profile,
            apparent_suspicion=x.apparent_suspicion,
            trust=state.npcs[x.suspect_id].trust,
            emotion=state.npcs[x.suspect_id].emotion,
        )
        for x in bible.suspects
    ]


def collected_out(state: GameState, bible: CaseBible) -> list[s.EvidenceOut]:
    by_id = {e.evidence_id: e for e in bible.evidence}
    return [evidence_out(by_id[e]) for e in state.collected]


def scene_objects(state: GameState, bible: CaseBible) -> list[s.SceneObject]:
    objects: list[s.SceneObject] = []
    for item in bible.evidence:
        if item.hotspot is None:  # puzzle rewards have no place in the scene
            continue
        if item.evidence_id in state.collected or game.is_discoverable(state, item):
            objects.append(
                s.SceneObject(
                    object_id=item.evidence_id,
                    kind="evidence",
                    location_id=item.location_id,
                    label=item.name,
                    hotspot=_hotspot(item.hotspot),
                    done=item.evidence_id in state.collected,
                )
            )
    for puzzle in bible.puzzles:
        status = game.puzzle_status(state, puzzle)
        if status != "locked":
            objects.append(
                s.SceneObject(
                    object_id=puzzle.puzzle_id,
                    kind="puzzle",
                    location_id=puzzle.location_id,
                    label=puzzle.title,
                    hotspot=_hotspot(puzzle.hotspot),
                    done=status == "solved",
                )
            )
    return objects


def session_out(state: GameState, bible: CaseBible) -> s.SessionOut:
    b = bible.briefing
    return s.SessionOut(
        session_id=state.session_id,
        case_id=state.case_id,
        case_sha256=state.case_sha256,
        title=bible.title,
        briefing=s.BriefingOut(
            headline=b.headline,
            summary=b.summary,
            objective=b.objective,
            opening_location_id=b.opening_location_id,
            motive_options=[s.Option(id=m.motive_id, label=m.label) for m in b.motive_options],
            method_options=[s.Option(id=m.method_id, label=m.label) for m in b.method_options],
        ),
        locations=[
            s.LocationOut(location_id=x.location_id, name=x.name, description=x.description)
            for x in bible.locations
        ],
        suspects=suspects_out(state, bible),
        collected_evidence=collected_out(state, bible),
        objects=scene_objects(state, bible),
        puzzles=[puzzle_out(state, p) for p in bible.puzzles],
        deduction_submitted=state.deduction is not None,
    )


def statement_out(turn: Turn) -> s.StatementOut:
    return s.StatementOut(
        statement_id=turn.turn_id,
        npc_id=turn.npc_id,
        question=turn.question,
        text=turn.answer,
        pinned=turn.pinned,
    )


def _fmt(t: TimeRange | None) -> str | None:
    if t is None:
        return None
    return t.start if t.is_instant else f"{t.start}-{t.end}"


def board_out(state: GameState, bible: CaseBible) -> s.BoardOut:
    by_id = {e.evidence_id: e for e in bible.evidence}
    marks = [
        s.TimelineMark(
            evidence_id=ev,
            evidence_name=by_id[ev].name,
            location_id=att.location_id,
            time=_fmt(att.time),
        )
        for ev in state.collected
        for att in by_id[ev].attests
    ]
    marks.sort(key=lambda m: (m.time is None, m.time or ""))
    pinned = [t for t in state.turns if t.pinned]
    return s.BoardOut(
        suspects=suspects_out(state, bible),
        evidence=collected_out(state, bible),
        statements=[statement_out(t) for t in pinned],
        contradictions=[contradiction_out(c) for c in state.contradictions],
        timeline=marks,
    )


def debrief_out(state: GameState, bible: CaseBible) -> s.DebriefOut:
    assert state.deduction is not None
    sol = bible.solution
    names = {x.suspect_id: x.name for x in bible.suspects}
    places = {x.location_id: x.name for x in bible.locations}
    evidence = {e.evidence_id: e for e in bible.evidence}
    facts = {f.fact_id: f for f in bible.facts}
    motive = next(m.label for m in bible.briefing.motive_options if m.motive_id == sol.motive_id)
    method = next(
        (m.label for m in bible.briefing.method_options if m.method_id == sol.method_id), ""
    )

    missed: list[s.NamedRef] = []
    for ev in (*sol.key_evidence, *sol.acceptable_evidence):
        if ev not in state.collected:
            missed.append(s.NamedRef(id=ev, name=evidence[ev].name, reason="수집하지 않은 증거"))
    for p in bible.puzzles:
        if p.puzzle_id not in state.solved:
            missed.append(s.NamedRef(id=p.puzzle_id, name=p.title, reason="풀지 않은 퍼즐"))
    for lie in bible.lies:
        if lie.lie_id not in state.npcs[lie.npc_id].broken_lies:
            missed.append(
                s.NamedRef(
                    id=lie.npc_id,
                    name=f"{names[lie.npc_id]}: “{lie.claim}”",
                    reason="무너뜨리지 못한 거짓 진술",
                )
            )

    wrong = []
    for ev in state.deduction.wrong_links:
        item = evidence[ev]
        reason = (
            "범인을 가리키는 것처럼 보이지만 실제로는 함정이다"
            if item.role == "red_herring"
            else "범행을 증명하지 않는 증거다"
        )
        wrong.append(s.NamedRef(id=ev, name=item.name, reason=reason))

    timeline = sorted(bible.timeline, key=lambda e: (e.time.start_min, e.event_id))
    return s.DebriefOut(
        culprit=s.NamedRef(id=sol.culprit_id, name=names[sol.culprit_id]),
        motive=motive,
        method=method,
        method_steps=[facts[f].content for f in sol.method_steps],
        key_evidence=[s.NamedRef(id=e, name=evidence[e].name) for e in sol.key_evidence],
        timeline=[
            s.TimelineEventOut(
                time=_fmt(e.time) or "",
                actor=names.get(e.actor_id) if e.actor_id else None,
                location=places[e.location_id],
                action=e.action,
            )
            for e in timeline
        ],
        missed_clues=missed,
        wrong_links=wrong,
        score=s.ScoreOut(**state.deduction.score.model_dump()),
        flags=state.deduction.flags,
        your_answer=s.DeductionIn(**state.deduction.submission.model_dump()),
        narrative_feedback=state.deduction.feedback,
    )
