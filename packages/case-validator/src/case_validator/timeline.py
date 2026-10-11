"""NetworkX timeline graph (person, location, time, evidence nodes) and T01-T03 checks."""

from __future__ import annotations

import math
from itertools import pairwise

import networkx as nx

from case_validator.report import ValidationReport
from case_validator.schema import CaseBible, TimelineEvent, TimeRange


def build_timeline_graph(bible: CaseBible) -> nx.MultiDiGraph:
    """Nodes: person:*, location:*, time:HH:MM, event:*, evidence:*.

    Edges: person -did-> event, event -at-> location, event -starts-> time,
    evidence -attests-> event, evidence -found_in-> location.
    """
    g = nx.MultiDiGraph()
    for loc in bible.locations:
        g.add_node(f"location:{loc.location_id}", kind="location")
    for s in bible.suspects:
        g.add_node(f"person:{s.suspect_id}", kind="person")
    for ev in bible.timeline:
        node = f"event:{ev.event_id}"
        g.add_node(node, kind="event", event=ev)
        g.add_node(f"time:{ev.time.start}", kind="time", minute=ev.time.start_min)
        g.add_edge(node, f"time:{ev.time.start}", rel="starts")
        g.add_edge(node, f"location:{ev.location_id}", rel="at")
        if ev.actor_id:
            g.add_edge(f"person:{ev.actor_id}", node, rel="did")
    for item in bible.evidence:
        node = f"evidence:{item.evidence_id}"
        g.add_node(node, kind="evidence")
        g.add_edge(node, f"location:{item.location_id}", rel="found_in")
        for att in item.attests:
            g.add_edge(node, f"event:{att.event_id}", rel="attests", attestation=att)
    return g


def build_location_graph(bible: CaseBible) -> nx.Graph:
    g = nx.Graph()
    for loc in bible.locations:
        g.add_node(loc.location_id)
    for loc in bible.locations:
        for adj in loc.adjacent:
            g.add_edge(loc.location_id, adj.to, minutes=adj.minutes)
    return g


def travel_minutes(locations: nx.Graph, src: str, dst: str) -> float:
    if src == dst:
        return 0
    try:
        return nx.shortest_path_length(locations, src, dst, weight="minutes")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return math.inf


def events_of(graph: nx.MultiDiGraph, person_id: str) -> list[TimelineEvent]:
    node = f"person:{person_id}"
    if node not in graph:
        return []
    events = [
        graph.nodes[target]["event"]
        for _, target, data in graph.out_edges(node, data=True)
        if data["rel"] == "did"
    ]
    return sorted(events, key=lambda e: (e.time.start_min, e.time.end_min, e.event_id))


def check_t01_presence(bible: CaseBible, graph: nx.MultiDiGraph, report: ValidationReport) -> None:
    for suspect in bible.suspects:
        events = events_of(graph, suspect.suspect_id)
        for i, a in enumerate(events):
            for b in events[i + 1 :]:
                if a.location_id != b.location_id and a.time.overlaps(b.time):
                    report.error(
                        "T01",
                        f"{suspect.suspect_id} is in {a.location_id} ({a.event_id}) and "
                        f"{b.location_id} ({b.event_id}) at the same time",
                        ref=suspect.suspect_id,
                    )


def check_t02_evidence(bible: CaseBible, graph: nx.MultiDiGraph, report: ValidationReport) -> None:
    for item in bible.evidence:
        for att in item.attests:
            node = f"event:{att.event_id}"
            if node not in graph:
                continue  # dangling reference is reported by V01
            event: TimelineEvent = graph.nodes[node]["event"]
            if att.location_id != event.location_id:
                report.error(
                    "T02",
                    f"{item.evidence_id} places {att.event_id} in {att.location_id}, "
                    f"timeline says {event.location_id}",
                    ref=item.evidence_id,
                )
            if att.time is not None and not att.time.touches(event.time):
                report.error(
                    "T02",
                    f"{item.evidence_id} dates {att.event_id} at {_fmt(att.time)}, "
                    f"timeline says {_fmt(event.time)}",
                    ref=item.evidence_id,
                )


def check_t03_travel(
    bible: CaseBible, graph: nx.MultiDiGraph, locations: nx.Graph, report: ValidationReport
) -> None:
    for suspect in bible.suspects:
        for a, b in pairwise(events_of(graph, suspect.suspect_id)):
            if a.location_id == b.location_id or a.time.overlaps(b.time):
                continue  # overlaps are T01's business
            needed = travel_minutes(locations, a.location_id, b.location_id)
            available = b.time.start_min - a.time.end_min
            if needed > available:
                report.error(
                    "T03",
                    f"{suspect.suspect_id} cannot get from {a.location_id} ({a.event_id}, "
                    f"ends {a.time.end}) to {b.location_id} ({b.event_id}, starts {b.time.start}): "
                    f"needs {needed} min, has {available}",
                    ref=suspect.suspect_id,
                )


def _fmt(t: TimeRange) -> str:
    return t.start if t.is_instant else f"{t.start}-{t.end}"
