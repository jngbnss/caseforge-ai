from __future__ import annotations

from .analysis import reachable
from .critique import CaseCritic, as_warnings
from .graph import location_graph, relation_graph
from .report import Issue, ValidationReport
from .rules import basic, timeline
from .schema import CaseBible


def validate(bible: CaseBible, critic: CaseCritic | None = None) -> ValidationReport:
    report = ValidationReport(case_id=bible.case_id)
    for issue in basic.v01_references(bible):
        report.add(issue)
    if report.errors:
        report.add(Issue("V01", "warning", "참조 오류가 있어 이후 검사를 생략했다"))
        return report

    reach = reachable(bible)
    rel = relation_graph(bible)
    locs = location_graph(bible)
    checks = [
        basic.v02_key_evidence_reachable(bible, reach),
        basic.v03_puzzle_graph(bible, reach),
        basic.v04_puzzle_unique(bible),
        basic.v05_not_solvable_upfront(bible),
        basic.v06_lies_breakable(bible, reach),
        basic.v07_secrets_revealable(bible, reach),
        timeline.t01_no_double_presence(bible, rel),
        timeline.t02_evidence_matches_timeline(bible),
        timeline.t03_travel_possible(bible, rel, locs),
        timeline.u01_unique_culprit(bible, rel, locs, reach),
        timeline.u02_key_evidence_needed(bible, reach),
    ]
    for check in checks:
        for issue in check:
            report.add(issue)
    if critic is not None:
        for issue in as_warnings(critic.critique(bible)):
            report.add(issue)

    report.metrics = {
        "suspects": len(bible.suspects),
        "evidence": len(bible.evidence),
        "puzzles": len(bible.puzzles),
        "timeline_events": len(bible.timeline),
        "reachable_evidence": len(reach.collected),
        "solvable_puzzles": len(reach.solved),
        "graph_nodes": rel.number_of_nodes(),
        "graph_edges": rel.number_of_edges(),
    }
    return report
