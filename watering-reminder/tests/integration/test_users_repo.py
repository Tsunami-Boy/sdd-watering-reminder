from datetime import UTC, datetime

from waterbot.storage.postgres import PostgresRepository

NOW = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)


async def test_ensure_user_is_idempotent_and_timezone_persists(postgres_repo):
    first = await postgres_repo.ensure_user(10, NOW)
    again = await postgres_repo.ensure_user(10, datetime(2030, 1, 1, tzinfo=UTC))
    assert first == again and first.timezone is None

    await postgres_repo.set_timezone(10, "America/Santiago")

    other = PostgresRepository(postgres_repo._dsn)  # a new instance, as after a restart
    user = await other.get_user(10)
    assert user is not None and user.timezone == "America/Santiago"


async def test_unknown_user_is_none(postgres_repo):
    assert await postgres_repo.get_user(999) is None


async def test_health_check(postgres_repo):
    assert await postgres_repo.health_check() is True
