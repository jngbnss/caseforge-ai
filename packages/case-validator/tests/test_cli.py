from __future__ import annotations

import json
import shutil

from case_validator.cli import main
from conftest import MUSEUM_DIR


def test_cli_ok(capsys) -> None:
    assert main(["check", str(MUSEUM_DIR)]) == 0
    assert "0 errors" in capsys.readouterr().out


def test_cli_json(capsys) -> None:
    assert main(["check", str(MUSEUM_DIR), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is True
    assert len(data["sha256"]) == 64


def test_cli_fails_on_broken_case(tmp_path, capsys) -> None:
    case = tmp_path / "broken"
    shutil.copytree(MUSEUM_DIR, case)
    solution = case / "solution.yaml"
    solution.write_text(
        solution.read_text(encoding="utf-8").replace(
            "culprit_id: suspect-03", "culprit_id: suspect-01"
        ),
        encoding="utf-8",
    )
    assert main(["check", str(case)]) == 1
    assert "U01" in capsys.readouterr().out


def test_cli_fails_on_schema_error(tmp_path, capsys) -> None:
    case = tmp_path / "bad-yaml"
    shutil.copytree(MUSEUM_DIR, case)
    (case / "solution.yaml").write_text("solution: [unclosed", encoding="utf-8")
    assert main(["check", str(case)]) == 1
    assert "SCHEMA" in capsys.readouterr().err
