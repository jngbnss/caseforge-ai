"""LLM 모순 판정을 심문 응답 뒤에 따로 돌린다. 심문 지연에 영향을 주지 않는다.

REST는 FastAPI BackgroundTasks(응답을 보낸 뒤 실행), WebSocket은 asyncio 작업으로 돌린다.
판정은 자기 DB 세션을 연다. 실패해도 게임은 계속되며 로그만 남긴다.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.core.config import settings
from app.core.session import SessionStore
from app.evidence.llm_contradiction import judge_turn

log = logging.getLogger(__name__)


async def run_judgement(app_state: Any, session_id: str, npc_id: str, turn_no: int) -> int:
    """판정 한 번. 새로 저장한 모순 수를 돌려준다."""
    try:
        with app_state.sessionmaker() as db:
            session = SessionStore(db).get(session_id)
            llm = app_state.llm_for_case(session.bible.case_id)
            verify = settings.llm_contradiction_verify
            return len(await judge_turn(llm, db, session, npc_id, turn_no, verify=verify))
    except Exception:
        log.exception("LLM 모순 판정 실패 (session=%s npc=%s turn=%s)", session_id, npc_id, turn_no)
        return 0


def schedule_judgement(app_state: Any, session_id: str, npc_id: str, turn_no: int) -> None:
    """WebSocket용: 이벤트 루프에 판정 작업을 올리고 참조를 보관한다 (GC 방지, 테스트 대기용)."""
    task = asyncio.create_task(run_judgement(app_state, session_id, npc_id, turn_no))
    app_state.judge_tasks.add(task)
    task.add_done_callback(app_state.judge_tasks.discard)
