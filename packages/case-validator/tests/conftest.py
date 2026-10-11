import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from materialize import MUSEUM_001  # noqa: E402

from case_validator import LoadedCase, load_case  # noqa: E402


@pytest.fixture(scope="session")
def museum() -> LoadedCase:
    return load_case(MUSEUM_001)
