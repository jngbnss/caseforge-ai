from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from case_validator.loader import read_case_dict

MUSEUM_DIR = Path(__file__).resolve().parents[3] / "cases" / "museum-001"
_BASE = read_case_dict(MUSEUM_DIR)


@pytest.fixture
def museum() -> dict[str, Any]:
    """museum-001 원본 dict의 깊은 복사본. 테스트에서 마음대로 망가뜨린다."""
    return copy.deepcopy(_BASE)


def find(items: list[dict], key: str, value: str) -> dict:
    return next(x for x in items if x[key] == value)
