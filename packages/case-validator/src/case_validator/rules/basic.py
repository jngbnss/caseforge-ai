"""규칙 기반 검사 V01–V07."""

from __future__ import annotations

from collections.abc import Iterator
from itertools import permutations, product

import networkx as nx

from ..analysis import ALL_CLAIMS, Reach, established_claims, reachable
from ..conditions import referenced_ids, satisfiable
from ..report import Issue
from ..schema import CaseBible, Puzzle

MAX_PERMUTATION_ITEMS = 8
MAX_CODE_LENGTH = 6


def v01_references(bible: CaseBible) -> Iterator[Issue]:
    """모든 참조 ID가 존재한다."""
    ids = {
        "location": {x.location_id for x in bible.locations},
        "suspect": {x.suspect_id for x in bible.suspects},
        "fact": {x.fact_id for x in bible.facts},
        "evidence": {x.evidence_id for x in bible.evidence},
        "puzzle": {x.puzzle_id for x in bible.puzzles},
        "event": {x.event_id for x in bible.timeline},
    }
    any_id = set().union(*ids.values())

    def check(kind: str, ref: str | None, owner: str) -> Iterator[Issue]:
        if ref is not None and ref not in ids[kind]:
            yield Issue(
                "V01", "error", f"{owner}이(가) 없는 {kind} '{ref}'를 참조한다", (owner, ref)
            )

    def check_cond(cond, owner: str) -> Iterator[Issue]:
        for kind, ref in referenced_ids(cond):
            yield from check(kind, ref, owner)

    for loc in bible.locations:
        for adj in loc.adjacent:
            yield from check("location", adj.to, loc.location_id)
    for fid in bible.briefing.public_fact_ids:
        yield from check("fact", fid, "briefing")
    for f in bible.facts:
        for s in f.known_by:
            yield from check("suspect", s, f.fact_id)
        yield from check("location", f.location_id, f.fact_id)
        yield from check_cond(f.unlock_condition, f.fact_id)
        for subj in f.subjects:
            if subj not in any_id:
                yield Issue("V01", "error", f"{f.fact_id}의 subject '{subj}'가 없다", (f.fact_id,))
    for lie in bible.lies:
        yield from check("suspect", lie.npc_id, lie.lie_id)
        yield from check("fact", lie.contradicts_fact_id, lie.lie_id)
        for eid in lie.breaks_on:
            yield from check("evidence", eid, lie.lie_id)
    for sec in bible.secrets:
        yield from check("suspect", sec.npc_id, sec.secret_id)
        for fid in sec.fact_ids:
            yield from check("fact", fid, sec.secret_id)
        yield from check_cond(sec.reveal_when, sec.secret_id)
    for e in bible.evidence:
        yield from check("location", e.location_id, e.evidence_id)
        yield from check_cond(e.discoverable, e.evidence_id)
        for fid in e.proves_fact_ids:
            yield from check("fact", fid, e.evidence_id)
        if e.attests:
            yield from check("event", e.attests.event_id, e.evidence_id)
            yield from check("location", e.attests.location_id, e.evidence_id)
        for imp in e.implicates:
            yield from check("suspect", imp.suspect_id, e.evidence_id)
    for p in bible.puzzles:
        yield from check_cond(p.requires, p.puzzle_id)
        for eid in p.unlocks_evidence:
            yield from check("evidence", eid, p.puzzle_id)
    for ev in bible.timeline:
        yield from check("suspect", ev.actor_id, ev.event_id)
        yield from check("location", ev.location_id, ev.event_id)
        for fid in ev.fact_ids:
            yield from check("fact", fid, ev.event_id)
    sol = bible.solution
    yield from check("suspect", sol.culprit_id, "solution")
    yield from check("location", sol.crime.location_id, "solution")
    for fid in sol.method_steps:
        yield from check("fact", fid, "solution")
    for eid in sol.key_evidence + sol.acceptable_evidence:
        yield from check("evidence", eid, "solution")
    if sol.motive_id not in {o.id for o in bible.deduction_options.motives}:
        yield Issue("V01", "error", f"정답 동기 '{sol.motive_id}'가 선택지에 없다", ("solution",))
    if sol.method_id not in {o.id for o in bible.deduction_options.methods}:
        yield Issue("V01", "error", f"정답 수법 '{sol.method_id}'가 선택지에 없다", ("solution",))
    for d in bible.dialogues:
        yield from check("suspect", d.suspect_id, f"dialogue:{d.suspect_id}")
    missing = ids["suspect"] - {d.suspect_id for d in bible.dialogues}
    for s in sorted(missing):
        yield Issue("V01", "warning", f"{s}의 대사 파일이 없다", (s,))


def v02_key_evidence_reachable(bible: CaseBible, reach: Reach) -> Iterator[Issue]:
    """정답의 핵심 증거는 모두 발견 가능하다."""
    for eid in bible.solution.key_evidence:
        if eid not in reach.collected:
            yield Issue("V02", "error", f"핵심 증거 {eid}에 도달할 수 없다", (eid,))
    for e in bible.evidence:
        if (
            e.evidence_id not in reach.collected
            and e.evidence_id not in bible.solution.key_evidence
        ):
            yield Issue(
                "V02", "warning", f"증거 {e.evidence_id}에 도달할 수 없다", (e.evidence_id,)
            )


def v03_puzzle_graph(bible: CaseBible, reach: Reach) -> Iterator[Issue]:
    """퍼즐 선행조건에 순환이 없고 모든 퍼즐에 도달할 수 있다."""
    unlocker = {eid: p.puzzle_id for p in bible.puzzles for eid in p.unlocks_evidence}
    g = nx.DiGraph()
    for p in bible.puzzles:
        g.add_node(p.puzzle_id)
        for kind, ref in referenced_ids(p.requires):
            if kind == "puzzle":
                g.add_edge(ref, p.puzzle_id)
            elif kind == "evidence" and ref in unlocker:
                g.add_edge(unlocker[ref], p.puzzle_id)
    for cycle in nx.simple_cycles(g):
        yield Issue("V03", "error", f"퍼즐 선행조건이 순환한다: {' → '.join(cycle)}", tuple(cycle))
    for p in bible.puzzles:
        if p.puzzle_id not in reach.solved:
            yield Issue("V03", "error", f"퍼즐 {p.puzzle_id}에 도달할 수 없다", (p.puzzle_id,))


def _order_solutions(p: Puzzle) -> list[tuple[str, ...]] | None:
    items = [o.id for o in p.options]
    if len(items) > MAX_PERMUTATION_ITEMS:
        return None
    found = []
    for perm in permutations(items):
        pos = {x: i for i, x in enumerate(perm)}
        ok = True
        for c in p.order_clues:
            if c.before is not None and c.after is not None:
                ok = pos.get(c.before, -1) < pos.get(c.after, -1)
            elif c.first is not None:
                ok = perm[0] == c.first
            elif c.last is not None:
                ok = perm[-1] == c.last
            if not ok:
                break
        if ok:
            found.append(perm)
    return found


def _code_solutions(p: Puzzle) -> list[str] | None:
    assert p.code_length is not None
    if p.code_length > MAX_CODE_LENGTH:
        return None
    found = []
    for digits in product("0123456789", repeat=p.code_length):
        code = "".join(digits)
        if all(code[c.start : c.end] in c.one_of for c in p.code_clues):
            found.append(code)
    return found


def v04_puzzle_unique(bible: CaseBible) -> Iterator[Issue]:
    """퍼즐 단서를 만족하는 답이 정확히 하나이며 정답과 같다."""
    for p in bible.puzzles:
        if p.input_type == "code":
            sols: list | None = _code_solutions(p)
            answer: object = p.answer
        else:
            option_ids = {o.id for o in p.options}
            if sorted(p.answer) != sorted(option_ids):
                yield Issue(
                    "V04", "error", f"{p.puzzle_id}의 정답이 선택지의 순열이 아니다", (p.puzzle_id,)
                )
                continue
            sols = _order_solutions(p)
            answer = tuple(p.answer)
        if sols is None:
            yield Issue("V04", "warning", f"{p.puzzle_id}는 탐색 공간이 커서 생략", (p.puzzle_id,))
        elif not sols:
            yield Issue(
                "V04", "error", f"{p.puzzle_id}의 단서를 만족하는 답이 없다", (p.puzzle_id,)
            )
        elif len(sols) > 1:
            yield Issue(
                "V04",
                "error",
                f"{p.puzzle_id}의 정답이 {len(sols)}개다 (유일하지 않음)",
                (p.puzzle_id,),
            )
        elif sols[0] != answer:
            yield Issue(
                "V04",
                "error",
                f"{p.puzzle_id}의 단서가 가리키는 답이 정답과 다르다",
                (p.puzzle_id,),
            )


def v05_not_solvable_upfront(bible: CaseBible) -> Iterator[Issue]:
    """퍼즐 없이 얻는 정보만으로 범인을 완전히 입증할 수 없다."""
    culprit = bible.solution.culprit_id
    early = reachable(bible, allow_puzzles=False)
    if established_claims(bible, culprit, set(early.collected)) >= ALL_CLAIMS:
        yield Issue("V05", "error", "퍼즐을 풀지 않고도 범인의 기회·수단·동기가 모두 입증된다")
    secret_facts = {f.fact_id for f in bible.facts if f.forbidden} | set(
        bible.solution.method_steps
    )
    for fid in bible.briefing.public_fact_ids:
        if fid in secret_facts:
            yield Issue("V05", "error", f"브리핑에 정답 사실 {fid}가 공개된다", (fid,))


def v06_lies_breakable(bible: CaseBible, reach: Reach) -> Iterator[Issue]:
    """모든 거짓말은 발견 가능한 증거로 무너뜨릴 수 있다."""
    for lie in bible.lies:
        if not lie.breaks_on:
            yield Issue("V06", "error", f"{lie.lie_id}를 무너뜨릴 증거가 없다", (lie.lie_id,))
        elif not any(eid in reach.collected for eid in lie.breaks_on):
            yield Issue("V06", "error", f"{lie.lie_id}의 반박 증거에 도달할 수 없다", (lie.lie_id,))


def v07_secrets_revealable(bible: CaseBible, reach: Reach) -> Iterator[Issue]:
    """모든 비밀의 공개 조건은 충족될 수 있다."""
    for sec in bible.secrets:
        if not satisfiable(sec.reveal_when, set(reach.collected), set(reach.solved)):
            yield Issue(
                "V07", "error", f"{sec.secret_id}의 공개 조건을 충족할 수 없다", (sec.secret_id,)
            )
