"""추리 서술 LLM 피드백 (4-6). 점수에는 쓰지 않고 해설 화면의 피드백 문장에만 쓴다.

모델은 플레이어의 자유 서술을 읽고 근거 없는 주장, 논리 비약, 증거와 잘 연결한 부분만 표시한다.
정답(Solution)은 주지 않는다: 답이 맞았는지가 아니라 서술이 제출한 증거로 뒷받침되는지를 본다.
모든 표시는 서술 원문을 글자 그대로 인용해야 하고, 증거 연결은 제출한 증거만 가리켜야 한다 (코드로 확인).
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from app.core.llm.ports import LLMPort, Message
from app.core.llm.structured import generate_structured
from app.core.session import DeductionFeedbackRecord, DeductionRecord, SessionStore
from case_validator import CaseBible

log = logging.getLogger(__name__)

MAX_ITEMS = 5


class EvidenceLink(BaseModel):
    claim: str = Field(min_length=1, max_length=200)
    evidence_id: str


class DeductionFeedback(BaseModel):
    unsupported_claims: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    """제출한 증거로 뒷받침되지 않는 주장 (서술 원문 인용)."""
    logical_leaps: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    """앞뒤 사이에 근거 단계가 빠진 결론 (서술 원문 인용)."""
    evidence_links: list[EvidenceLink] = Field(default_factory=list, max_length=MAX_ITEMS)
    """제출한 증거로 잘 뒷받침된 주장과 그 증거."""


FEEDBACK_SYSTEM = (
    "너는 추리 게임에서 탐정의 최종 보고서를 검토하는 선배 형사다. 정답을 알려 주지 않고, "
    "보고서의 논리만 본다.\n"
    "- unsupported_claims: 함께 제출한 증거 어디에도 근거가 없는 주장\n"
    "- logical_leaps: 결론을 내리기 전에 필요한 근거 단계가 빠진 부분 (예: 기회만으로 범행을 단정)\n"
    "- evidence_links: 제출한 증거로 잘 뒷받침된 주장과 그 증거 ID\n"
    "- 모든 항목의 문장은 보고서에서 **글자 그대로** 옮긴 구절이어야 한다. 바꿔 쓰지 않는다.\n"
    "- 증거 ID는 아래 '제출한 증거' 목록에 있는 것만 쓴다.\n"
    "- 해당하는 것이 없으면 빈 목록으로 둔다.\n"
    'JSON 하나로만 답한다: {"unsupported_claims": [str], "logical_leaps": [str], '
    '"evidence_links": [{"claim": str, "evidence_id": str}]}'
)
NARRATIVE_HEADER = "## 탐정의 보고서"
EVIDENCE_HEADER = "## 제출한 증거"
ANSWER_HEADER = "## 탐정이 고른 답"


def build_feedback_messages(bible: CaseBible, record: DeductionRecord) -> list[Message]:
    culprit = bible.suspect(record.culprit_id)
    motives = {o.id: o.text for o in bible.deduction_options.motives}
    methods = {o.id: o.text for o in bible.deduction_options.methods}
    lines = [
        ANSWER_HEADER,
        f"- 범인: {culprit.name if culprit else record.culprit_id}",
        f"- 동기: {motives.get(record.motive_id, record.motive_id)}",
        f"- 수법: {methods.get(record.method_id, record.method_id)}",
        EVIDENCE_HEADER,
    ]
    for eid in record.evidence_ids:
        e = bible.evidence_by_id(eid)
        if e is not None:
            lines.append(f"- [{eid}] {e.name}: {e.description}")
    if not record.evidence_ids:
        lines.append("- (없음)")
    lines += [NARRATIVE_HEADER, record.narrative.strip()]
    return [Message("system", FEEDBACK_SYSTEM), Message("user", "\n".join(lines))]


def _compact(text: str) -> str:
    return "".join(text.split()).strip("\"'“”‘’.,…")


def ground(feedback: DeductionFeedback, narrative: str, evidence_ids: list[str]) -> dict[str, Any]:
    """서술에 없는 인용과 제출하지 않은 증거를 가리키는 연결을 버린다."""
    text = _compact(narrative)
    allowed = set(evidence_ids)

    def quoted(items: list[str]) -> list[str]:
        out: list[str] = []
        for item in items:
            c = _compact(item)
            if c and c in text and item.strip() not in out:
                out.append(item.strip())
        return out

    links = []
    for link in feedback.evidence_links:
        c = _compact(link.claim)
        if c and c in text and link.evidence_id in allowed:
            links.append({"claim": link.claim.strip(), "evidence_id": link.evidence_id})
    return {
        "unsupported_claims": quoted(feedback.unsupported_claims),
        "logical_leaps": quoted(feedback.logical_leaps),
        "evidence_links": links,
    }


async def make_feedback(
    llm: LLMPort, bible: CaseBible, record: DeductionRecord
) -> DeductionFeedbackRecord:
    if not record.narrative.strip():
        return DeductionFeedbackRecord(status="skipped")
    result = await generate_structured(
        llm,
        build_feedback_messages(bible, record),
        DeductionFeedback,
        fallback=DeductionFeedback(),
        temperature=0.0,
        max_tokens=700,
    )
    if result.fallback_used:
        return DeductionFeedbackRecord(status="unavailable", model_id=llm.model_id)
    grounded = ground(result.value, record.narrative, record.evidence_ids)
    dropped = (
        len(result.value.unsupported_claims)
        + len(result.value.logical_leaps)
        + len(result.value.evidence_links)
        - sum(len(v) for v in grounded.values())
    )
    if dropped:
        log.info("추리 피드백 중 원문·증거와 맞지 않는 항목 %d개 기각", dropped)
    return DeductionFeedbackRecord(
        status="ready",
        model_id=result.raw.model_id if result.raw else llm.model_id,
        dropped=dropped,
        **grounded,
    )


async def run_feedback(app_state: Any, session_id: str) -> None:
    """추리 제출 뒤 백그라운드에서 피드백을 만들어 세션에 저장한다. 실패하면 unavailable."""
    try:
        with app_state.sessionmaker() as db:
            store = SessionStore(db)
            session = store.get(session_id)
            record = session.state.deduction
            if record is None:
                return
            try:
                llm = app_state.llm_for_case(session.bible.case_id)
                record.feedback = await make_feedback(llm, session.bible, record)
            except Exception:
                log.exception("추리 피드백 생성 실패 (session=%s)", session_id)
                record.feedback = DeductionFeedbackRecord(status="unavailable")
            store.save(session)
    except Exception:
        log.exception("추리 피드백 저장 실패 (session=%s)", session_id)
