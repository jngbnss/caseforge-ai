"""사건 디렉터리(YAML 여러 개)를 하나의 CaseBible로 읽는다."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .schema import CaseBible

CASE_FILES = (
    "case.yaml",
    "timeline.yaml",
    "suspects.yaml",
    "evidence.yaml",
    "puzzles.yaml",
    "solution.yaml",
)


class CaseLoadError(Exception):
    pass


@dataclass(frozen=True)
class LoadedCase:
    bible: CaseBible
    sha256: str


def bible_hash(bible: CaseBible) -> str:
    """서식과 무관한 정규화 JSON의 SHA-256."""
    canonical = json.dumps(bible.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def read_case_dict(case_dir: Path) -> dict[str, Any]:
    case_dir = Path(case_dir)
    merged: dict[str, Any] = {}
    for name in CASE_FILES:
        path = case_dir / name
        if not path.exists():
            raise CaseLoadError(f"필수 파일이 없다: {path}")
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise CaseLoadError(f"YAML 문법 오류: {path}\n{exc}") from exc
        if not isinstance(data, dict):
            raise CaseLoadError(f"최상위가 매핑이어야 한다: {path}")
        overlap = merged.keys() & data.keys()
        if overlap:
            raise CaseLoadError(f"{name}의 키가 다른 파일과 겹친다: {sorted(overlap)}")
        merged.update(data)

    dialogues = []
    dialogue_dir = case_dir / "dialogues"
    if dialogue_dir.is_dir():
        for path in sorted(dialogue_dir.glob("*.yaml")):
            dialogues.append(yaml.safe_load(path.read_text(encoding="utf-8")))
    merged["dialogues"] = dialogues
    return merged


def load_case(case_dir: Path | str) -> LoadedCase:
    """사건을 읽고 스키마 검증 후 해시와 함께 반환한다. 실패하면 ValidationError."""
    bible = CaseBible.model_validate(read_case_dict(Path(case_dir)))
    return LoadedCase(bible=bible, sha256=bible_hash(bible))
