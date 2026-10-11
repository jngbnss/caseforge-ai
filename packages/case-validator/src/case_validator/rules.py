"""Rule checks V01-V07 and the uniqueness checks U01-U02."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

import networkx as nx

from case_validator.conditions import MAX_TRUST, ConditionState, evaluate, iter_atoms
from case_validator.puzzles import PuzzleSpaceError, normalize_answer, solve
from case_validator.report import ValidationReport
from case_validator.schema import (
    CaseBible,
    Condition,
    EvidenceCollected,
    EvidencePresented,
    PuzzleSolved,
    Suspect,
    TrustGte,
)
from case_validator.timeline import events_of, travel_minutes

# ------------------------------------------------------------------------ V01 references


def check_v01_references(bible: CaseBible, report: ValidationReport) -> None:
    ids = {
        "location": [x.location_id for x in bible.locations],
        "suspect": [x.suspect_id for x in bible.suspects],
        "fact": [x.fact_id for x in bible.facts],
        "lie": [x.lie_id for x in bible.lies],
        "secret": [x.secret_id for x in bible.secrets],
        "evidence": [x.evidence_id for x in bible.evidence],
        "puzzle": [x.puzzle_id for x in bible.puzzles],
        "event": [x.event_id for x in bible.timeline],
        "motive": [x.motive_id for x in bible.briefing.motive_options],
        "method": [x.method_id for x in bible.briefing.method_options],
    }
    for kind, values in ids.items():
        for value, count in Counter(values).items():
            if count > 1:
                report.error("V01", f"duplicate {kind} id {value!r}", ref=value)
    known = {kind: set(values) for kind, values in ids.items()}
    entity_ids = known["suspect"] | known["evidence"] | known["location"]

    def need(kind: str, value: str | None, where: str) -> None:
        if value is not None and value not in known[kind]:
            report.error("V01", f"{where} references unknown {kind} {value!r}", ref=value)

    def need_condition(cond: Condition | None, where: str) -> None:
        for atom in iter_atoms(cond):
            match atom:
                case EvidenceCollected(evidence_collected=ev):
                    need("evidence", ev, where)
                case EvidencePresented(evidence_presented=ev, npc=npc):
                    need("evidence", ev, where)
                    need("suspect", npc, where)
                case PuzzleSolved(puzzle_solved=pz):
                    need("puzzle", pz, where)
                case TrustGte(npc=npc):
                    need("suspect", npc, where)

    need("location", bible.briefing.opening_location_id, "briefing")
    for loc in bible.locations:
        for adj in loc.adjacent:
            need("location", adj.to, f"location {loc.location_id}")
    for f in bible.facts:
        where = f"fact {f.fact_id}"
        need("location", f.location_id, where)
        for s in f.known_by:
            need("suspect", s, where)
        for s in f.implicates:
            need("suspect", s, where)
        for subject in f.subjects:
            if subject not in entity_ids:
                report.error("V01", f"{where} has unknown subject {subject!r}", ref=subject)
        need_condition(f.unlock_condition, where)
    for lie in bible.lies:
        where = f"lie {lie.lie_id}"
        need("suspect", lie.npc_id, where)
        need("fact", lie.contradicts_fact_id, where)
        for ev in lie.breaks_on:
            need("evidence", ev, where)
    for sec in bible.secrets:
        where = f"secret {sec.secret_id}"
        need("suspect", sec.npc_id, where)
        for fid in sec.fact_ids:
            need("fact", fid, where)
        need_condition(sec.reveal_when, where)
    for item in bible.evidence:
        where = f"evidence {item.evidence_id}"
        need("location", item.location_id, where)
        for fid in item.proves_fact_ids:
            need("fact", fid, where)
        for att in item.attests:
            need("event", att.event_id, where)
            need("location", att.location_id, where)
        need_condition(item.discoverable, where)
    for pz in bible.puzzles:
        where = f"puzzle {pz.puzzle_id}"
        need("location", pz.location_id, where)
        for ev in pz.unlocks_evidence:
            need("evidence", ev, where)
        need_condition(pz.requires, where)
    for event in bible.timeline:
        where = f"event {event.event_id}"
        need("suspect", event.actor_id, where)
        need("location", event.location_id, where)
        for fid in event.fact_ids:
            need("fact", fid, where)
    sol = bible.solution
    need("suspect", sol.culprit_id, "solution")
    need("motive", sol.motive_id, "solution")
    need("method", sol.method_id, "solution")
    need("location", sol.crime.location_id, "solution.crime")
    for fid in sol.method_steps:
        need("fact", fid, "solution.method_steps")
    for ev in (*sol.key_evidence, *sol.acceptable_evidence):
        need("evidence", ev, "solution")


# ------------------------------------------------------------------ reachability model


@dataclass(frozen=True)
class Exploration:
    collected: frozenset[str]
    solved: frozenset[str]


def optimistic_state(
    bible: CaseBible,
    collected: Iterable[str],
    solved: Iterable[str],
    *,
    interrogation: bool = True,
) -> ConditionState:
    """Best case for the player: every collected item shown to every NPC, trust maxed."""
    collected = frozenset(collected)
    npcs = [s.suspect_id for s in bible.suspects]
    return ConditionState(
        collected=collected,
        presented={npc: collected for npc in npcs} if interrogation else {},
        solved=frozenset(solved),
        trust={npc: MAX_TRUST for npc in npcs} if interrogation else {},
    )


def explore(bible: CaseBible, *, puzzles: bool = True, interrogation: bool = True) -> Exploration:
    """Fixpoint of everything a player can reach from the starting state."""
    collected: set[str] = set()
    solved: set[str] = set()
    changed = True
    while changed:
        changed = False
        state = optimistic_state(bible, collected, solved, interrogation=interrogation)
        for item in bible.evidence:
            if item.evidence_id not in collected and evaluate(item.discoverable, state):
                collected.add(item.evidence_id)
                changed = True
        if puzzles:
            for pz in bible.puzzles:
                if pz.puzzle_id in solved:
                    continue
                if pz.requires is None or evaluate(pz.requires, state):
                    solved.add(pz.puzzle_id)
                    changed = True
    return Exploration(frozenset(collected), frozenset(solved))


def proven_facts(bible: CaseBible, evidence_ids: Iterable[str]) -> set[str]:
    """Facts the player can establish: public facts plus facts proven by the evidence."""
    evidence_ids = set(evidence_ids)
    proven = {
        f.fact_id for f in bible.facts if f.available_to_player and f.unlock_condition is None
    }
    for item in bible.evidence:
        if item.evidence_id in evidence_ids:
            proven.update(item.proves_fact_ids)
    return proven


# ------------------------------------------------------------------------- V02 - V07


def check_v02_key_evidence(bible: CaseBible, full: Exploration, report: ValidationReport) -> None:
    for ev in bible.solution.key_evidence:
        if ev not in full.collected:
            report.error("V02", f"key evidence {ev} can never be discovered", ref=ev)


def puzzle_dependency_graph(bible: CaseBible) -> nx.DiGraph:
    """Edge P -> Q when puzzle Q needs puzzle P solved (directly or via P's unlocked evidence)."""
    g = nx.DiGraph()
    unlocked_by: dict[str, set[str]] = {}
    for pz in bible.puzzles:
        g.add_node(pz.puzzle_id)
        for ev in pz.unlocks_evidence:
            unlocked_by.setdefault(ev, set()).add(pz.puzzle_id)
    for item in bible.evidence:
        for atom in iter_atoms(item.discoverable):
            if isinstance(atom, PuzzleSolved):
                unlocked_by.setdefault(item.evidence_id, set()).add(atom.puzzle_solved)
    for pz in bible.puzzles:
        for atom in iter_atoms(pz.requires):
            if isinstance(atom, PuzzleSolved):
                g.add_edge(atom.puzzle_solved, pz.puzzle_id)
            elif isinstance(atom, EvidenceCollected | EvidencePresented):
                ev = (
                    atom.evidence_collected
                    if isinstance(atom, EvidenceCollected)
                    else atom.evidence_presented
                )
                for source in unlocked_by.get(ev, ()):
                    g.add_edge(source, pz.puzzle_id)
    return g


def check_v03_puzzle_graph(bible: CaseBible, full: Exploration, report: ValidationReport) -> None:
    g = puzzle_dependency_graph(bible)
    for cycle in nx.simple_cycles(g):
        report.error("V03", f"puzzle prerequisites form a cycle: {' -> '.join(cycle)}")
    for pz in bible.puzzles:
        if pz.puzzle_id not in full.solved:
            report.error("V03", f"puzzle {pz.puzzle_id} can never be reached", ref=pz.puzzle_id)


def check_v04_puzzle_uniqueness(bible: CaseBible, report: ValidationReport) -> dict[str, int]:
    counts: dict[str, int] = {}
    for pz in bible.puzzles:
        try:
            solutions = solve(pz)
        except PuzzleSpaceError as exc:
            report.error("V04", f"puzzle {pz.puzzle_id}: {exc}", ref=pz.puzzle_id)
            continue
        counts[pz.puzzle_id] = len(solutions)
        answer = normalize_answer(pz)
        if not solutions:
            report.error("V04", f"puzzle {pz.puzzle_id} has no valid answer", ref=pz.puzzle_id)
        elif len(solutions) > 1:
            shown = ", ".join(_fmt_answer(s) for s in solutions[:4])
            report.error(
                "V04",
                f"puzzle {pz.puzzle_id} has {len(solutions)}+ valid answers ({shown})",
                ref=pz.puzzle_id,
            )
        elif solutions[0] != answer:
            report.error(
                "V04",
                f"puzzle {pz.puzzle_id}: clues lead to {_fmt_answer(solutions[0])}, "
                f"stored answer is {_fmt_answer(answer)}",
                ref=pz.puzzle_id,
            )
    return counts


def _fmt_answer(answer: str | tuple[str, ...]) -> str:
    return answer if isinstance(answer, str) else "/".join(answer)


def check_v05_not_solvable_at_start(
    bible: CaseBible, opportunity: dict[str, bool], means: dict[str, bool], report: ValidationReport
) -> None:
    start = explore(bible, puzzles=False, interrogation=False)
    proven = proven_facts(bible, start.collected)
    identifiable = [
        s.suspect_id
        for s in bible.suspects
        if opportunity[s.suspect_id] and means[s.suspect_id] and has_chain(bible, s, proven)
    ]
    if bible.solution.culprit_id in identifiable:
        report.error(
            "V05",
            "the culprit can be proven without solving any puzzle or interrogating anyone "
            f"(evidence available at start: {sorted(start.collected)})",
            ref=bible.solution.culprit_id,
        )


def check_v06_lies(bible: CaseBible, full: Exploration, report: ValidationReport) -> None:
    for lie in bible.lies:
        if not lie.breaks_on:
            report.error("V06", f"lie {lie.lie_id} has no breaks_on evidence", ref=lie.lie_id)
        elif not any(ev in full.collected for ev in lie.breaks_on):
            report.error(
                "V06",
                f"lie {lie.lie_id} can never be broken: none of {list(lie.breaks_on)} "
                "is discoverable",
                ref=lie.lie_id,
            )


def check_v07_secrets(bible: CaseBible, full: Exploration, report: ValidationReport) -> None:
    state = optimistic_state(bible, full.collected, full.solved)
    for sec in bible.secrets:
        if not evaluate(sec.reveal_when, state, npc=sec.npc_id):
            report.error(
                "V07",
                f"secret {sec.secret_id} can never be revealed (trust caps at {MAX_TRUST})",
                ref=sec.secret_id,
            )


# ---------------------------------------------------------------------------- U01 / U02


def implicating_facts(bible: CaseBible, suspect_id: str) -> set[str]:
    return {
        f.fact_id
        for f in bible.facts
        if suspect_id in f.implicates and f.kind in ("truth", "record")
    }


def has_chain(bible: CaseBible, suspect: Suspect, proven: set[str]) -> bool:
    """Evidence chain: every fact implicating the suspect can be established."""
    needed = implicating_facts(bible, suspect.suspect_id)
    return bool(needed) and needed <= proven


def has_means(bible: CaseBible, suspect: Suspect) -> bool:
    return set(bible.solution.required_means) <= set(suspect.capabilities)


def has_opportunity(
    bible: CaseBible, graph: nx.MultiDiGraph, locations: nx.Graph, suspect: Suspect
) -> bool:
    """True when the suspect's true timeline lets them be at the crime scene for the window."""
    crime = bible.solution.crime
    events = events_of(graph, suspect.suspect_id)
    if any(e.location_id == crime.location_id and e.time.overlaps(crime.time) for e in events):
        return True
    # Otherwise look for an unaccounted gap long enough to get there and back.
    bounds = [(-math.inf, None)] + [(e.time.end_min, e.location_id) for e in events]
    nexts = [(e.time.start_min, e.location_id) for e in events] + [(math.inf, None)]
    for (gap_start, before_loc), (gap_end, after_loc) in zip(bounds, nexts, strict=True):
        arrive = gap_start + (
            travel_minutes(locations, before_loc, crime.location_id) if before_loc else 0
        )
        leave_by = gap_end - (
            travel_minutes(locations, crime.location_id, after_loc) if after_loc else 0
        )
        if arrive <= crime.time.start_min and crime.time.end_min <= leave_by:
            return True
    return False


def suspect_profile(
    bible: CaseBible, graph: nx.MultiDiGraph, locations: nx.Graph
) -> tuple[dict[str, bool], dict[str, bool]]:
    opportunity = {
        s.suspect_id: has_opportunity(bible, graph, locations, s) for s in bible.suspects
    }
    means = {s.suspect_id: has_means(bible, s) for s in bible.suspects}
    return opportunity, means


def check_u01_unique_culprit(
    bible: CaseBible,
    full: Exploration,
    opportunity: dict[str, bool],
    means: dict[str, bool],
    report: ValidationReport,
) -> dict[str, dict[str, bool]]:
    proven = proven_facts(bible, full.collected)
    table = {
        s.suspect_id: {
            "opportunity": opportunity[s.suspect_id],
            "means": means[s.suspect_id],
            "evidence_chain": has_chain(bible, s, proven),
        }
        for s in bible.suspects
    }
    qualified = [sid for sid, row in table.items() if all(row.values())]
    culprit = bible.solution.culprit_id
    if qualified != [culprit]:
        report.error(
            "U01",
            f"suspects satisfying opportunity, means and evidence chain: {qualified or 'none'}; "
            f"expected only {culprit}",
            ref=culprit,
        )
    return table


def check_u02_key_evidence_needed(
    bible: CaseBible, full: Exploration, report: ValidationReport
) -> None:
    culprit = next((s for s in bible.suspects if s.suspect_id == bible.solution.culprit_id), None)
    if culprit is None:
        return  # reported by V01
    key = set(bible.solution.key_evidence)
    if not has_chain(bible, culprit, proven_facts(bible, key)):
        report.error("U02", "key_evidence alone does not prove the culprit's evidence chain")
    for ev in sorted(key):
        if has_chain(bible, culprit, proven_facts(bible, full.collected - {ev})):
            report.error(
                "U02",
                f"key evidence {ev} is not necessary: the culprit is still proven without it",
                ref=ev,
            )
