from functools import lru_cache

from app.core.config import settings
from case_validator import LoadedCase, load_case


@lru_cache
def get_case(case_id: str) -> LoadedCase:
    """사건을 한 번 읽어 캐시한다. CaseBible은 frozen이라 공유해도 안전하다."""
    return load_case(settings.cases_dir / case_id)
