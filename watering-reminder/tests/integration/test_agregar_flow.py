import pytest

from tests.fakes import FakeClock, utc
from waterbot.bot.flows import BotService

CHAT = 7


@pytest.fixture
def clock():
    return FakeClock(utc(2026, 1, 15, 15, 0))  # Santiago, summer, 12:00 local


@pytest.fixture
def service(fake_repo, clock):
    return BotService(fake_repo, clock)


async def register(service, name="Catalina", ptype="Dólar", summer="7", winter="14"):
    await service.agregar(CHAT)
    await service.text(CHAT, name)
    await service.text(CHAT, ptype)
    await service.text(CHAT, summer)
    return await service.text(CHAT, winter)


async def test_without_timezone_asks_for_zone_and_saves_nothing(service, fake_repo):
    reply = await service.agregar(CHAT)
    assert reply.text == "Primero elige tu zona con /zona."
    reply = await service.text(CHAT, "Catalina")
    assert await fake_repo.list_plants(CHAT) == []
    assert "/start" in reply.text  # not inside a flow: generic help


async def test_happy_path_saves_and_summarises(service, fake_repo, clock):
    await service.text(CHAT, "America/Santiago")
    summary = await register(service)
    for expected in ["Catalina", "Dólar", "7", "14", "22/01/2026"]:
        assert expected in summary.text
    [plant] = await fake_repo.list_plants(CHAT)
    assert (plant.name, plant.plant_type, plant.summer_days, plant.winter_days) == (
        "Catalina",
        "Dólar",
        7,
        14,
    )
    assert plant.last_watered_on.isoformat() == "2026-01-15"  # counts as watered today


@pytest.mark.parametrize("bad", ["0", "-1", "abc", "7.5", "400"])
async def test_invalid_interval_asks_again_on_same_step(service, fake_repo, bad):
    await service.text(CHAT, "America/Santiago")
    await service.agregar(CHAT)
    await service.text(CHAT, "Catalina")
    await service.text(CHAT, "Dólar")
    again = await service.text(CHAT, bad)
    assert "entre 1 y 365" in again.text or "número entero" in again.text
    ok = await service.text(CHAT, "7")  # still on the summer step, now accepted
    assert "invierno" in ok.text
    assert await fake_repo.list_plants(CHAT) == []


async def test_duplicate_name_is_rejected_case_insensitively(service, fake_repo):
    await service.text(CHAT, "America/Santiago")
    await register(service)
    await service.agregar(CHAT)
    reply = await service.text(CHAT, "catalina")
    assert "Ya tienes una planta" in reply.text
    next_step = await service.text(CHAT, "Otra")
    assert "tipo" in next_step.text.lower()


async def test_invalid_name_asks_again(service):
    await service.text(CHAT, "America/Santiago")
    await service.agregar(CHAT)
    assert "entre 1 y 40" in (await service.text(CHAT, "x" * 41)).text


@pytest.mark.parametrize("steps", [0, 1, 2, 3])
async def test_cancel_at_each_step_saves_nothing(service, fake_repo, steps):
    await service.text(CHAT, "America/Santiago")
    await service.agregar(CHAT)
    for answer in ["Catalina", "Dólar", "7"][:steps]:
        await service.text(CHAT, answer)
    assert (await service.cancelar(CHAT)).text == "Listo, cancelado."
    await service.text(CHAT, "14")  # outside a flow now
    assert await fake_repo.list_plants(CHAT) == []
    assert (await service.cancelar(CHAT)).text == "No hay nada que cancelar."
