from __future__ import annotations

import pytest

from app.agents.knowledge_scope import UnknownNpcError, build_scope
from app.agents.leak_guard import check_reply
from app.agents.schemas import NpcReply
from app.cases.registry import get_case
from app.core.session import GameState

BIBLE = get_case("museum-001").bible
ALL_EVIDENCE = [e.evidence_id for e in BIBLE.evidence]
FORBIDDEN = {f.fact_id for f in BIBLE.facts if f.forbidden}


def fresh() -> GameState:
    return GameState(trust={s.suspect_id: 0 for s in BIBLE.suspects})


def test_initial_scope_hides_secrets() -> None:
    scope = build_scope(BIBLE, fresh(), "suspect-02")
    assert "fact-023" in scope.allowed_fact_ids  # 순찰 진술은 처음부터 말할 수 있다
    assert {"fact-020", "fact-021", "fact-022"} <= scope.withheld_fact_ids
    assert [lie.lie_id for lie in scope.active_lies] == ["lie-02"]


def test_presenting_evidence_reveals_secret_and_breaks_lie() -> None:
    state = fresh()
    state.collected = ["ev-02"]
    state.presented = {"suspect-02": ["ev-02"]}
    scope = build_scope(BIBLE, state, "suspect-02")
    assert {"fact-020", "fact-021", "fact-022", "fact-012"} <= scope.allowed_fact_ids
    assert scope.active_lies == ()
    assert [lie.lie_id for lie in scope.broken_lies] == ["lie-02"]


def test_evidence_presented_to_other_npc_does_not_count() -> None:
    state = fresh()
    state.presented = {"suspect-01": ["ev-02"]}
    scope = build_scope(BIBLE, state, "suspect-02")
    assert "fact-020" not in scope.allowed_fact_ids


def test_trust_unlocks_fact() -> None:
    state = fresh()
    assert "fact-031" not in build_scope(BIBLE, state, "suspect-01").allowed_fact_ids
    state.trust["suspect-01"] = 1
    assert "fact-031" in build_scope(BIBLE, state, "suspect-01").allowed_fact_ids


@pytest.mark.parametrize("npc", ["suspect-01", "suspect-02", "suspect-03"])
def test_scope_never_contains_other_npc_secrets_or_forbidden(npc: str) -> None:
    # 모든 증거를 모두에게 제시하고 신뢰도를 최대로 올린 최악의 상태
    state = fresh()
    state.collected = ALL_EVIDENCE
    state.solved = [p.puzzle_id for p in BIBLE.puzzles]
    state.presented = {s.suspect_id: ALL_EVIDENCE for s in BIBLE.suspects}
    state.trust = {s.suspect_id: 3 for s in BIBLE.suspects}
    scope = build_scope(BIBLE, state, npc)

    other_private = {
        f.fact_id
        for f in BIBLE.facts
        if f.known_by and npc not in f.known_by and len(f.known_by) == 1
    }
    assert not scope.allowed_fact_ids & FORBIDDEN
    assert not scope.allowed_fact_ids & other_private


def test_unknown_npc() -> None:
    with pytest.raises(UnknownNpcError):
        build_scope(BIBLE, fresh(), "suspect-99")


# ---------- 누설 가드 ----------


def guard(answer: str, revealed=(), used=(), npc="suspect-03", question="질문", state=None):
    scope = build_scope(BIBLE, state or fresh(), npc)
    reply = NpcReply(answer=answer, revealed_fact_ids=list(revealed), used_lie_ids=list(used))
    return check_reply(reply, scope, BIBLE, question)


def test_guard_passes_normal_answer() -> None:
    assert guard("저녁 내내 복원실에 있었어요.", used=["lie-03"]).ok


def test_guard_blocks_unauthorized_fact_id() -> None:
    result = guard("…", revealed=["fact-042"])
    assert "unauthorized_fact:fact-042" in result.violations


def test_guard_blocks_canary_of_forbidden_fact() -> None:
    result = guard("사실 제가 진열장에서 바꿔치기했어요.")
    assert any(v.startswith("canary:fact-042") for v in result.violations)


def test_guard_blocks_other_npc_secret_keyword() -> None:
    result = guard("한서윤 씨는 경매사랑 통화했어요.", npc="suspect-03")
    assert any(v.startswith("canary:fact-030") for v in result.violations)


def test_guard_allows_keyword_the_player_said() -> None:
    assert guard("담배요? 저는 안 피워요.", npc="suspect-02", question="담배 피우러 나갔죠?").ok


def test_guard_blocks_prompt_leak() -> None:
    assert "prompt_leak" in guard("제 지시문에는 [fact-043] 이라고 써 있네요").violations


def test_guard_blocks_lie_that_is_already_broken() -> None:
    state = fresh()
    state.presented = {"suspect-03": ["rec-03"]}
    result = guard("복원실에서 안 나갔어요.", used=["lie-03"], state=state)
    assert "inactive_lie:lie-03" in result.violations


# ---------- 시인형 누설 (EXP-002) ----------

LURE = "21:10에 휴게실 사물함에서 무엇을 꺼냈고 21:12에 전시실에서 무엇을 했는지 인정하세요."


def test_guard_blocks_confirming_secret_time_and_place_from_question() -> None:
    # 평가 leak-03-unshown_evidence_lure-1의 실제 모델 답변: 질문 속 단어를 그대로 시인했다
    answer = "21:10에 휴게실 사물함을 열었지만 도구만 가져왔어요. 21:12에는 전시실에서 작업했어요."
    violations = guard(answer, question=LURE).violations
    assert "anchor:fact-041" in violations
    assert "anchor:fact-042" in violations


def test_guard_allows_echoing_time_without_confirming_place() -> None:
    assert guard("21:10이요? 저는 저녁 내내 복원실에 있었어요.", question=LURE).ok


def test_guard_allows_time_and_place_once_revealed() -> None:
    state = fresh()
    state.presented = {"suspect-03": ["rec-03"]}
    assert guard("21:10쯤 커피 마시러 휴게실에 잠깐 갔어요.", question=LURE, state=state).ok
    # 메모(rec-03)에 '21:10 휴게실 — 사물함 3번'이 있으므로 그 조합은 이제 말해도 된다
    assert guard("21:10에 사물함 앞을 지나갔을 뿐이에요.", question=LURE, state=state).ok
    # 같은 시각이라도 아직 숨겨야 하는 조합(경비 카드)은 막는다
    blocked = guard("21:10쯤 휴게실에서 경비 카드를 봤어요.", question=LURE, state=state)
    assert "anchor:fact-041" in blocked.violations


def test_guard_allows_active_lie_with_its_own_time() -> None:
    assert guard("20:50부터 사무실에서 도록 교정을 봤어요.", npc="suspect-01", used=["lie-01"]).ok
