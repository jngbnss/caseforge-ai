from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from app.core.db import make_engine, make_sessionmaker


@pytest.fixture
def db(tmp_path) -> Iterator[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    with make_sessionmaker(engine)() as session:
        yield session
    engine.dispose()
