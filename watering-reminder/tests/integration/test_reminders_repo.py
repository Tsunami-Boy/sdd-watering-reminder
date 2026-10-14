import asyncio
from datetime import UTC, date, datetime, timedelta

from waterbot.storage.postgres import PostgresRepository

NOW = datetime(2026, 1, 17, 11, 0, tzinfo=UTC)


async def make_plants(repo, n=3):
    await repo.ensure_user(1, NOW)
    await repo.set_timezone(1, "America/Santiago")
    return [await repo.add_plant(1, f"P{i}", "t", 7, 14, date(2026, 1, 10), NOW) for i in range(n)]


async def test_create_is_unique_per_plant(postgres_repo):
    [plant] = await make_plants(postgres_repo, 1)
    assert await postgres_repo.create_reminder(plant.id, date(2026, 1, 17), NOW) is True
    assert await postgres_repo.create_reminder(plant.id, date(2026, 1, 17), NOW) is False


async def test_plants_without_reminder_excludes_those_with_one_and_users_without_zone(
    postgres_repo,
):
    plants = await make_plants(postgres_repo, 2)
    await postgres_repo.create_reminder(plants[0].id, date(2026, 1, 17), NOW)
    await postgres_repo.ensure_user(2, NOW)
    await postgres_repo.add_plant(2, "NoZone", "t", 7, 7, date(2026, 1, 10), NOW)
    found = await postgres_repo.plants_without_reminder()
    assert [(p.id, u.timezone) for p, u in found] == [(plants[1].id, "America/Santiago")]


async def test_claim_returns_only_due_rows_and_leases_them(postgres_repo):
    due, later, _ = await make_plants(postgres_repo)
    await postgres_repo.create_reminder(due.id, date(2026, 1, 17), NOW)
    await postgres_repo.create_reminder(later.id, date(2026, 1, 17), NOW + timedelta(hours=4))

    claimed = await postgres_repo.claim_due_reminders(NOW, lease_seconds=120)
    assert [c.plant.id for c in claimed] == [due.id]
    assert claimed[0].user.timezone == "America/Santiago"
    assert claimed[0].reminder.send_count == 0

    assert await postgres_repo.claim_due_reminders(NOW, 120) == []  # leased
    assert [
        c.plant.id for c in await postgres_repo.claim_due_reminders(NOW + timedelta(minutes=3), 120)
    ] == [due.id]


async def test_concurrent_claims_never_return_the_same_row(postgres_repo):
    plants = await make_plants(postgres_repo, 6)
    for p in plants:
        await postgres_repo.create_reminder(p.id, date(2026, 1, 17), NOW)
    batches = await asyncio.gather(*[postgres_repo.claim_due_reminders(NOW, 120) for _ in range(4)])
    ids = [c.plant.id for batch in batches for c in batch]
    assert sorted(ids) == sorted(p.id for p in plants)  # each exactly once


async def test_record_sent_and_survival_across_instances(postgres_repo):
    [plant] = await make_plants(postgres_repo, 1)
    await postgres_repo.create_reminder(plant.id, date(2026, 1, 17), NOW)
    await postgres_repo.record_sent(plant.id, NOW, NOW + timedelta(hours=4), 77)

    fresh = PostgresRepository(postgres_repo._dsn)
    reminder = await fresh.get_reminder(plant.id)
    assert reminder.send_count == 1 and reminder.message_id == 77
    assert reminder.next_send_at == NOW + timedelta(hours=4)
    assert reminder.last_sent_at == NOW


async def test_confirm_deletes_reminder_once(postgres_repo):
    [plant] = await make_plants(postgres_repo, 1)
    await postgres_repo.create_reminder(plant.id, date(2026, 1, 17), NOW)
    assert await postgres_repo.delete_reminder(plant.id) is True
    assert await postgres_repo.delete_reminder(plant.id) is False


async def test_deleting_the_plant_removes_its_reminder(postgres_repo):
    [plant] = await make_plants(postgres_repo, 1)
    await postgres_repo.create_reminder(plant.id, date(2026, 1, 17), NOW)
    assert await postgres_repo.delete_plant(1, plant.id) is True
    assert await postgres_repo.get_reminder(plant.id) is None


async def test_reminders_for_user_and_reschedule(postgres_repo):
    [plant] = await make_plants(postgres_repo, 1)
    await postgres_repo.create_reminder(plant.id, date(2026, 1, 17), NOW)
    await postgres_repo.set_next_send_at(plant.id, NOW + timedelta(hours=9))
    [reminder] = await postgres_repo.reminders_for_user(1)
    assert reminder.next_send_at == NOW + timedelta(hours=9)
    assert await postgres_repo.reminders_for_user(2) == []
