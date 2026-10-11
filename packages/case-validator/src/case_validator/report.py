from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Issue(BaseModel):
    rule_id: str
    message: str
    ref: str | None = None  # id of the offending entity, when there is one


class ValidationReport(BaseModel):
    case_id: str
    sha256: str | None = None
    errors: list[Issue] = Field(default_factory=list)
    warnings: list[Issue] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def failed_rules(self) -> set[str]:
        return {issue.rule_id for issue in self.errors}

    def error(self, rule_id: str, message: str, ref: str | None = None) -> None:
        self.errors.append(Issue(rule_id=rule_id, message=message, ref=ref))

    def warn(self, rule_id: str, message: str, ref: str | None = None) -> None:
        self.warnings.append(Issue(rule_id=rule_id, message=message, ref=ref))
