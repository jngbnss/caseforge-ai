"""그래프 기반 시간선 검사 T01–T03, 유일 범인 U01–U02."""

from __future__ import annotations

from collections.abc import Iterator
from itertools import pairwise

import networkx as nx

from ..analysis import ALL_CLAIMS, Reach, established_claims, has_means, has_opportunity
from ..graph import events_of, travel_minutes
from ..report import Issue
from ..schema import CaseBible


def t01_no_double_presence(bible: CaseBible, rel: nx.MultiDiGraph) -> Iterator[Issue]:
    """한 인물이 겹치는 시간에 두 장소에 있지 않다."""
    for s in bible.suspects:
        events = events_of(rel, bible, s.suspect_id)
        for i, a in enumerate(events):
            for b in events[i + 1 :]:
                if a.location_id != b.location_id and a.time.overlaps(b.time):
                    yield Issue(
                        "T01",
                        "error",
                        f"{s.suspect_id}가 {a.time.start}–{a.time.end} {a.location_id}와 "
                        f"{b.time.start}–{b.time.end} {b.location_id}에 동시에 있다",
                        (a.event_id, b.event_id),
                    )


def t02_evidence_matches_timeline(bible: CaseBible) -> Iterator[Issue]:
    """증거가 기록한 시각과 장소가 연결된 시간선 이벤트와 일치한다."""
    events = {e.event_id: e for e in bible.timeline}
    for e in bible.evidence:
        if not e.attests or e.attests.event_id not in events:
            continue
        ev = events[e.attests.event_id]
        a = e.attests
        inside = ev.time.start_min <= a.time.start_min and a.time.end_min <= ev.time.end_min
        if not inside:
            yield Issue(
                "T02",
                "error",
                f"{e.evidence_id}의 기록 시각 {a.time.start}–{a.time.end}가 "
                f"{ev.event_id}({ev.time.start}–{ev.time.end}) 밖이다",
                (e.evidence_id, ev.event_id),
            )
        if a.location_id != ev.location_id:
            yield Issue(
                "T02",
                "error",
                f"{e.evidence_id}의 기록 장소 {a.location_id}가 {ev.event_id}의 장소 "
                f"{ev.location_id}와 다르다",
                (e.evidence_id, ev.event_id),
            )


def t03_travel_possible(bible: CaseBible, rel: nx.MultiDiGraph, locs: nx.Graph) -> Iterator[Issue]:
    """연속된 두 이벤트 사이에 장소 이동 시간이 충분하다."""
    for s in bible.suspects:
        for a, b in pairwise(events_of(rel, bible, s.suspect_id)):
            if a.time.overlaps(b.time):
                continue  # T01이 다룬다
            need = travel_minutes(locs, a.location_id, b.location_id)
            have = b.time.start_min - a.time.end_min
            if need > have:
                need_text = "도달 불가" if need == float("inf") else f"{int(need)}분 필요"
                yield Issue(
                    "T03",
                    "error",
                    f"{s.suspect_id}: {a.location_id}→{b.location_id} 이동에 {need_text}, "
                    f"{have}분뿐이다",
                    (a.event_id, b.event_id),
                )


def u01_unique_culprit(
    bible: CaseBible, rel: nx.MultiDiGraph, locs: nx.Graph, reach: Reach
) -> Iterator[Issue]:
    """기회 ∧ 수단 ∧ 증거 체인을 모두 만족하는 용의자는 범인 하나뿐이다."""
    culprit = bible.solution.culprit_id
    evidence = set(reach.collected)
    full: list[str] = []
    for s in bible.suspects:
        opp = has_opportunity(bible, rel, locs, s.suspect_id)
        means = has_means(bible, s.suspect_id)
        chain = established_claims(bible, s.suspect_id, evidence) >= ALL_CLAIMS
        if opp and means and chain:
            full.append(s.suspect_id)
        elif s.suspect_id == culprit:
            missing = [
                n for n, ok in (("기회", opp), ("수단", means), ("증거 체인", chain)) if not ok
            ]
            yield Issue(
                "U01", "error", f"범인 {culprit}에게 {', '.join(missing)}이(가) 없다", (culprit,)
            )
        elif opp and means:
            yield Issue(
                "U01",
                "warning",
                f"{s.suspect_id}도 기회와 수단이 있다 (증거로는 배제됨)",
                (s.suspect_id,),
            )
    others = [s for s in full if s != culprit]
    if others:
        yield Issue(
            "U01",
            "error",
            f"범인 외에도 완전히 입증되는 용의자가 있다: {', '.join(others)}",
            tuple(others),
        )


def u02_key_evidence_needed(bible: CaseBible, reach: Reach) -> Iterator[Issue]:
    """핵심 증거를 빼면 범인을 입증할 수 없다."""
    culprit = bible.solution.culprit_id
    key = set(bible.solution.key_evidence)
    if established_claims(bible, culprit, set(reach.collected) - key) >= ALL_CLAIMS:
        yield Issue("U02", "error", "핵심 증거 없이도 범인이 입증된다 (핵심 증거가 불필요)")
    for eid in sorted(key):
        if not established_claims(bible, culprit, {eid}):
            yield Issue(
                "U02", "warning", f"핵심 증거 {eid}가 범인에 대해 입증하는 것이 없다", (eid,)
            )
