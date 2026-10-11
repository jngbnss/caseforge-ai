"""게임 규칙 서비스. 모든 판정(수집, 퍼즐, 제시, 채점)은 여기서 코드로 한다."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.agents.interrogation import Interrogator, Turn
from app.agents.knowledge_scope import UnknownNpcError, build_scope
from app.core.db import ContradictionRow, DialogueRow, LlmContradictionRow
from app.core.embedding.ports import EmbeddingPort
from app.core.llm.ports import LLMPort
from app.core.session import (
    CaseChangedError,
    DeductionFeedbackRecord,
    GameSession,
    SessionNotFoundError,
    SessionStore,
)
from app.deduction.scoring import DeductionSubmission, score_deduction
from app.evidence.contradiction import detect_rule_contradictions
from case_validator import evaluate
from case_validator.loader import CaseLoadError
from case_validator.schema import Evidence, Puzzle


class GameError(Exception):
    status = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFound(GameError):
    status = 404


class Conflict(GameError):
    status = 409


@dataclass
class AskOutcome:
    turn: Turn
    contradiction_detected: bool


class GameService:
    def __init__(
        self,
        db: DbSession,
        llm_for_case: Callable[[str], LLMPort],
        embedder: EmbeddingPort,
    ) -> None:
        self.db = db
        self.store = SessionStore(db)
        self.llm_for_case = llm_for_case
        self.embedder = embedder

    # ---------- 조회 헬퍼 ----------

    def load(self, session_id: str) -> GameSession:
        try:
            return self.store.get(session_id)
        except SessionNotFoundError as exc:
            raise NotFound("세션을 찾을 수 없다") from exc
        except CaseChangedError as exc:
            raise Conflict(str(exc)) from exc

    @staticmethod
    def evidence(session: GameSession, evidence_id: str) -> Evidence:
        evidence = session.bible.evidence_by_id(evidence_id)
        if evidence is None:
            raise NotFound(f"증거 {evidence_id}가 없다")
        return evidence

    @staticmethod
    def puzzle(session: GameSession, puzzle_id: str) -> Puzzle:
        puzzle = next((p for p in session.bible.puzzles if p.puzzle_id == puzzle_id), None)
        if puzzle is None:
            raise NotFound(f"퍼즐 {puzzle_id}가 없다")
        return puzzle

    @staticmethod
    def require_npc(session: GameSession, npc_id: str) -> None:
        if session.bible.suspect(npc_id) is None:
            raise NotFound(f"용의자 {npc_id}가 없다")

    @staticmethod
    def puzzle_available(session: GameSession, puzzle: Puzzle) -> bool:
        return evaluate(puzzle.requires, session.state.play_state())

    def _require_open(self, session: GameSession) -> None:
        if session.state.deduction is not None:
            raise Conflict("이미 추리를 제출해 수사가 끝났다")

    # ---------- 행동 ----------

    def create(self, case_id: str) -> GameSession:
        try:
            return self.store.create(case_id)
        except CaseLoadError as exc:
            raise NotFound(f"사건 {case_id}가 없다") from exc

    def collect(self, session: GameSession, evidence_id: str) -> tuple[Evidence, int]:
        self._require_open(session)
        evidence = self.evidence(session, evidence_id)
        if evidence.source != "scene":
            raise GameError("퍼즐로만 얻을 수 있는 기록이다")
        if evidence_id in session.state.collected:
            raise Conflict("이미 수집한 증거다")
        if not evaluate(evidence.discoverable, session.state.play_state()):
            raise Conflict("아직 조사할 수 없는 곳이다")
        session.state.collected.append(evidence_id)
        self.store.save(session)
        return evidence, len(detect_rule_contradictions(self.db, session))

    def attempt_puzzle(
        self, session: GameSession, puzzle_id: str, answer: str | list[str]
    ) -> tuple[bool, list[Evidence]]:
        self._require_open(session)
        puzzle = self.puzzle(session, puzzle_id)
        if not self.puzzle_available(session, puzzle):
            raise Conflict("아직 풀 수 없는 퍼즐이다")
        if puzzle_id in session.state.solved:
            raise Conflict("이미 푼 퍼즐이다")
        state = session.state
        state.puzzle_attempts[puzzle_id] = state.puzzle_attempts.get(puzzle_id, 0) + 1
        if puzzle.input_type == "code":
            correct = isinstance(answer, str) and answer.strip() == puzzle.answer
        else:
            correct = isinstance(answer, list) and tuple(answer) == tuple(puzzle.answer)
        unlocked: list[Evidence] = []
        if correct:
            state.solved.append(puzzle_id)
            for eid in puzzle.unlocks_evidence:
                if eid not in state.collected:
                    state.collected.append(eid)
                    unlocked.append(self.evidence(session, eid))
        self.store.save(session)
        if unlocked:
            detect_rule_contradictions(self.db, session)
        return correct, unlocked

    def hint(self, session: GameSession, puzzle_id: str) -> tuple[str, int, int]:
        puzzle = self.puzzle(session, puzzle_id)
        if not self.puzzle_available(session, puzzle):
            raise Conflict("아직 풀 수 없는 퍼즐이다")
        if not puzzle.hints:
            raise Conflict("힌트가 없는 퍼즐이다")
        used = min(session.state.hints_used.get(puzzle_id, 0) + 1, len(puzzle.hints))
        session.state.hints_used[puzzle_id] = used
        self.store.save(session)
        return puzzle.hints[used - 1], used, len(puzzle.hints) - used

    def present(self, session: GameSession, npc_id: str, evidence_id: str) -> str:
        """증거를 제시한다. 이 NPC의 반응이 달라지면 'shaken'."""
        self._require_open(session)
        self.require_npc(session, npc_id)
        self.evidence(session, evidence_id)
        if evidence_id not in session.state.collected:
            raise Conflict("수집하지 않은 증거는 제시할 수 없다")
        presented = session.state.presented.setdefault(npc_id, [])
        if evidence_id in presented:
            return "none"
        before = build_scope(session.bible, session.state, npc_id)
        presented.append(evidence_id)
        after = build_scope(session.bible, session.state, npc_id)
        own_unlocked = (after.allowed_fact_ids - before.allowed_fact_ids) - {
            fid for e in after.presented for fid in e.proves_fact_ids
        }
        shaken = len(after.broken_lies) > len(before.broken_lies) or bool(own_unlocked)
        if shaken:
            session.state.emotion[npc_id] = "shaken"
        self.store.save(session)
        return "shaken" if shaken else "none"

    async def ask(
        self,
        session: GameSession,
        npc_id: str,
        question: str,
        on_delta: Callable[[str], Awaitable[None]] | None = None,
    ) -> AskOutcome:
        self._require_open(session)
        self.require_npc(session, npc_id)
        interrogator = Interrogator(
            self.llm_for_case(session.bible.case_id), self.embedder, self.db
        )
        try:
            turn = await interrogator.ask(session, npc_id, question, on_delta)
        except UnknownNpcError as exc:
            raise NotFound(f"용의자 {npc_id}가 없다") from exc
        self.store.save(session)
        new = detect_rule_contradictions(self.db, session)
        detected = any(c.npc_id == npc_id and c.statement_turn == turn.turn_no for c in new)
        return AskOutcome(turn, detected)

    def statements(self, session: GameSession) -> list[tuple[DialogueRow, DialogueRow]]:
        rows = self.db.scalars(
            select(DialogueRow).where(DialogueRow.session_id == session.id).order_by(DialogueRow.id)
        ).all()
        pending: dict[tuple[str, int], DialogueRow] = {}
        pairs = []
        for row in rows:
            if row.role == "player":
                pending[(row.npc_id, row.turn)] = row
            elif (q := pending.pop((row.npc_id, row.turn), None)) is not None:
                pairs.append((q, row))
        return pairs

    def contradictions(self, session: GameSession) -> list[ContradictionRow]:
        detect_rule_contradictions(self.db, session)
        return list(
            self.db.scalars(
                select(ContradictionRow)
                .where(ContradictionRow.session_id == session.id)
                .order_by(ContradictionRow.id)
            )
        )

    def llm_contradictions(self, session: GameSession) -> list[LlmContradictionRow]:
        return list(
            self.db.scalars(
                select(LlmContradictionRow)
                .where(LlmContradictionRow.session_id == session.id)
                .order_by(LlmContradictionRow.id)
            )
        )

    def deduce(
        self, session: GameSession, sub: DeductionSubmission, *, with_feedback: bool = False
    ):
        self._require_open(session)
        bible = session.bible
        if bible.suspect(sub.culprit_id) is None:
            raise GameError("용의자 목록에 없는 범인이다")
        if sub.motive_id not in {o.id for o in bible.deduction_options.motives}:
            raise GameError("선택지에 없는 동기다")
        if sub.method_id not in {o.id for o in bible.deduction_options.methods}:
            raise GameError("선택지에 없는 수법이다")
        missing = [e for e in sub.evidence_ids if e not in session.state.collected]
        if missing:
            raise GameError(f"수집하지 않은 증거는 제출할 수 없다: {', '.join(missing)}")
        session.state.deduction = score_deduction(bible, sub)
        if with_feedback and sub.narrative.strip():
            session.state.deduction.feedback = DeductionFeedbackRecord(status="pending")
        self.store.save(session)
        return session.state.deduction

    def require_deduction(self, session: GameSession):
        if session.state.deduction is None:
            raise Conflict("추리를 제출한 뒤에 해설을 볼 수 있다")
        return session.state.deduction
