from __future__ import annotations

from collections.abc import Iterator

from fastapi import APIRouter, Depends, Request

from app.api import schemas as v
from app.api import views
from app.core.game import GameService
from app.deduction.scoring import DeductionSubmission

router = APIRouter(prefix="/sessions", tags=["game"])


def get_service(request: Request) -> Iterator[GameService]:
    state = request.app.state
    with state.sessionmaker() as db:
        yield GameService(db, state.llm_for_case, state.embedder)


Service = Depends(get_service)


@router.post("", response_model=v.SessionView, status_code=201)
def create_session(body: v.CreateSessionRequest, svc: GameService = Service) -> v.SessionView:
    return views.session_view(svc.create(body.case_id))


@router.get("/{session_id}", response_model=v.SessionView)
def get_session(session_id: str, svc: GameService = Service) -> v.SessionView:
    return views.session_view(svc.load(session_id))


@router.post("/{session_id}/evidence/{evidence_id}/collect", response_model=v.CollectResponse)
def collect(session_id: str, evidence_id: str, svc: GameService = Service) -> v.CollectResponse:
    session = svc.load(session_id)
    evidence, found = svc.collect(session, evidence_id)
    return v.CollectResponse(
        evidence=views.evidence_view(session.bible, evidence),
        puzzles=[views.puzzle_view(session, p) for p in session.bible.puzzles],
        contradictions_found=found,
    )


@router.post("/{session_id}/puzzles/{puzzle_id}/attempt", response_model=v.PuzzleAttemptResponse)
def attempt_puzzle(
    session_id: str, puzzle_id: str, body: v.PuzzleAttemptRequest, svc: GameService = Service
) -> v.PuzzleAttemptResponse:
    session = svc.load(session_id)
    correct, unlocked = svc.attempt_puzzle(session, puzzle_id, body.answer)
    return v.PuzzleAttemptResponse(
        correct=correct,
        unlocked=[views.evidence_view(session.bible, e) for e in unlocked],
        puzzle=views.puzzle_view(session, svc.puzzle(session, puzzle_id)),
    )


@router.get("/{session_id}/puzzles/{puzzle_id}/hint", response_model=v.HintResponse)
def hint(session_id: str, puzzle_id: str, svc: GameService = Service) -> v.HintResponse:
    text, used, remaining = svc.hint(svc.load(session_id), puzzle_id)
    return v.HintResponse(hint=text, hints_used=used, remaining=remaining)


@router.post("/{session_id}/npcs/{npc_id}/present", response_model=v.PresentResponse)
def present(
    session_id: str, npc_id: str, body: v.PresentRequest, svc: GameService = Service
) -> v.PresentResponse:
    session = svc.load(session_id)
    reaction = svc.present(session, npc_id, body.evidence_id)
    return v.PresentResponse(npc=views.npc_state(session, npc_id), reaction=reaction)


@router.post("/{session_id}/npcs/{npc_id}/ask", response_model=v.AskResponse)
async def ask(
    session_id: str, npc_id: str, body: v.AskRequest, svc: GameService = Service
) -> v.AskResponse:
    session = svc.load(session_id)
    outcome = await svc.ask(session, npc_id, body.question)
    reply = outcome.turn.reply
    assert reply is not None
    return v.AskResponse(
        answer=reply.answer,
        emotion=reply.emotion,
        revealed_fact_ids=reply.revealed_fact_ids,
        contradiction_detected=outcome.contradiction_detected,
        trust_delta=reply.trust_delta,
        turn=outcome.turn.turn_no,
    )


@router.get("/{session_id}/board", response_model=v.BoardView)
def board(session_id: str, svc: GameService = Service) -> v.BoardView:
    session = svc.load(session_id)
    bible = session.bible
    pairs = svc.statements(session)
    answer_by_turn = {(a.npc_id, a.turn): a.text for _, a in pairs}
    return v.BoardView(
        evidence=[
            views.evidence_view(bible, e)
            for eid in session.state.collected
            if (e := bible.evidence_by_id(eid))
        ],
        statements=[
            v.StatementView(
                npc_id=a.npc_id, turn=a.turn, question=q.text, answer=a.text, emotion=a.emotion
            )
            for q, a in pairs
        ],
        contradictions=[
            v.ContradictionView(
                npc_id=c.npc_id,
                statement_turn=c.statement_turn,
                statement=answer_by_turn.get((c.npc_id, c.statement_turn), ""),
                evidence_id=c.evidence_id,
                evidence_name=svc.evidence(session, c.evidence_id).name,
                type=c.type,
                source=c.source,
            )
            for c in svc.contradictions(session)
        ],
    )


@router.post("/{session_id}/deduction", response_model=v.DeductionResultView)
def deduce(
    session_id: str, body: DeductionSubmission, svc: GameService = Service
) -> v.DeductionResultView:
    return views.deduction_result(svc.deduce(svc.load(session_id), body))


@router.get("/{session_id}/debrief", response_model=v.DebriefView)
def debrief(session_id: str, svc: GameService = Service) -> v.DebriefView:
    session = svc.load(session_id)
    return views.debrief_view(session, svc.require_deduction(session))
