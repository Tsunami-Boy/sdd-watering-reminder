from datetime import date

from tests.fakes import FakeClock, utc
from waterbot.bot.flows import BotService
from waterbot.scheduler import tick


async def test_two_users_with_different_zones_get_independent_reminders(fake_repo, notifier):
    # Both plants are due on 17 Jan: Santiago is in summer (7 days), Tokyo in winter (14 days).
    for chat, zone, last in [
        (1, "America/Santiago", date(2026, 1, 10)),
        (2, "Asia/Tokyo", date(2026, 1, 3)),
    ]:
        await fake_repo.ensure_user(chat, utc(2026, 1, 1))
        await fake_repo.set_timezone(chat, zone)
        await fake_repo.add_plant(chat, "Catalina", "Dólar", 7, 14, last, utc(2026, 1, 1))

    clock = FakeClock(utc(2026, 1, 16, 23, 0))  # 08:00 on 17 Jan in Tokyo, 20:00 on 16th Santiago
    await tick(fake_repo, notifier, clock)
    assert [s.chat_id for s in notifier.sent] == [2]
    clock.set(utc(2026, 1, 17, 11, 0))  # 08:00 in Santiago (and the 20:00 repeat slot in Tokyo)
    await tick(fake_repo, notifier, clock)
    assert [(s.chat_id, s.repeat) for s in notifier.sent if s.chat_id == 1] == [(1, False)]
    assert [(s.chat_id, s.repeat) for s in notifier.sent if s.chat_id == 2] == [
        (2, False),
        (2, True),
    ]


async def test_users_cannot_see_or_delete_each_others_plants(fake_repo):
    clock = FakeClock(utc(2026, 1, 17, 12))
    service = BotService(fake_repo, clock)
    for chat in (1, 2):
        await service.text(chat, "America/Santiago")
    mine = await fake_repo.add_plant(1, "Mine", "t", 7, 7, date(2026, 1, 10), clock.now())

    assert "Mine" not in (await service.plantas(2)).text
    assert (await service.callback(2, f"delok:{mine.id}")).text == "Esa planta ya no existe."
    assert len(await fake_repo.list_plants(1)) == 1
    assert (await service.callback(2, f"water:{mine.id}")).alert


async def test_same_plant_name_for_two_users(fake_repo):
    clock = FakeClock(utc(2026, 1, 17, 12))
    service = BotService(fake_repo, clock)
    for chat in (1, 2):
        await service.text(chat, "America/Santiago")
        await service.agregar(chat)
        for answer in ["Catalina", "Dólar", "7", "14"]:
            await service.text(chat, answer)
    assert len(await fake_repo.list_plants(1)) == len(await fake_repo.list_plants(2)) == 1
