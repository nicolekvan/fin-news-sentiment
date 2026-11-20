import os

import pytest
from sqlalchemy import create_engine, text

from marketlens.db import migrate


@pytest.fixture(scope="session")
def engine():
    """Fresh, fully migrated database. Requires TEST_DATABASE_URL (a disposable database)."""
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set")
    eng = create_engine(url)
    with eng.begin() as conn:
        conn.execute(text("drop schema public cascade; create schema public"))
    migrate.up(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def conn(engine):
    """Connection whose changes are rolled back after each test."""
    with engine.connect() as c:
        tx = c.begin()
        yield c
        tx.rollback()
