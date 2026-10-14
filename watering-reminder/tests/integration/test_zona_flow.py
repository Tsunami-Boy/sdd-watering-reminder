import pytest

from tests.fakes import FakeClock, utc
from waterbot.bot import timezones
from waterbot.bot.flows import BotService

CHAT = 42


@pytest.fixture
def clock():
    return FakeClock(utc(2026, 1, 15, 15, 5))  # 12:05 in Santiago (UTC-3, summer time)


@pytest.fixture
def service(fake_repo, clock):
    return BotService(fake_repo, clock)


async def test_start_lists_every_command(service):
    reply = await service.start(CHAT)
    for command in ["/zona", "/agregar", "/plantas", "/eliminar", "/cancelar"]:
        assert command in reply.text


async def test_region_page_zone_selection_stores_zone(service, fake_repo):
    reply = await service.zona(CHAT)
    assert any(b.data == timezones.region_callback("am") for row in reply.buttons for b in row)

    page = await service.callback(CHAT, timezones.region_callback("am"))
    zone_buttons = [b for row in page.buttons for b in row if b.data.startswith("tz:s:")]
    assert zone_buttons and page.edit

    chosen = await service.callback(CHAT, timezones.zone_callback("America/Santiago"))
    assert "America/Santiago" in chosen.text
    assert "12:05" in chosen.text
    assert "verano" in chosen.text
    assert (await fake_repo.get_user(CHAT)).timezone == "America/Santiago"


async def test_paging_buttons_navigate(service):
    page1 = await service.callback(CHAT, timezones.region_callback("am"))
    assert any(b.data == timezones.page_callback("am", 1) for row in page1.buttons for b in row)
    page2 = await service.callback(CHAT, timezones.page_callback("am", 1))
    assert any(b.data == timezones.page_callback("am", 0) for row in page2.buttons for b in row)
    back = await service.callback(CHAT, timezones.BACK_CALLBACK)
    assert back.text == (await service.zona(CHAT)).text


async def test_typed_valid_zone_is_stored(service, fake_repo):
    reply = await service.text(CHAT, "europe/madrid")
    assert "Europe/Madrid" in reply.text and "invierno" in reply.text
    assert (await fake_repo.get_user(CHAT)).timezone == "Europe/Madrid"


async def test_typed_invalid_zone_keeps_previous_zone(service, fake_repo):
    await service.text(CHAT, "America/Santiago")
    reply = await service.text(CHAT, "Nope/Nowhere")
    assert "no es una zona" in reply.text
    assert (await fake_repo.get_user(CHAT)).timezone == "America/Santiago"
    bad_callback = await service.callback(CHAT, "tz:s:Nope/Nowhere")
    assert bad_callback.alert
    assert (await fake_repo.get_user(CHAT)).timezone == "America/Santiago"


async def test_changing_zone_replaces_it(service, fake_repo):
    await service.text(CHAT, "America/Santiago")
    await service.text(CHAT, "Asia/Tokyo")
    assert (await fake_repo.get_user(CHAT)).timezone == "Asia/Tokyo"
