from datetime import date

import pytest

from tests.fakes import FakeClock, utc
from waterbot.bot import messages
from waterbot.bot.flows import BotService
from waterbot.scheduler import tick

CHAT = 5


@pytest.fixture
def clock():
    return FakeClock(utc(2026, 1, 12, 11, 0))  # 08:00 in Santiago, summer


@pytest.fixture
async def plant(fake_repo, clock):
    await fake_repo.ensure_user(CHAT, clock.now())
    await fake_repo.set_timezone(CHAT, "America/Santiago")
    return await fake_repo.add_plant(
        CHAT, "Catalina", "Dólar", 7, 14, date(2026, 1, 10), clock.now()
    )


@pytest.fixture
def service(fake_repo, clock):
    return BotService(fake_repo, clock)


async def last_watered(fake_repo, plant):
    return (await fake_repo.get_plant(CHAT, plant.id)).last_watered_on


# US1 ----------------------------------------------------------------------------------


async def test_regar_lists_one_button_per_plant(service, plant, fake_repo, clock):
    await fake_repo.add_plant(CHAT, "Otra", "Cactus", 10, 20, date(2026, 1, 10), clock.now())
    reply = await service.regar(CHAT)
    assert reply.text == messages.REGAR_CHOOSE
    assert [b.text for row in reply.buttons for b in row] == ["Catalina", "Otra"]
    assert reply.buttons[0][0].data == f"reg:{plant.id}"


async def test_choosing_a_plant_asks_confirmation(service, plant, fake_repo):
    reply = await service.callback(CHAT, f"reg:{plant.id}")
    assert reply.edit and reply.text == messages.regar_ask("Catalina")
    assert [(b.text, b.data) for b in reply.buttons[0]] == [
        ("Sí", f"regok:{plant.id}"),
        ("No", "regno"),
    ]
    assert await last_watered(fake_repo, plant) == date(2026, 1, 10)


async def test_confirm_sets_today_and_next_due(service, plant, fake_repo):
    reply = await service.callback(CHAT, f"regok:{plant.id}")
    assert reply.edit and reply.text == messages.regar_done("Catalina", date(2026, 1, 19))
    assert await last_watered(fake_repo, plant) == date(2026, 1, 12)


async def test_confirm_uses_season_in_effect_today(service, plant, fake_repo, clock):
    clock.set(utc(2026, 7, 10, 15, 0))  # winter in Santiago: 14 days
    reply = await service.callback(CHAT, f"regok:{plant.id}")
    assert "24/07/2026" in reply.text


async def test_decline_changes_nothing(service, plant, fake_repo):
    reply = await service.callback(CHAT, "regno")
    assert reply.edit and reply.text == messages.REGAR_CANCELLED
    assert await last_watered(fake_repo, plant) == date(2026, 1, 10)


async def test_no_reminder_on_original_due_date(service, plant, fake_repo, notifier, clock):
    await service.callback(CHAT, f"regok:{plant.id}")  # watered 12 Jan, originally due 17 Jan
    clock.set(utc(2026, 1, 17, 11, 0))
    await tick(fake_repo, notifier, clock)
    assert await fake_repo.get_reminder(plant.id) is None


# US2 ----------------------------------------------------------------------------------


async def test_pending_reminder_is_cleared(service, plant, fake_repo, notifier, clock):
    clock.set(utc(2026, 1, 17, 11, 0))
    await tick(fake_repo, notifier, clock)
    assert await fake_repo.get_reminder(plant.id) is not None
    await service.callback(CHAT, f"regok:{plant.id}")
    assert await fake_repo.get_reminder(plant.id) is None
    assert await last_watered(fake_repo, plant) == date(2026, 1, 17)


async def test_no_repeats_after_regar(service, plant, fake_repo, notifier, clock):
    clock.set(utc(2026, 1, 17, 11, 0))
    await tick(fake_repo, notifier, clock)
    await service.callback(CHAT, f"regok:{plant.id}")
    sent = len(notifier.sent)
    clock.set(utc(2026, 1, 17, 23, 0))
    await tick(fake_repo, notifier, clock)
    assert len(notifier.sent) == sent


async def test_old_ya_regue_is_inactive(service, plant, fake_repo, notifier, clock):
    clock.set(utc(2026, 1, 17, 11, 0))
    await tick(fake_repo, notifier, clock)
    await service.callback(CHAT, f"regok:{plant.id}")
    reply = await service.callback(CHAT, f"water:{plant.id}")
    assert reply.alert == messages.REMINDER_INACTIVE
    assert await last_watered(fake_repo, plant) == date(2026, 1, 17)


# US3 ----------------------------------------------------------------------------------


async def test_regar_without_timezone(fake_repo, clock):
    await fake_repo.ensure_user(CHAT, clock.now())
    reply = await BotService(fake_repo, clock).regar(CHAT)
    assert reply.text == messages.NEED_TIMEZONE


async def test_regar_without_plants(fake_repo, clock):
    await fake_repo.ensure_user(CHAT, clock.now())
    await fake_repo.set_timezone(CHAT, "America/Santiago")
    reply = await BotService(fake_repo, clock).regar(CHAT)
    assert reply.text == messages.NO_PLANTS


async def test_deleted_plant(service, plant, fake_repo):
    await fake_repo.delete_plant(CHAT, plant.id)
    for data in (f"reg:{plant.id}", f"regok:{plant.id}"):
        reply = await service.callback(CHAT, data)
        assert reply.text == messages.PLANT_GONE


async def test_other_chat_cannot_water(service, plant, fake_repo, clock):
    await fake_repo.ensure_user(999, clock.now())
    await fake_repo.set_timezone(999, "America/Santiago")
    reply = await BotService(fake_repo, clock).callback(999, f"regok:{plant.id}")
    assert reply.text == messages.PLANT_GONE
    assert await last_watered(fake_repo, plant) == date(2026, 1, 10)


async def test_cancelar_after_regar(service, plant, fake_repo):
    await service.regar(CHAT)
    reply = await service.cancelar(CHAT)
    assert reply.text == messages.NOTHING_TO_CANCEL
    assert await last_watered(fake_repo, plant) == date(2026, 1, 10)


async def test_confirm_twice_is_idempotent(service, plant):
    first = await service.callback(CHAT, f"regok:{plant.id}")
    second = await service.callback(CHAT, f"regok:{plant.id}")
    assert first.text == second.text


@pytest.mark.parametrize("data", ["reg:abc", "regok:abc", "reg:", "regok:"])
async def test_non_numeric_ids(service, data):
    reply = await service.callback(CHAT, data)
    assert reply.text == messages.PLANT_GONE
