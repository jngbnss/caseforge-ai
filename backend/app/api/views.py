"""도메인 객체 → 공개 응답 모델 변환. 이 모듈만 Case Bible을 응답으로 옮긴다."""

from __future__ import annotations

import random

from app.api import schemas as v
from app.core.session import DeductionRecord, GameSession
from case_validator import evaluate
from case_validator.schema import CaseBible, Evidence, Puzzle


def _location_name(bible: CaseBible, location_id: str) -> str:
    return next((loc.name for loc in bible.locations if loc.location_id == location_id), "")


def evidence_view(bible: CaseBible, e: Evidence) -> v.EvidenceView:
    facts = [f.content for fid in e.proves_fact_ids if (f := bible.fact(fid)) and not f.forbidden]
    return v.EvidenceView(
        evidence_id=e.evidence_id,
        name=e.name,
        description=e.description,
        spot=e.spot or e.name,
        location_name=_location_name(bible, e.location_id),
        facts=facts,
    )


def shuffled_options(session_id: str, puzzle: Puzzle) -> list[v.PuzzleOptionView]:
    """세션마다 고정된 순서로 섞는다. 섞은 결과가 정답 순서와 같으면 한 칸 돌린다."""
    options = list(puzzle.options)
    random.Random(f"{session_id}:{puzzle.puzzle_id}").shuffle(options)
    if [o.id for o in options] == list(puzzle.answer):
        options = options[1:] + options[:1]
    return [v.PuzzleOptionView(id=o.id, label=o.label) for o in options]


def puzzle_view(session: GameSession, p: Puzzle) -> v.PuzzleView:
    state = session.state
    available = evaluate(p.requires, state.play_state())
    view = v.PuzzleView(
        puzzle_id=p.puzzle_id,
        title=p.title,
        available=available,
        solved=p.puzzle_id in state.solved,
        attempts=state.puzzle_attempts.get(p.puzzle_id, 0),
    )
    if available:
        used = state.hints_used.get(p.puzzle_id, 0)
        view.prompt = p.prompt
        view.input_type = p.input_type
        view.code_length = p.code_length
        view.options = shuffled_options(session.id, p) if p.options else []
        view.hints = list(p.hints[:used])
        view.hints_remaining = len(p.hints) - used
    return view


def npc_state(session: GameSession, npc_id: str) -> v.NpcStateView:
    s = session.state
    return v.NpcStateView(
        npc_id=npc_id,
        emotion=s.emotion.get(npc_id, "calm"),
        trust=s.trust.get(npc_id, 0),
        presented=s.presented_to(npc_id),
    )


def deduction_result(record: DeductionRecord) -> v.DeductionResultView:
    f = record.flags
    return v.DeductionResultView(
        scores=record.scores,
        total=record.total,
        correct_culprit=bool(f.get("correct_culprit")),
        unsupported_guess=bool(f.get("unsupported_guess")),
        wrong_links=list(f.get("wrong_links", [])),  # type: ignore[arg-type]
        missing_key=list(f.get("missing_key", [])),  # type: ignore[arg-type]
    )


def session_view(session: GameSession) -> v.SessionView:
    bible = session.bible
    state = session.state
    b = bible.briefing
    return v.SessionView(
        session_id=session.id,
        case_id=bible.case_id,
        briefing=v.BriefingView(
            title=bible.title,
            summary=b.summary,
            damage=b.damage,
            objective=b.objective,
            public_facts=[f.content for fid in b.public_fact_ids if (f := bible.fact(fid))],
        ),
        suspects=[
            v.SuspectView(
                suspect_id=s.suspect_id, name=s.name, role=s.role, public_profile=s.public_profile
            )
            for s in bible.suspects
        ],
        scene=[
            v.SceneObjectView(
                evidence_id=e.evidence_id,
                spot=e.spot or e.name,
                location_name=_location_name(bible, e.location_id),
                collected=e.evidence_id in state.collected,
            )
            for e in bible.evidence
            if e.source == "scene"
        ],
        evidence=[
            evidence_view(bible, e) for eid in state.collected if (e := bible.evidence_by_id(eid))
        ],
        puzzles=[puzzle_view(session, p) for p in bible.puzzles],
        npcs=[npc_state(session, s.suspect_id) for s in bible.suspects],
        deduction_options=v.DeductionOptionsView(
            motives=[v.OptionView(id=o.id, text=o.text) for o in bible.deduction_options.motives],
            methods=[v.OptionView(id=o.id, text=o.text) for o in bible.deduction_options.methods],
        ),
        deduction=deduction_result(state.deduction) if state.deduction else None,
    )


def debrief_view(session: GameSession, record: DeductionRecord) -> v.DebriefView:
    bible = session.bible
    sol = bible.solution
    collected = set(session.state.collected)
    names = {s.suspect_id: s.name for s in bible.suspects}

    def ev(eid: str) -> v.DebriefEvidenceView:
        e = bible.evidence_by_id(eid)
        assert e is not None
        return v.DebriefEvidenceView(
            evidence_id=eid,
            name=e.name,
            spot=e.spot or e.name,
            role=e.role,
            collected=eid in collected,
        )

    culprit = bible.suspect(sol.culprit_id)
    assert culprit is not None
    motives = {o.id: o.text for o in bible.deduction_options.motives}
    methods = {o.id: o.text for o in bible.deduction_options.methods}
    timeline = sorted(bible.timeline, key=lambda e: (e.time.start_min, e.actor_id))
    return v.DebriefView(
        culprit=v.SuspectView(
            suspect_id=culprit.suspect_id,
            name=culprit.name,
            role=culprit.role,
            public_profile=culprit.public_profile,
        ),
        motive=motives[sol.motive_id],
        method=methods[sol.method_id],
        method_steps=[f.content for fid in sol.method_steps if (f := bible.fact(fid))],
        timeline=[
            v.TimelineRowView(
                start=e.time.start,
                end=e.time.end,
                actor=names.get(e.actor_id, e.actor_id),
                location=_location_name(bible, e.location_id),
                action=e.action,
                is_crime=e.is_crime,
            )
            for e in timeline
        ],
        key_evidence=[ev(e) for e in sol.key_evidence],
        missed_key=[ev(e) for e in sol.key_evidence if e not in collected],
        wrong_links=[ev(e) for e in record.flags.get("wrong_links", [])],  # type: ignore[union-attr]
        result=deduction_result(record),
    )
