"""사건 관계 그래프 (NetworkX).

검증용 도구이며 AI 모델이 아니다. 두 개의 그래프를 만든다.
- 관계 그래프: 인물 · 장소 · 시간선 이벤트 · 증거 노드와 그 관계
- 장소 그래프: 장소 사이 이동 시간(분)을 가중치로 하는 무방향 그래프
"""

from __future__ import annotations

import math

import networkx as nx

from .schema import CaseBible, TimelineEvent


def relation_graph(bible: CaseBible) -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()
    for loc in bible.locations:
        g.add_node(loc.location_id, kind="location", name=loc.name)
    for s in bible.suspects:
        g.add_node(s.suspect_id, kind="person", name=s.name)
    for ev in bible.timeline:
        g.add_node(ev.event_id, kind="event", start=ev.time.start_min, end=ev.time.end_min)
        g.add_edge(ev.actor_id, ev.event_id, relation="did")
        g.add_edge(ev.event_id, ev.location_id, relation="at")
    for e in bible.evidence:
        g.add_node(e.evidence_id, kind="evidence", role=e.role)
        g.add_edge(e.evidence_id, e.location_id, relation="found_at")
        if e.attests:
            g.add_edge(e.evidence_id, e.attests.event_id, relation="attests")
        for imp in e.implicates:
            g.add_edge(e.evidence_id, imp.suspect_id, relation="implicates", claim=imp.claim)
    return g


def location_graph(bible: CaseBible) -> nx.Graph:
    g = nx.Graph()
    for loc in bible.locations:
        g.add_node(loc.location_id)
        for adj in loc.adjacent:
            g.add_edge(loc.location_id, adj.to, minutes=adj.minutes)
    return g


def travel_minutes(locs: nx.Graph, a: str, b: str) -> float:
    if a == b:
        return 0
    try:
        return nx.shortest_path_length(locs, a, b, weight="minutes")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return math.inf


def events_of(rel: nx.MultiDiGraph, bible: CaseBible, actor_id: str) -> list[TimelineEvent]:
    """관계 그래프에서 인물이 한 이벤트를 시작 시각 순으로 꺼낸다."""
    by_id = {e.event_id: e for e in bible.timeline}
    if actor_id not in rel:
        return []
    ids = [v for _, v, d in rel.out_edges(actor_id, data=True) if d.get("relation") == "did"]
    return sorted((by_id[i] for i in ids), key=lambda e: (e.time.start_min, e.time.end_min))
