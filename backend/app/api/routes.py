from __future__ import annotations

from collections.abc import Iterator

from fastapi import APIRouter, BackgroundTasks, Depends, Request, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.api import schemas as v
from app.api import views
from app.core.game import AskOutcome, GameError, GameService
from app.deduction.feedback import run_feedback
from app.deduction.scoring import DeductionSubmission
from app.evidence.judge_runner import run_judgement, schedule_judgement

router = APIRouter(prefix="/sessions", tags=["game"])
ws_router = APIRouter(tags=["game"])


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


def wants_judgement(app_state, outcome: AskOutcome) -> bool:
    """회피 대사(가드 대체·기본값)는 실제 진술이 아니므로 판정하지 않는다."""
    return bool(app_state.llm_contradictions) and not outcome.turn.fallback_used


def ask_response(outcome: AskOutcome, debug_api: bool) -> v.AskResponse:
    turn = outcome.turn
    reply = turn.reply
    assert reply is not None and turn.guard is not None
    debug = None
    if debug_api:
        debug = v.AskDebug(
            grounding_fact_ids=[f.fact_id for f in turn.grounding],
            used_lie_ids=reply.used_lie_ids,
            guard_violations=turn.guard.violations,
            regenerated=turn.regenerated,
            fallback=turn.fallback_used,
            llm_calls=turn.llm_calls,
        )
    return v.AskResponse(
        answer=reply.answer,
        emotion=reply.emotion,
        revealed_fact_ids=reply.revealed_fact_ids,
        contradiction_detected=outcome.contradiction_detected,
        trust_delta=reply.trust_delta,
        turn=turn.turn_no,
        debug=debug,
    )


@router.post("/{session_id}/npcs/{npc_id}/ask", response_model=v.AskResponse)
async def ask(
    session_id: str,
    npc_id: str,
    body: v.AskRequest,
    request: Request,
    background: BackgroundTasks,
    svc: GameService = Service,
) -> v.AskResponse:
    outcome = await svc.ask(svc.load(session_id), npc_id, body.question)
    if wants_judgement(request.app.state, outcome):
        background.add_task(
            run_judgement, request.app.state, session_id, npc_id, outcome.turn.turn_no
        )
    return ask_response(outcome, request.app.state.debug_api)


@ws_router.websocket("/ws/interrogation/{session_id}/{npc_id}")
async def interrogation_ws(websocket: WebSocket, session_id: str, npc_id: str) -> None:
    """질문을 받아 답변 글자를 조각(delta)으로 보내고, 끝나면 최종 응답(final)을 보낸다.

    누설 가드가 답변을 바꾸면 final의 answer가 스트리밍된 글자와 다르다. 화면은 final로 교체한다.
    """
    await websocket.accept()
    state = websocket.app.state
    try:
        while True:
            try:
                body = v.AskRequest.model_validate(await websocket.receive_json())
            except (ValidationError, ValueError):
                await websocket.send_json({"type": "error", "detail": "질문 형식이 올바르지 않다."})
                continue
            with state.sessionmaker() as db:
                svc = GameService(db, state.llm_for_case, state.embedder)

                async def send_delta(text: str) -> None:
                    await websocket.send_json({"type": "delta", "text": text})

                try:
                    outcome = await svc.ask(svc.load(session_id), npc_id, body.question, send_delta)
                except GameError as exc:
                    await websocket.send_json({"type": "error", "detail": exc.message})
                    continue
                final = ask_response(outcome, state.debug_api)
                await websocket.send_json({"type": "final", **final.model_dump()})
                if wants_judgement(state, outcome):
                    schedule_judgement(state, session_id, npc_id, outcome.turn.turn_no)
    except WebSocketDisconnect:
        return


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
        contradictions=contradiction_views(svc, session, answer_by_turn),
    )


def contradiction_views(svc: GameService, session, answer_by_turn) -> list[v.ContradictionView]:
    """규칙 판정을 먼저, LLM 판정은 그 뒤에 둔다. 규칙이 이미 찾은 (진술, 증거) 쌍은 LLM 쪽에서 뺀다."""
    rule = svc.contradictions(session)
    views_: list[v.ContradictionView] = [
        v.ContradictionView(
            npc_id=c.npc_id,
            statement_turn=c.statement_turn,
            statement=answer_by_turn.get((c.npc_id, c.statement_turn), ""),
            evidence_id=c.evidence_id,
            evidence_name=svc.evidence(session, c.evidence_id).name,
            type=c.type,
            source=c.source,
        )
        for c in rule
    ]
    covered = {(c.npc_id, c.evidence_id) for c in rule}
    for c in svc.llm_contradictions(session):
        if c.evidence_ids and all((c.npc_id, e) in covered for e in c.evidence_ids):
            continue
        evidence_id = c.evidence_ids[0] if c.evidence_ids else None
        views_.append(
            v.ContradictionView(
                npc_id=c.npc_id,
                statement_turn=c.statement_turn,
                statement=answer_by_turn.get((c.npc_id, c.statement_turn), ""),
                evidence_id=evidence_id,
                evidence_name=svc.evidence(session, evidence_id).name if evidence_id else None,
                type=c.type,
                source="llm",
                confidence=c.confidence,
                explanation=c.explanation,
                other_statements=[
                    answer_by_turn.get((c.npc_id, t), "")
                    for t in c.statement_turns
                    if t != c.statement_turn
                ],
            )
        )
    return views_


@router.post("/{session_id}/deduction", response_model=v.DeductionResultView)
def deduce(
    session_id: str,
    body: DeductionSubmission,
    request: Request,
    background: BackgroundTasks,
    svc: GameService = Service,
) -> v.DeductionResultView:
    session = svc.load(session_id)
    record = svc.deduce(session, body, with_feedback=request.app.state.deduction_feedback)
    if record.feedback is not None and record.feedback.status == "pending":
        background.add_task(run_feedback, request.app.state, session_id)
    return views.deduction_result(record)


@router.get("/{session_id}/debrief", response_model=v.DebriefView)
def debrief(session_id: str, svc: GameService = Service) -> v.DebriefView:
    session = svc.load(session_id)
    return views.debrief_view(session, svc.require_deduction(session))
