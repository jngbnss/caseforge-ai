"""Load a case directory (several YAML files) into a frozen CaseBible plus its SHA-256 hash."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, NamedTuple

import yaml

from case_validator.schema import CaseBible

CASE_FILES = (
    "case.yaml",
    "timeline.yaml",
    "suspects.yaml",
    "evidence.yaml",
    "puzzles.yaml",
    "solution.yaml",
)


class CaseLoadError(Exception):
    """Raised when a case directory is missing files or contains malformed YAML."""


class LoadedCase(NamedTuple):
    bible: CaseBible
    sha256: str


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise CaseLoadError(f"{path.name}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise CaseLoadError(f"{path.name}: top level must be a mapping")
    return data


def read_case_dir(case_dir: str | Path) -> dict[str, Any]:
    """Merge the YAML files of a case directory into one raw dict (not yet validated)."""
    root = Path(case_dir)
    if not root.is_dir():
        raise CaseLoadError(f"case directory not found: {root}")

    merged: dict[str, Any] = {}
    for name in CASE_FILES:
        path = root / name
        if not path.is_file():
            raise CaseLoadError(f"missing case file: {name}")
        for key, value in _read_yaml(path).items():
            if key in merged:
                raise CaseLoadError(f"{name}: key {key!r} is defined in more than one file")
            merged[key] = value

    dialogues: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "dialogues").glob("*.yaml")):
        data = _read_yaml(path)
        suspect_id = data.pop("suspect_id", None)
        if not suspect_id:
            raise CaseLoadError(f"dialogues/{path.name}: suspect_id is required")
        dialogues[suspect_id] = data

    for suspect in merged.get("suspects") or []:
        sid = suspect.get("suspect_id")
        if "dialogue" not in suspect:
            if sid not in dialogues:
                raise CaseLoadError(f"no dialogues/*.yaml for suspect {sid!r}")
            suspect["dialogue"] = dialogues.pop(sid)
    if dialogues:
        raise CaseLoadError(f"dialogue files for unknown suspects: {sorted(dialogues)}")
    return merged


def bible_sha256(bible: CaseBible) -> str:
    """Hash of the canonical JSON form, independent of YAML formatting and file layout."""
    canonical = json.dumps(
        bible.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_case(case_dir: str | Path) -> LoadedCase:
    """Load and schema-validate a case. Raises CaseLoadError or pydantic.ValidationError."""
    bible = CaseBible.model_validate(read_case_dir(case_dir))
    return LoadedCase(bible=bible, sha256=bible_sha256(bible))
