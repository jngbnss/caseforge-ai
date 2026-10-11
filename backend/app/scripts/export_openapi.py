"""Write the OpenAPI schema to a file: python -m app.scripts.export_openapi OUT.json"""

import json
import sys
from pathlib import Path

from app.core.config import Settings
from app.main import create_app


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
    app = create_app(Settings(_env_file=None, database_url="sqlite://"))
    out.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
