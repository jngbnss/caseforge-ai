"""Nothing secret may reach a client before the deduction is submitted."""

import json

from playthrough import Recorder, play_until_deduction

# "answer" (NPC reply) and "role" (job title) are legitimate public keys, so puzzle answers and
# evidence roles are checked by value instead.
FORBIDDEN_KEYS = {
    "solution",
    "culprit_id",
    "lie_id",
    "proves_fact_ids",
    "known_by",
    "unlock_condition",
    "reveal_when",
    "key_evidence",
    "secret_id",
    "constraints",
}


def _walk(node, path=""):
    if isinstance(node, dict):
        for key, value in node.items():
            yield f"{path}.{key}", key, value
            yield from _walk(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield f"{path}[{i}]", None, value
            yield from _walk(value, f"{path}[{i}]")


def test_no_response_before_deduction_leaks_secrets(client, museum):
    bible = museum.bible
    rec = Recorder(client)
    play_until_deduction(rec)
    assert len(rec.responses) > 20

    locked_contents = [f.content for f in bible.facts if f.leak_forbidden]
    puzzle_answers = [p.answer for p in bible.puzzles]

    for label, body in rec.responses:
        text = json.dumps(body, ensure_ascii=False)
        for path, key, value in _walk(body):
            assert key not in FORBIDDEN_KEYS, f"{label}: key {key!r} at {path}"
            if isinstance(value, list) and value in [
                list(a) for a in puzzle_answers if not isinstance(a, str)
            ]:
                raise AssertionError(f"{label}: puzzle answer order at {path}")
        for content in locked_contents:
            assert content not in text, f"{label}: leak_forbidden fact content"
        for answer in puzzle_answers:
            if isinstance(answer, str):
                assert answer not in text, f"{label}: puzzle answer {answer}"
        assert "red_herring" not in text, f"{label}: evidence role"


def test_puzzle_items_are_never_served_in_answer_order(client, museum):
    answers = {p.puzzle_id: list(p.answer) for p in museum.bible.puzzles if p.input_type != "code"}
    for _ in range(20):
        session = client.post("/sessions").json()
        for puzzle in session["puzzles"]:
            if puzzle["puzzle_id"] in answers:
                order = [i["item_id"] for i in puzzle["items"]]
                assert order != answers[puzzle["puzzle_id"]]


def test_secret_fact_content_appears_only_after_reveal(client, museum):
    facts = {f.fact_id: f.content for f in museum.bible.facts}
    sid = client.post("/sessions").json()["session_id"]
    ask = client.post(
        f"/sessions/{sid}/npcs/suspect-01/ask", json={"question": "그 시간에 어디 있었어요?"}
    )
    assert "fact-006" not in ask.json()["revealed_fact_ids"]
    assert facts["fact-006"] not in ask.text
