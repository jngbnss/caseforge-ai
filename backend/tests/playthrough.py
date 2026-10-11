"""Scripted full playthrough of museum-001 through the public API only.

Every response is recorded so leak tests can inspect everything a client ever received.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi.testclient import TestClient

PHYSICAL = ["ev-01", "ev-02", "ev-03", "ev-04", "ev-05"]
PUZZLE_ANSWERS: dict[str, Any] = {
    "pz-01": ["fr-c", "fr-a", "fr-d", "fr-b"],
    "pz-02": "0784",
    "pz-03": ["mp-c", "mp-a", "mp-d", "mp-b"],
}
CORRECT_DEDUCTION = {
    "culprit_id": "suspect-03",
    "motive_id": "motive-gambling-debt",
    "method_id": "method-card-theft-swap",
    "evidence_ids": ["ev-03", "ev-04", "rec-01", "rec-03", "rec-02"],
    "narrative": "윤재민이 CCTV를 끄고 박도현의 카드를 몰래 써서 모조품과 바꿔치기했다.",
}


@dataclass
class Recorder:
    client: TestClient
    responses: list[tuple[str, Any]] = field(default_factory=list)

    def call(self, method: str, url: str, expected: int = 200, **kwargs: Any) -> Any:
        res = self.client.request(method, url, **kwargs)
        assert res.status_code == expected, (method, url, res.status_code, res.text)
        body = res.json()
        self.responses.append((f"{method} {url}", body))
        return body


def play_until_deduction(rec: Recorder) -> str:
    """Investigate everything; return the session id. Stops before submitting."""
    session = rec.call("POST", "/sessions", expected=201, json={})
    sid = session["session_id"]
    base = f"/sessions/{sid}"

    # Questions before evidence: everyone tells their lie.
    rec.call(
        "POST",
        f"{base}/npcs/suspect-01/ask",
        json={"question": "어젯밤 그 시간에 어디 있었습니까?"},
    )
    rec.call("POST", f"{base}/npcs/suspect-02/ask", json={"question": "21시 이후 어디 있었어요?"})
    rec.call("POST", f"{base}/npcs/suspect-03/ask", json={"question": "그 시간에 뭐 했습니까?"})

    for ev in PHYSICAL:
        rec.call("POST", f"{base}/evidence/{ev}/collect")

    for pz in ("pz-01", "pz-02", "pz-03"):
        rec.call("GET", f"{base}/puzzles/{pz}/hint")
        result = rec.call(
            "POST", f"{base}/puzzles/{pz}/attempt", json={"answer": PUZZLE_ANSWERS[pz]}
        )
        assert result["correct"], pz

    rec.call("POST", f"{base}/npcs/suspect-02/present", json={"evidence_id": "ev-02"})
    rec.call(
        "POST", f"{base}/npcs/suspect-02/ask", json={"question": "그럼 그 시간에 어디 있었어요?"}
    )
    rec.call("POST", f"{base}/npcs/suspect-01/present", json={"evidence_id": "ev-01"})
    rec.call(
        "POST",
        f"{base}/npcs/suspect-01/ask",
        json={"question": "사무실에 없었다면 어디 있었습니까?"},
    )
    rec.call("POST", f"{base}/npcs/suspect-03/present", json={"evidence_id": "rec-03"})
    rec.call("POST", f"{base}/npcs/suspect-03/present", json={"evidence_id": "rec-02"})
    rec.call(
        "POST", f"{base}/npcs/suspect-03/ask", json={"question": "이 독촉장, 빚이 있었습니까?"}
    )
    turn = rec.call(
        "POST", f"{base}/npcs/suspect-03/ask", json={"question": "아까 어디 있었다고 했죠?"}
    )
    rec.call("POST", f"{base}/statements/{turn['turn_id']}/pin")

    rec.call("GET", f"{base}")
    rec.call("GET", f"{base}/board")
    rec.call("GET", f"{base}/npcs/suspect-03/dialogue")
    return sid
