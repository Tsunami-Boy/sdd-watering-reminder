import asyncio
from datetime import UTC, date, datetime

import psycopg
import pytest

from waterbot.storage.interface import DuplicatePlantName
from waterbot.storage.postgres import PostgresRepository

NOW = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


async def user(repo, chat=1):
    await repo.ensure_user(chat, NOW)


async def test_plant_is_saved_and_read_back_from_a_new_connection(postgres_repo):
    await user(postgres_repo)
    saved = await postgres_repo.add_plant(1, "Catalina", "Dólar", 7, 14, date(2026, 1, 15), NOW)

    fresh = PostgresRepository(postgres_repo._dsn)  # as after a restart
    [found] = await fresh.list_plants(1)
    assert found == saved
    assert (found.name, found.plant_type, found.summer_days, found.winter_days) == (
        "Catalina",
        "Dólar",
        7,
        14,
    )
    assert found.last_watered_on == date(2026, 1, 15)
    assert await fresh.get_plant(1, saved.id) == saved


async def test_duplicate_name_differing_by_case_is_rejected(postgres_repo):
    await user(postgres_repo)
    await postgres_repo.add_plant(1, "Catalina", "Dólar", 7, 14, date(2026, 1, 15), NOW)
    with pytest.raises(DuplicatePlantName):
        await postgres_repo.add_plant(1, "CATALINA", "Otra", 3, 6, date(2026, 1, 15), NOW)


async def test_same_name_for_two_users_is_allowed(postgres_repo):
    await user(postgres_repo, 1)
    await user(postgres_repo, 2)
    await postgres_repo.add_plant(1, "Catalina", "Dólar", 7, 14, date(2026, 1, 15), NOW)
    await postgres_repo.add_plant(2, "Catalina", "Dólar", 7, 14, date(2026, 1, 15), NOW)
    assert len(await postgres_repo.list_plants(1)) == 1
    assert len(await postgres_repo.list_plants(2)) == 1


@pytest.mark.parametrize(
    "name,ptype,summer,winter",
    [
        ("", "t", 7, 7),
        ("x" * 41, "t", 7, 7),
        ("n", "t" * 61, 7, 7),
        ("n", "t", 0, 7),
        ("n", "t", 7, 366),
    ],
)
async def test_database_checks_reject_out_of_range_values(
    postgres_repo, name, ptype, summer, winter
):
    await user(postgres_repo)
    with pytest.raises(psycopg.errors.CheckViolation):
        await postgres_repo.add_plant(1, name, ptype, summer, winter, date(2026, 1, 15), NOW)


async def test_deleting_a_user_cascades_to_plants_and_reminders(postgres_repo):
    await user(postgres_repo)
    plant = await postgres_repo.add_plant(1, "C", "D", 7, 14, date(2026, 1, 15), NOW)
    await postgres_repo.create_reminder(plant.id, date(2026, 1, 22), NOW)
    async with await psycopg.AsyncConnection.connect(postgres_repo._dsn, autocommit=True) as conn:
        await conn.execute("DELETE FROM users WHERE chat_id = 1")
    assert await postgres_repo.list_plants(1) == []
    assert await postgres_repo.get_reminder(plant.id) is None


async def test_mark_watered_persists(postgres_repo):
    await user(postgres_repo)
    plant = await postgres_repo.add_plant(1, "C", "D", 7, 14, date(2026, 1, 15), NOW)
    await postgres_repo.mark_watered(plant.id, date(2026, 1, 30))
    assert (await postgres_repo.get_plant(1, plant.id)).last_watered_on == date(2026, 1, 30)


async def test_concurrent_adds_of_the_same_name_create_only_one(postgres_repo):
    await user(postgres_repo)
    results = await asyncio.gather(
        *[postgres_repo.add_plant(1, "Dup", "t", 7, 7, date(2026, 1, 15), NOW) for _ in range(4)],
        return_exceptions=True,
    )
    assert sum(not isinstance(r, Exception) for r in results) == 1
    assert len(await postgres_repo.list_plants(1)) == 1
