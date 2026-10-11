"""평가 데이터와 러너. 저장소 루트에서 `uv run python -m evals.<모듈>`로 실행한다."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))  # backend의 app 패키지를 쓴다

DATA_DIR = Path(__file__).resolve().parent / "data"
RESULTS_DIR = Path(__file__).resolve().parent / "results"
