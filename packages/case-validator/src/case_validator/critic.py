"""L01: LLM critique of motive/narrative plausibility and hint fairness.

Interface only. A critic may add warnings but never decides pass/fail.
TODO(P5+): implement on top of the backend's LLMPort.
"""

from __future__ import annotations

from typing import Protocol

from case_validator.report import Issue
from case_validator.schema import CaseBible


class NarrativeCritic(Protocol):
    def critique(self, bible: CaseBible) -> list[Issue]:
        """Return L01 warnings. Must not raise on a valid case."""
        ...
