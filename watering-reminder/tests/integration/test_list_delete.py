from datetime import date

import pytest

from tests.fakes import FakeClock, utc
from waterbot.bot.flows import BotService
from waterbot.scheduler import tick

CHAT = 11


@pytest.fixture
def clock():
    return FakeClock(utc(2026, 1, 17, 11, 0))


@pytest.fixture
async def service(fake_repo, clock):
    await fake_repo.ensure_user(CHAT, clock.now())
    await fake_repo.set_timezone(CHAT, "America/Santiago")
    return BotService(fake_repo, clock)


async def add(repo, name, ptype="Dólar", s=7, w=14, last=date(2026, 1, 10)):
    return await repo.add_plant(CHAT, name, ptype, s, w, last, utc(2026, 1, 1))


async def test_list_shows_every_field(service, fake_repo):
    await add(fake_repo, "Catalina", "Dólar", 7, 14)
    await add(fake_repo, "Bruno", "Cactus", 10, 30)
    text = (await service.plantas(CHAT)).text
    for expected in [
        "Catalina",
        "Dólar",
        "7",
        "14",
        "Bruno",
        "Cactus",
        "10",
        "30",
        "17/01/2026",
        "20/01/2026",
    ]:
        assert expected in text


async def test_empty_list_explains_how_to_add(service):
    assert "/agregar" in (await service.plantas(CHAT)).text


async def test_delete_flow_yes_removes_plant_and_pending_reminder(
    service, fake_repo, clock, notifier
):
    plant = await add(fake_repo, "Catalina")
    await tick(fake_repo, notifier, clock)
    assert await fake_repo.get_reminder(plant.id)

    choose = await service.eliminar(CHAT)
    assert [b.text for row in choose.buttons for b in row] == ["Catalina"]
    ask = await service.callback(CHAT, choose.buttons[0][0].data)
    assert "Catalina" in ask.text and [b.text for b in ask.buttons[0]] == ["Sí", "No"]
    done = await service.callback(CHAT, ask.buttons[0][0].data)
    assert "eliminada" in done.text
    assert await fake_repo.list_plants(CHAT) == []
    assert await fake_repo.get_reminder(plant.id) is None


async def test_delete_flow_no_keeps_plant(service, fake_repo):
    plant = await add(fake_repo, "Catalina")
    ask = await service.callback(CHAT, f"del:{plant.id}")
    result = await service.callback(CHAT, ask.buttons[0][1].data)
    assert result.text == "No se eliminó nada."
    assert len(await fake_repo.list_plants(CHAT)) == 1


async def test_deleting_a_missing_or_foreign_plant_is_graceful(service, fake_repo):
    plant = await add(fake_repo, "Catalina")
    await fake_repo.delete_plant(CHAT, plant.id)
    assert (await service.callback(CHAT, f"delok:{plant.id}")).text == "Esa planta ya no existe."
    assert (await service.callback(CHAT, "del:abc")).text == "Esa planta ya no existe."
    assert (await service.callback(CHAT + 1, f"del:{plant.id}")).text == "Esa planta ya no existe."


async def test_delete_with_no_plants(service):
    assert "/agregar" in (await service.eliminar(CHAT)).text
