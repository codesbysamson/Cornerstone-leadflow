"""Engine configuration.

Only the settings with a production consequence are pinned here. Asserting on
SQLAlchemy's internals beyond that would make the suite a hostage to the driver.
"""

import pytest
from sqlalchemy import Engine

from app import database
from app.database import get_database_url


@pytest.fixture
def engine(monkeypatch: pytest.MonkeyPatch) -> Engine:
    """A throwaway engine built the same way the application builds it."""
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    database.get_engine.cache_clear()
    try:
        yield database.get_engine()
    finally:
        database.get_engine.cache_clear()


def test_pre_ping_is_enabled(engine: Engine) -> None:
    """A pooled connection is validated before it is handed out.

    Serverless PostgreSQL — Neon included — closes connections that have gone
    idle, and can suspend compute. Without pre-ping, the first request after a
    quiet period fails on a connection the database had already discarded, which
    looks like an intermittent application error rather than a stale socket.
    """
    assert engine.pool._pre_ping is True


def test_engine_uses_the_configured_database_url(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The URL still comes from the environment and nowhere else."""
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:other")

    assert get_database_url() == "sqlite+pysqlite:///:memory:other"
    assert "sqlite" in str(engine.url)


def test_missing_database_url_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """A blank DATABASE_URL must fail loudly rather than fall back to a default.

    Silently connecting to something unintended is how a deployment ends up
    writing to the wrong database.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL is not set"):
        get_database_url()
