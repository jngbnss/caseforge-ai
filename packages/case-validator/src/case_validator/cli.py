from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from pydantic import ValidationError

from case_validator.loader import CaseLoadError, load_case
from case_validator.report import ValidationReport
from case_validator.validator import validate


def _check(case_dir: str) -> ValidationReport:
    try:
        loaded = load_case(case_dir)
    except CaseLoadError as exc:
        report = ValidationReport(case_id=case_dir)
        report.error("LOAD", str(exc))
        return report
    except ValidationError as exc:
        report = ValidationReport(case_id=case_dir)
        for err in exc.errors():
            location = ".".join(str(part) for part in err["loc"])
            report.error("SCHEMA", f"{location}: {err['msg']}")
        return report
    return validate(loaded.bible, sha256=loaded.sha256)


def _print_human(report: ValidationReport) -> None:
    status = "PASS" if report.ok else "FAIL"
    print(f"[{status}] {report.case_id}")
    if report.sha256:
        print(f"  sha256: {report.sha256}")
    for issue in report.errors:
        print(f"  ERROR   {issue.rule_id}: {issue.message}")
    for issue in report.warnings:
        print(f"  WARNING {issue.rule_id}: {issue.message}")
    if report.metrics:
        print(f"  suspects: {report.metrics.get('suspects')}")
        print(f"  puzzle solutions: {report.metrics.get('puzzle_solution_counts')}")
    print(f"  {len(report.errors)} error(s), {len(report.warnings)} warning(s)")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="case-validator")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="validate a case directory")
    check.add_argument("case_dir")
    check.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)

    report = _check(args.case_dir)
    if args.json:
        print(report.model_dump_json(indent=2))
    else:
        _print_human(report)
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
