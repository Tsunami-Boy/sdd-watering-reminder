import os

import pytest

from tests.fakes import FakeNotifier, FakeRepository
from waterbot.storage.postgres import PostgresRepository

_TABLES = "reminders, plants, users"


@pytest.fixture
def fake_repo() -> FakeRepository:
    return FakeRepository()


@pytest.fixture
def notifier() -> FakeNotifier:
    return FakeNotifier()


@pytest.fixture(scope="session")
def _test_dsn(tmp_path_factory):
    """TEST_DATABASE_URL, or an embedded PostgreSQL when `pgserver` is installed (no Docker)."""
    dsn = os.environ.get("TEST_DATABASE_URL")
    if dsn:
        yield dsn
        return
    try:
        import pgserver
    except ImportError:
        yield None
        return
    server = pgserver.get_server(tmp_path_factory.mktemp("pgdata"), cleanup_mode="stop")
    yield server.get_uri()
    server.cleanup()


@pytest.fixture
async def postgres_repo(_test_dsn):
    dsn = _test_dsn
    if not dsn:
        pytest.skip("TEST_DATABASE_URL is not set (and pgserver is not installed)")
    repo = PostgresRepository(dsn)
    await repo.apply_schema()
    import psycopg

    async with await psycopg.AsyncConnection.connect(dsn, autocommit=True) as conn:
        await conn.execute(f"TRUNCATE {_TABLES} RESTART IDENTITY CASCADE")
    yield repo


def pytest_collection_modifyitems(config, items):
    """Tests marked `postgres` use the postgres_repo fixture, which skips without a database."""
    for item in items:
        if "postgres_repo" in getattr(item, "fixturenames", ()):
            item.add_marker(pytest.mark.postgres)
