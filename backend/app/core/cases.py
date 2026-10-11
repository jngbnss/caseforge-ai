"""Case registry: load, validate and cache Case Bibles by id."""

import re
from functools import lru_cache

from case_validator import LoadedCase, load_case, validate

from app.core.config import get_settings

_CASE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class CaseNotFoundError(LookupError):
    pass


class InvalidCaseError(RuntimeError):
    pass


@lru_cache(maxsize=16)
def get_case(case_id: str) -> LoadedCase:
    """Return a validated, frozen Case Bible. Invalid cases are never served."""
    if not _CASE_ID.match(case_id):
        raise CaseNotFoundError(case_id)
    path = get_settings().cases_dir / case_id
    if not path.is_dir():
        raise CaseNotFoundError(case_id)
    loaded = load_case(path)
    report = validate(loaded.bible, sha256=loaded.sha256)
    if not report.ok:
        rules = ", ".join(sorted(report.failed_rules()))
        raise InvalidCaseError(f"case {case_id} fails validation: {rules}")
    return loaded
