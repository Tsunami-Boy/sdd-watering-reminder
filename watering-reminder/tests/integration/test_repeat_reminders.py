from datetime import date, timedelta

import pytest

from tests.fakes import FakeClock, utc
from waterbot.bot.flows import BotService
from waterbot.scheduler import tick

CHAT = 3
ZONE = "America/Santiago"  # UTC-3 in January


@pytest.fixture
async def plant(fake_repo):
    await fake_repo.ensure_user(CHAT, utc(2026, 1, 1))
    await fake_repo.set_timezone(CHAT, ZONE)
    return await fake_repo.add_plant(
        CHAT, "Catalina", "Dólar", 7, 14, date(2026, 1, 10), utc(2026, 1, 1)
    )


def local(h, m=0, day=17):
    return utc(2026, 1, day) + timedelta(hours=h + 3, minutes=m)  # Santiago is UTC-3


async def test_repeats_every_four_hours_then_nothing_overnight(fake_repo, notifier, plant):
    clock = FakeClock(local(8))
    log = []
    for hour in [8, 9, 12, 13, 16, 20, 22]:
        clock.set(local(hour))
        await tick(fake_repo, notifier, clock)
        log.append(len(notifier.sent))
    assert log == [1, 1, 2, 2, 3, 4, 4]
    assert [s.repeat for s in notifier.sent] == [False, True, True, True]

    clock.set(local(3, day=18))  # 03:00 next day
    await tick(fake_repo, notifier, clock)
    assert len(notifier.sent) == 4
    clock.set(local(8, day=18))
    await tick(fake_repo, notifier, clock)
    assert len(notifier.sent) == 5


async def test_one_pending_reminder_per_plant(fake_repo, notifier, plant):
    clock = FakeClock(local(8))
    for _ in range(5):
        await tick(fake_repo, notifier, clock)
        clock.advance(minutes=30)
    assert len(fake_repo.reminders) == 1


async def test_confirming_stops_later_messages(fake_repo, notifier, plant):
    clock = FakeClock(local(8))
    await tick(fake_repo, notifier, clock)
    clock.set(local(14))
    await BotService(fake_repo, clock).callback(CHAT, f"water:{plant.id}")
    for hour in [16, 20]:
        clock.set(local(hour))
        await tick(fake_repo, notifier, clock)
    assert len(notifier.sent) == 1


async def test_deleting_the_plant_stops_messages(fake_repo, notifier, plant):
    clock = FakeClock(local(8))
    await tick(fake_repo, notifier, clock)
    await fake_repo.delete_plant(CHAT, plant.id)
    clock.set(local(12))
    await tick(fake_repo, notifier, clock)
    assert len(notifier.sent) == 1


async def test_changing_timezone_reschedules_without_duplicates(fake_repo, notifier, plant):
    clock = FakeClock(local(8))
    await tick(fake_repo, notifier, clock)  # sent; next slot 12:00 Santiago
    service = BotService(fake_repo, clock)
    clock.set(local(9))  # 09:00 Santiago = 14:00 in Madrid (UTC+1)... still inside both windows
    await service.text(CHAT, "Europe/Madrid")
    assert len(fake_repo.reminders) == 1
    reminder = fake_repo.reminders[plant.id]
    assert reminder.next_send_at == clock.now()  # inside the new window: allowed right away


async def test_six_hours_offline_sends_one_message_not_a_burst(fake_repo, notifier, plant):
    await tick(fake_repo, notifier, FakeClock(local(8)))  # next slot 12:00
    await tick(fake_repo, notifier, FakeClock(local(18)))  # back after missing 12:00 and 16:00
    assert len(notifier.sent) == 2
    await tick(fake_repo, notifier, FakeClock(local(18, 1)))
    assert len(notifier.sent) == 2
