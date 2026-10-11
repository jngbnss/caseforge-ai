from playthrough import CORRECT_DEDUCTION, PHYSICAL, Recorder, play_until_deduction


def test_full_case_can_be_cleared_through_the_api(client, services):
    rec = Recorder(client)
    sid = play_until_deduction(rec)
    base = f"/sessions/{sid}"

    state = rec.call("GET", base)
    collected = {e["evidence_id"] for e in state["collected_evidence"]}
    assert collected == set(PHYSICAL) | {"rec-01", "rec-02", "rec-03"}
    assert all(p["status"] == "solved" for p in state["puzzles"])

    board = rec.call("GET", f"{base}/board")
    by_npc = {c["npc_id"]: c for c in board["contradictions"]}
    assert set(by_npc) == {"suspect-01", "suspect-02", "suspect-03"}
    assert all(c["source"] == "rule" for c in board["contradictions"])
    assert by_npc["suspect-02"]["type"] == "time"
    assert board["statements"] and board["statements"][0]["pinned"]
    assert any(m["time"] == "21:07" for m in board["timeline"])

    rec.call("GET", f"{base}/debrief", expected=403)
    result = rec.call("POST", f"{base}/deduction", json=CORRECT_DEDUCTION)
    assert result["score"] == {
        "culprit": 40,
        "motive": 20,
        "method": 20,
        "evidence": 20,
        "total": 100,
    }
    assert result["flags"] == []
    rec.call("POST", f"{base}/deduction", expected=409, json=CORRECT_DEDUCTION)

    debrief = rec.call("GET", f"{base}/debrief")
    assert debrief["culprit"]["name"] == "윤재민"
    assert debrief["missed_clues"] == []
    assert len(debrief["timeline"]) == 15

    log = services.repo.dialogue_log(sid)
    assert len(log) == 7
    assert all(isinstance(row.used_fact_ids, list) for row in log)


def test_interrogation_reacts_to_presented_evidence(client):
    rec = Recorder(client)
    sid = rec.call("POST", "/sessions", expected=201)["session_id"]
    base = f"/sessions/{sid}"
    ask = {"question": "21시 이후 어디 있었어요?"}

    before = rec.call("POST", f"{base}/npcs/suspect-02/ask", json=ask)
    assert "경비실" in before["answer"] and before["revealed_fact_ids"] == []

    rec.call("POST", f"{base}/npcs/suspect-02/present", expected=403, json={"evidence_id": "ev-02"})
    rec.call("POST", f"{base}/evidence/ev-02/collect")
    contradictions = rec.call("GET", f"{base}/board")["contradictions"]
    assert [c["npc_id"] for c in contradictions] == ["suspect-02"]

    presented = rec.call("POST", f"{base}/npcs/suspect-02/present", json={"evidence_id": "ev-02"})
    assert presented["lie_broken"] and presented["trust_delta"] == 1

    after = rec.call("POST", f"{base}/npcs/suspect-02/ask", json=ask)
    assert set(after["revealed_fact_ids"]) == {"fact-007", "fact-008"}
    assert not after["guard_blocked"]
    assert after["trust"] == 3


def test_game_rules_are_enforced(client):
    rec = Recorder(client)
    sid = rec.call("POST", "/sessions", expected=201)["session_id"]
    base = f"/sessions/{sid}"
    rec.call("POST", f"{base}/evidence/rec-01/collect", expected=403)  # puzzle reward
    rec.call("POST", f"{base}/evidence/ev-99/collect", expected=404)
    rec.call("POST", f"{base}/puzzles/pz-02/attempt", expected=403, json={"answer": "0784"})
    wrong = rec.call(
        "POST", f"{base}/puzzles/pz-01/attempt", json={"answer": ["fr-a", "fr-b", "fr-c", "fr-d"]}
    )
    assert wrong == {"correct": False, "attempts": 1, "unlocked_evidence": []}
    rec.call("POST", f"{base}/npcs/suspect-09/ask", expected=404, json={"question": "누구세요?"})
    rec.call(
        "POST", f"{base}/deduction", expected=400, json={**_guess(), "evidence_ids": ["ev-03"]}
    )
    rec.call("GET", "/sessions/nope", expected=404)


def test_unsupported_guess_is_flagged(client):
    rec = Recorder(client)
    sid = rec.call("POST", "/sessions", expected=201)["session_id"]
    result = rec.call("POST", f"/sessions/{sid}/deduction", json=_guess())
    assert result["score"]["culprit"] == 40
    assert result["score"]["evidence"] == 0
    assert "unsupported_guess" in result["flags"]
    debrief = rec.call("GET", f"/sessions/{sid}/debrief")
    assert {m["id"] for m in debrief["missed_clues"]} >= {"ev-03", "pz-01"}


def _guess() -> dict:
    return {
        "culprit_id": "suspect-03",
        "motive_id": "motive-revenge",
        "method_id": "method-own-card",
        "evidence_ids": [],
        "narrative": "",
    }
