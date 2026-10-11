from case_validator import load_case, validate

from app.core.config import get_settings


def test_backend_can_load_and_validate_default_case():
    settings = get_settings()
    loaded = load_case(settings.cases_dir / settings.default_case_id)
    assert validate(loaded.bible).ok
