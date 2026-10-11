"""Rule-based output guard (proposal §3.4). Runs after generation, never uses an LLM.

1. revealed_fact_ids ⊆ scope
2. canary keywords of every fact outside the scope, except keywords the NPC may legitimately
   say (they belong to an allowed fact or appear in evidence shown to this NPC)
3. meta leaks: prompt/system/fact-id vocabulary
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from case_validator import CaseBible

from app.agents.knowledge_scope import KnowledgeScope

META_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"시스템\s*프롬프트",
        r"system\s*prompt",
        r"\bfact-\d+",
        r"\blie-\d+",
        r"evidence_facts|player_question|active_lies|revealed_fact_ids",
        r"case\s*bible",
        r"culprit",
    )
]


@dataclass(frozen=True)
class GuardVerdict:
    ok: bool
    violations: list[str] = field(default_factory=list)


def check(
    answer: str, revealed_fact_ids: list[str], scope: KnowledgeScope, bible: CaseBible
) -> GuardVerdict:
    violations: list[str] = []
    allowed = scope.allowed_fact_ids

    for fid in revealed_fact_ids:
        if fid not in allowed:
            violations.append(f"out_of_scope:{fid}")

    permitted_words = {kw for f in scope.facts.values() for kw in f.canary_keywords}
    shown_text = " ".join(f"{e.name} {e.description}" for e in scope.presented_evidence)
    for fact in bible.facts:
        if fact.fact_id in allowed:
            continue
        for kw in fact.canary_keywords:
            if kw in permitted_words or kw in shown_text:
                continue
            if kw in answer:
                violations.append(f"canary:{fact.fact_id}:{kw}")

    for pattern in META_PATTERNS:
        if pattern.search(answer):
            violations.append(f"meta:{pattern.pattern}")

    return GuardVerdict(ok=not violations, violations=violations)
