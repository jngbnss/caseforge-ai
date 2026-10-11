from __future__ import annotations

from case_validator import rules, timeline
from case_validator.critic import NarrativeCritic
from case_validator.report import ValidationReport
from case_validator.schema import CaseBible


def validate(
    bible: CaseBible, *, sha256: str | None = None, critic: NarrativeCritic | None = None
) -> ValidationReport:
    """Run every deterministic rule. A critic (L01) only ever adds warnings."""
    report = ValidationReport(case_id=bible.case_id, sha256=sha256)

    rules.check_v01_references(bible, report)

    graph = timeline.build_timeline_graph(bible)
    locations = timeline.build_location_graph(bible)
    full = rules.explore(bible)

    rules.check_v02_key_evidence(bible, full, report)
    rules.check_v03_puzzle_graph(bible, full, report)
    puzzle_solutions = rules.check_v04_puzzle_uniqueness(bible, report)
    opportunity, means = rules.suspect_profile(bible, graph, locations)
    rules.check_v05_not_solvable_at_start(bible, opportunity, means, report)
    rules.check_v06_lies(bible, full, report)
    rules.check_v07_secrets(bible, full, report)

    timeline.check_t01_presence(bible, graph, report)
    timeline.check_t02_evidence(bible, graph, report)
    timeline.check_t03_travel(bible, graph, locations, report)

    suspects = rules.check_u01_unique_culprit(bible, full, opportunity, means, report)
    rules.check_u02_key_evidence_needed(bible, full, report)

    if critic is not None:
        for issue in critic.critique(bible):
            report.warn("L01", issue.message, ref=issue.ref)

    report.metrics = {
        "counts": {
            "locations": len(bible.locations),
            "suspects": len(bible.suspects),
            "facts": len(bible.facts),
            "lies": len(bible.lies),
            "secrets": len(bible.secrets),
            "evidence": len(bible.evidence),
            "puzzles": len(bible.puzzles),
            "timeline_events": len(bible.timeline),
        },
        "reachable_evidence": sorted(full.collected),
        "reachable_puzzles": sorted(full.solved),
        "puzzle_solution_counts": puzzle_solutions,
        "suspects": suspects,
        "leak_forbidden_facts": sorted(f.fact_id for f in bible.facts if f.leak_forbidden),
        "timeline_graph": {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
        },
    }
    return report
