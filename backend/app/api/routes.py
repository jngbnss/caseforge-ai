"""REST API. State changes go through app.core.game; responses are built by app.api.views."""

from __future__ import annotations

from typing import Annotated

from case_validator import CaseBible
from fastapi import APIRouter, Depends, HTTPException, Request

from app.api import schemas as s
from app.api import views
from app.core import game
from app.core.cases import CaseNotFoundError, get_case
from app.core.services import Services
from app.core.session import DeductionSubmission, GameState

router = APIRouter()


def services(request: Request) -> Services:
    return request.app.state.services


Svc = Annotated[Services, Depends(services)]


def _load(svc: Services, session_id: str) -> tuple[GameState, CaseBible]:
    state = svc.repo.get(session_id)
    if state is None:
        raise HTTPException(404, "session not found")
    loaded = get_case(state.case_id)
    if loaded.sha256 != state.case_sha256:
        # The Bible is fixed for the lifetime of a session.
        raise HTTPException(409, "case data changed since this session started")
    return state, loaded.bible


def _run[T](fn, *args) -> T:
    try:
        return fn(*args)
    except game.GameError as exc:
        raise HTTPException(exc.status, exc.message) from exc


@router.post("/sessions", response_model=s.SessionOut, status_code=201)
def create_session(svc: Svc, body: s.CreateSessionIn | None = None) -> s.SessionOut:
    case_id = (body.case_id if body else None) or svc.settings.default_case_id
    try:
        loaded = get_case(case_id)
    except CaseNotFoundError as exc:
        raise HTTPException(404, "case not found") from exc
    state = GameState.new(loaded.bible, loaded.sha256)
    svc.repo.create(state)
    return views.session_out(state, loaded.bible)


@router.get("/sessions/{session_id}", response_model=s.SessionOut)
def get_session(session_id: str, svc: Svc) -> s.SessionOut:
    state, bible = _load(svc, session_id)
    return views.session_out(state, bible)


@router.post("/sessions/{session_id}/evidence/{evidence_id}/collect", response_model=s.CollectOut)
def collect_evidence(session_id: str, evidence_id: str, svc: Svc) -> s.CollectOut:
    state, bible = _load(svc, session_id)
    item, new = _run(game.collect, state, bible, evidence_id)
    svc.repo.save(state)
    return s.CollectOut(
        evidence=views.evidence_out(item),
        new_contradictions=[views.contradiction_out(c) for c in new],
    )


@router.post(
    "/sessions/{session_id}/puzzles/{puzzle_id}/attempt", response_model=s.PuzzleAttemptOut
)
def attempt_puzzle(
    session_id: str, puzzle_id: str, body: s.PuzzleAttemptIn, svc: Svc
) -> s.PuzzleAttemptOut:
    state, bible = _load(svc, session_id)
    correct, unlocked = _run(game.attempt_puzzle, state, bible, puzzle_id, body.answer)
    svc.repo.save(state)
    return s.PuzzleAttemptOut(
        correct=correct,
        attempts=state.puzzle_attempts.get(puzzle_id, 0),
        unlocked_evidence=[views.evidence_out(e) for e in unlocked],
    )


@router.get("/sessions/{session_id}/puzzles/{puzzle_id}/hint", response_model=s.HintOut)
def puzzle_hint(session_id: str, puzzle_id: str, svc: Svc) -> s.HintOut:
    state, bible = _load(svc, session_id)
    hint, used, remaining = _run(game.next_hint, state, bible, puzzle_id)
    svc.repo.save(state)
    return s.HintOut(hint=hint, hints_used=used, hints_remaining=remaining)


@router.post("/sessions/{session_id}/npcs/{npc_id}/present", response_model=s.PresentOut)
def present_evidence(session_id: str, npc_id: str, body: s.PresentIn, svc: Svc) -> s.PresentOut:
    state, bible = _load(svc, session_id)
    out = _run(game.present, state, bible, npc_id, body.evidence_id)
    svc.repo.save(state)
    return s.PresentOut(
        npc_id=npc_id,
        evidence_id=body.evidence_id,
        reaction=out.reaction,
        emotion=out.emotion,
        trust=out.trust,
        trust_delta=out.trust_delta,
        lie_broken=out.lie_broken,
    )


@router.post("/sessions/{session_id}/npcs/{npc_id}/ask", response_model=s.AskOut)
async def ask_npc(session_id: str, npc_id: str, body: s.AskIn, svc: Svc) -> s.AskOut:
    state, bible = _load(svc, session_id)
    _run(game.require_npc, state, npc_id)
    ctx = await svc.interrogator.run(state, bible, npc_id, body.question)
    svc.repo.save(state)
    turn = ctx.turn
    assert turn is not None
    svc.repo.log_turn(
        session_id,
        turn,
        guard_violations=ctx.violations,
        model_id=ctx.model_id,
        llm_calls=ctx.llm_calls,
        latency_ms=ctx.latency_ms,
    )
    return s.AskOut(
        turn_id=turn.turn_id,
        npc_id=npc_id,
        answer=turn.answer,
        emotion=turn.emotion,
        trust=state.npcs[npc_id].trust,
        trust_delta=turn.trust_delta,
        revealed_fact_ids=turn.revealed_fact_ids,
        contradiction_detected=turn.contradiction_detected,
        guard_blocked=turn.guard_blocked,
    )


@router.get("/sessions/{session_id}/npcs/{npc_id}/dialogue", response_model=s.DialogueOut)
def npc_dialogue(session_id: str, npc_id: str, svc: Svc) -> s.DialogueOut:
    state, _ = _load(svc, session_id)
    _run(game.require_npc, state, npc_id)
    return s.DialogueOut(
        npc_id=npc_id, statements=[views.statement_out(t) for t in state.turns_with(npc_id)]
    )


@router.post("/sessions/{session_id}/statements/{statement_id}/pin", response_model=s.StatementOut)
def pin_statement(
    session_id: str, statement_id: str, svc: Svc, pinned: bool = True
) -> s.StatementOut:
    state, _ = _load(svc, session_id)
    turn = next((t for t in state.turns if t.turn_id == statement_id), None)
    if turn is None:
        raise HTTPException(404, "statement not found")
    turn.pinned = pinned
    svc.repo.save(state)
    return views.statement_out(turn)


@router.get("/sessions/{session_id}/board", response_model=s.BoardOut)
def board(session_id: str, svc: Svc) -> s.BoardOut:
    state, bible = _load(svc, session_id)
    return views.board_out(state, bible)


@router.post("/sessions/{session_id}/deduction", response_model=s.DeductionOut)
async def submit_deduction(session_id: str, body: s.DeductionIn, svc: Svc) -> s.DeductionOut:
    state, bible = _load(svc, session_id)
    result = _run(game.submit_deduction, state, bible, DeductionSubmission(**body.model_dump()))
    svc.repo.save(state)
    return s.DeductionOut(score=s.ScoreOut(**result.score.model_dump()), flags=result.flags)


@router.get("/sessions/{session_id}/debrief", response_model=s.DebriefOut)
def debrief(session_id: str, svc: Svc) -> s.DebriefOut:
    state, bible = _load(svc, session_id)
    if state.deduction is None:
        raise HTTPException(403, "submit a deduction first")
    return views.debrief_out(state, bible)
