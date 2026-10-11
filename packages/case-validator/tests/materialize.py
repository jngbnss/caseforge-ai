"""Build a broken case directory from museum-001 plus a fixture's patch.yaml.

Usage: python tests/materialize.py broken-t01 OUT_DIR
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
MUSEUM_001 = REPO_ROOT / "cases" / "museum-001"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _step(node: Any, segment: str) -> tuple[Any, Any]:
    """Return (container, key) for one path segment."""
    if isinstance(node, dict):
        return node, segment
    if isinstance(node, list):
        if segment.isdigit():
            return node, int(segment)
        for i, item in enumerate(node):
            if isinstance(item, dict) and any(
                k.endswith("_id") and v == segment for k, v in item.items()
            ):
                return node, i
    raise KeyError(f"path segment {segment!r} not found")


def apply_patch(data: dict[str, Any], path: str, value: Any) -> None:
    segments = path.split("/")
    node: Any = data
    for segment in segments[:-1]:
        container, key = _step(node, segment)
        node = container[key]
    container, key = _step(node, segments[-1])
    container[key] = value


def load_patch(name: str) -> dict[str, Any]:
    return yaml.safe_load((FIXTURES / name / "patch.yaml").read_text(encoding="utf-8"))


def materialize(name: str, out_dir: Path) -> Path:
    target = Path(out_dir) / name
    shutil.copytree(MUSEUM_001, target)
    for patch in load_patch(name)["patches"]:
        file = target / patch["file"]
        data = yaml.safe_load(file.read_text(encoding="utf-8"))
        apply_patch(data, patch["path"], patch["value"])
        file.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), "utf-8")
    return target


def fixture_names() -> list[str]:
    return sorted(p.name for p in FIXTURES.glob("broken-*") if p.is_dir())


if __name__ == "__main__":
    print(materialize(sys.argv[1], Path(sys.argv[2])))
