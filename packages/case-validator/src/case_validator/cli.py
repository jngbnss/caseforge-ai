from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from .loader import CaseLoadError, load_case
from .validator import validate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="case-validator")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="사건 디렉터리를 검증한다")
    check.add_argument("case_dir", type=Path)
    check.add_argument("--json", action="store_true", help="JSON으로 출력")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    try:
        loaded = load_case(args.case_dir)
    except (CaseLoadError, ValidationError) as exc:
        print(f"SCHEMA 스키마 검증 실패: {exc}", file=sys.stderr)
        return 1

    report = validate(loaded.bible)
    if args.json:
        data = report.to_dict() | {"sha256": loaded.sha256}
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"{report.case_id}  sha256={loaded.sha256[:12]}")
        for issue in report.errors:
            print(f"  ERROR   {issue}")
        for issue in report.warnings:
            print(f"  WARNING {issue}")
        metrics = ", ".join(f"{k}={v}" for k, v in report.metrics.items())
        print(f"  {len(report.errors)} errors, {len(report.warnings)} warnings  ({metrics})")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
