"""SQLAlchemy + SQLite persistence: session state snapshots and the interrogation log."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.pool import StaticPool

from app.core.session import GameState, Turn


class Base(DeclarativeBase):
    pass


class SessionRow(Base):
    __tablename__ = "game_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(64))
    case_sha256: Mapped[str] = mapped_column(String(64))
    state: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DialogueRow(Base):
    __tablename__ = "dialogue_turns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("game_sessions.id"), index=True)
    turn_id: Mapped[str] = mapped_column(String(16))
    npc_id: Mapped[str] = mapped_column(String(64))
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    emotion: Mapped[str] = mapped_column(String(16))
    revealed_fact_ids: Mapped[list[str]] = mapped_column(JSON)
    used_fact_ids: Mapped[list[str]] = mapped_column(JSON)
    guard_blocked: Mapped[bool] = mapped_column(Boolean)
    guard_violations: Mapped[list[str]] = mapped_column(JSON)
    model_id: Mapped[str] = mapped_column(String(64))
    llm_calls: Mapped[int] = mapped_column(Integer)
    latency_ms: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def make_engine(url: str) -> Engine:
    kwargs: dict[str, Any] = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
    engine = create_engine(url, **kwargs)
    Base.metadata.create_all(engine)
    return engine


class SessionRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def create(self, state: GameState) -> None:
        now = datetime.now(UTC)
        with Session(self.engine) as db, db.begin():
            db.add(
                SessionRow(
                    id=state.session_id,
                    case_id=state.case_id,
                    case_sha256=state.case_sha256,
                    state=state.model_dump(mode="json"),
                    created_at=now,
                    updated_at=now,
                )
            )

    def get(self, session_id: str) -> GameState | None:
        with Session(self.engine) as db:
            row = db.get(SessionRow, session_id)
            return GameState.model_validate(row.state) if row else None

    def save(self, state: GameState) -> None:
        with Session(self.engine) as db, db.begin():
            row = db.get(SessionRow, state.session_id)
            if row is None:
                raise KeyError(state.session_id)
            row.state = state.model_dump(mode="json")
            row.updated_at = datetime.now(UTC)

    def log_turn(
        self,
        session_id: str,
        turn: Turn,
        *,
        guard_violations: list[str],
        model_id: str,
        llm_calls: int,
        latency_ms: float,
    ) -> None:
        with Session(self.engine) as db, db.begin():
            db.add(
                DialogueRow(
                    session_id=session_id,
                    turn_id=turn.turn_id,
                    npc_id=turn.npc_id,
                    question=turn.question,
                    answer=turn.answer,
                    emotion=turn.emotion,
                    revealed_fact_ids=turn.revealed_fact_ids,
                    used_fact_ids=turn.used_fact_ids,
                    guard_blocked=turn.guard_blocked,
                    guard_violations=guard_violations,
                    model_id=model_id,
                    llm_calls=llm_calls,
                    latency_ms=latency_ms,
                    created_at=datetime.now(UTC),
                )
            )

    def dialogue_log(self, session_id: str) -> list[DialogueRow]:
        with Session(self.engine) as db:
            rows = db.query(DialogueRow).filter_by(session_id=session_id).order_by(DialogueRow.id)
            return list(rows)
