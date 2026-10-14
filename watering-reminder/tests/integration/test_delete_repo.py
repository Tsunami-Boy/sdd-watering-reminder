from datetime import UTC, date, datetime

NOW = datetime(2026, 1, 17, 11, 0, tzinfo=UTC)


async def test_delete_only_affects_the_owner(postgres_repo):
    for chat in (1, 2):
        await postgres_repo.ensure_user(chat, NOW)
    mine = await postgres_repo.add_plant(1, "Mine", "t", 7, 7, date(2026, 1, 10), NOW)
    theirs = await postgres_repo.add_plant(2, "Theirs", "t", 7, 7, date(2026, 1, 10), NOW)
    await postgres_repo.create_reminder(mine.id, date(2026, 1, 17), NOW)

    assert await postgres_repo.delete_plant(2, mine.id) is False  # not theirs to delete
    assert await postgres_repo.delete_plant(1, mine.id) is True
    assert await postgres_repo.get_reminder(mine.id) is None
    assert [p.id for p in await postgres_repo.list_plants(2)] == [theirs.id]
    assert await postgres_repo.delete_plant(1, mine.id) is False  # already gone
