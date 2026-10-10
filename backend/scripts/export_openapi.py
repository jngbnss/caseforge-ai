"""백엔드 OpenAPI 스키마를 frontend/openapi.json으로 내보낸다. 프론트 TS 타입 생성의 입력이다."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.main import create_app

OUT = Path(__file__).resolve().parents[2] / "frontend" / "openapi.json"


def main() -> int:
    schema = create_app("sqlite://").openapi()
    text = json.dumps(schema, ensure_ascii=False, indent=2) + "\n"
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
