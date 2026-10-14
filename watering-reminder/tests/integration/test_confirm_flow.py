from datetime import date

import pytest

from tests.fakes import FakeClock, utc
from waterbot.bot.flows import BotService
from waterbot.scheduler import tick

CHAT = 5


@pytest.fixture
def clock():
    return FakeClock(utc(2026, 1, 17, 11, 0))  # 08:00 in Santiago


@pytest.fixture
async def due_plant(fake_repo, clock):
    await fake_repo.ensure_user(CHAT, clock.now())
    await fake_repo.set_timezone(CHAT, "America/Santiago")
    return await fake_repo.add_plant(
        CHAT, "Catalina", "Dólar", 7, 14, date(2026, 1, 10), clock.now()
    )


async def test_confirm_clears_reminder_and_schedules_next(fake_repo, notifier, clock, due_plant):
    await tick(fake_repo, notifier, clock)
    service = BotService(fake_repo, clock)
    reply = await service.callback(CHAT, f"water:{due_plant.id}")
    assert reply.edit and reply.text == "Regada ✅. Próximo riego: 24/01/2026"
    assert await fake_repo.get_reminder(due_plant.id) is None
    assert (await fake_repo.get_plant(CHAT, due_plant.id)).last_watered_on == date(2026, 1, 17)


async def test_second_tap_is_inactive(fake_repo, notifier, clock, due_plant):
    await tick(fake_repo, notifier, clock)
    service = BotService(fake_repo, clock)
    await service.callback(CHAT, f"water:{due_plant.id}")
    again = await service.callback(CHAT, f"water:{due_plant.id}")
    assert again.alert == "Este recordatorio ya no está activo."
    assert not again.edit


async def test_other_chat_cannot_confirm(fake_repo, notifier, clock, due_plant):
    await tick(fake_repo, notifier, clock)
    await fake_repo.ensure_user(999, clock.now())
    await fake_repo.set_timezone(999, "America/Santiago")
    reply = await BotService(fake_repo, clock).callback(999, f"water:{due_plant.id}")
    assert reply.alert
    assert await fake_repo.get_reminder(due_plant.id) is not None  # still pending


async def test_late_confirmation_counts_from_confirmation_day(
    fake_repo, notifier, clock, due_plant
):
    await tick(fake_repo, notifier, clock)
    clock.set(utc(2026, 1, 20, 15, 0))  # 3 days late
    reply = await BotService(fake_repo, clock).callback(CHAT, f"water:{due_plant.id}")
    assert "27/01/2026" in reply.text  # 20 Jan + 7


async def test_season_change_uses_winter_interval(fake_repo, notifier, due_plant):
    # Confirmed on 5 Apr (south winter): next = +14 days, not +7.
    clock = FakeClock(utc(2026, 4, 5, 15, 0))
    await fake_repo.create_reminder(due_plant.id, date(2026, 4, 3), clock.now())
    reply = await BotService(fake_repo, clock).callback(CHAT, f"water:{due_plant.id}")
    assert "19/04/2026" in reply.text


async def test_malformed_callback_data(fake_repo, clock):
    reply = await BotService(fake_repo, clock).callback(CHAT, "water:abc")
    assert reply.alert
