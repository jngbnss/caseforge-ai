"""SQLite 저장소. 세션 상태는 JSON 한 덩어리, 대화와 모순은 행 단위로 저장한다."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class SessionRow(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(64))
    case_sha256: Mapped[str] = mapped_column(String(64))
    state: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class DialogueRow(Base):
    """심문 한 턴의 발화. NPC 응답과 그 근거(fact_id)를 따로 저장한다."""

    __tablename__ = "dialogue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    npc_id: Mapped[str] = mapped_column(String(32))
    turn: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(16))  # player | npc
    text: Mapped[str] = mapped_column(Text)
    emotion: Mapped[str | None] = mapped_column(String(16), nullable=True)
    revealed_fact_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    grounding_fact_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    used_lie_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    guard: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ContradictionRow(Base):
    __tablename__ = "contradictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    npc_id: Mapped[str] = mapped_column(String(32))
    lie_id: Mapped[str] = mapped_column(String(32))
    statement_turn: Mapped[int] = mapped_column(Integer)
    evidence_id: Mapped[str] = mapped_column(String(32))
    type: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(8))  # rule | llm
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


def make_engine(url: str) -> Engine:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args)
    Base.metadata.create_all(engine)
    return engine


def make_sessionmaker(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False)
