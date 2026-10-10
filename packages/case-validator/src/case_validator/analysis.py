"""여러 규칙이 함께 쓰는 분석: 도달 가능성, 기회, 수단, 증거 체인."""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from .conditions import satisfiable
from .graph import events_of, travel_minutes
from .schema import CaseBible, Claim

ALL_CLAIMS: frozenset[Claim] = frozenset({"opportunity", "means", "motive"})


@dataclass(frozen=True)
class Reach:
    collected: frozenset[str]
    solved: frozenset[str]


def reachable(bible: CaseBible, *, allow_puzzles: bool = True) -> Reach:
    """시작 상태에서 플레이어가 얻을 수 있는 증거와 풀 수 있는 퍼즐 (고정점 계산)."""
    unlocked_by_puzzle = {eid for p in bible.puzzles for eid in p.unlocks_evidence}
    collected: set[str] = set()
    solved: set[str] = set()
    changed = True
    while changed:
        changed = False
        for e in bible.evidence:
            if e.evidence_id in collected:
                continue
            if e.source == "puzzle" or e.evidence_id in unlocked_by_puzzle:
                via_puzzle = any(
                    e.evidence_id in p.unlocks_evidence
                    for p in bible.puzzles
                    if p.puzzle_id in solved
                )
                if not via_puzzle:
                    continue
            if satisfiable(e.discoverable, collected, solved):
                collected.add(e.evidence_id)
                changed = True
        if not allow_puzzles:
            continue
        for p in bible.puzzles:
            if p.puzzle_id not in solved and satisfiable(p.requires, collected, solved):
                solved.add(p.puzzle_id)
                changed = True
    return Reach(frozenset(collected), frozenset(solved))


def established_claims(bible: CaseBible, suspect_id: str, evidence_ids: set[str]) -> set[Claim]:
    """주어진 증거들이 해당 용의자에 대해 입증하는 주장 (기회/수단/동기)."""
    claims: set[Claim] = set()
    for e in bible.evidence:
        if e.evidence_id in evidence_ids:
            claims |= {i.claim for i in e.implicates if i.suspect_id == suspect_id}
    return claims


def has_means(bible: CaseBible, suspect_id: str) -> bool:
    s = bible.suspect(suspect_id)
    return s is not None and set(bible.solution.required_means) <= set(s.capabilities)


def has_opportunity(
    bible: CaseBible, rel: nx.MultiDiGraph, locs: nx.Graph, suspect_id: str
) -> bool:
    """범행 시간 중 어느 한 분이라도 범행 장소에 있을 수 있었는가.

    해당 분에 다른 장소 이벤트 중이 아니고, 직전 이벤트 장소에서 오고 다음 이벤트 장소로 갈 수 있어야 한다.
    시간선에 기록이 없는 인물은 기회가 있다고 본다.
    """
    crime = bible.solution.crime
    events = events_of(rel, bible, suspect_id)
    for t in range(crime.time.start_min, crime.time.end_min + 1):
        busy = [e for e in events if e.time.start_min <= t < e.time.end_min]
        if any(e.location_id == crime.location_id for e in busy):
            return True
        if busy:
            continue
        prev = [e for e in events if e.time.end_min <= t]
        nxt = [e for e in events if e.time.start_min >= t]
        ok_prev = (
            not prev
            or prev[-1].time.end_min + travel_minutes(locs, prev[-1].location_id, crime.location_id)
            <= t
        )
        ok_next = not nxt or t + travel_minutes(locs, crime.location_id, nxt[0].location_id) <= (
            nxt[0].time.start_min
        )
        if ok_prev and ok_next:
            return True
    return False
