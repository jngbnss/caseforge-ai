from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class Issue:
    rule_id: str
    severity: Literal["error", "warning"]
    message: str
    refs: tuple[str, ...] = ()

    def __str__(self) -> str:
        refs = f" [{', '.join(self.refs)}]" if self.refs else ""
        return f"{self.rule_id} {self.message}{refs}"


@dataclass
class ValidationReport:
    case_id: str
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)
    metrics: dict[str, int | float] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add(self, issue: Issue) -> None:
        (self.errors if issue.severity == "error" else self.warnings).append(issue)

    def rule_ids(self) -> set[str]:
        return {i.rule_id for i in self.errors + self.warnings}

    def to_dict(self) -> dict:
        def dump(issues: list[Issue]) -> list[dict]:
            return [
                {"rule_id": i.rule_id, "message": i.message, "refs": list(i.refs)} for i in issues
            ]

        return {
            "case_id": self.case_id,
            "ok": self.ok,
            "errors": dump(self.errors),
            "warnings": dump(self.warnings),
            "metrics": self.metrics,
        }
