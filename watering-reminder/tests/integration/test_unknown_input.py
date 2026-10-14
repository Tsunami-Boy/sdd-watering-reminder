from tests.fakes import FakeClock, utc
from waterbot.bot.flows import BotService


async def test_plain_text_outside_a_flow_shows_help(fake_repo):
    service = BotService(fake_repo, FakeClock(utc(2026, 1, 1)))
    assert "/start" in (await service.text(1, "hola")).text


async def test_unknown_callback_data_is_answered(fake_repo):
    service = BotService(fake_repo, FakeClock(utc(2026, 1, 1)))
    assert (await service.callback(1, "nonsense:1")).alert


async def test_slash_looking_text_that_is_not_a_zone_is_explained(fake_repo):
    service = BotService(fake_repo, FakeClock(utc(2026, 1, 1)))
    assert "no es una zona" in (await service.text(1, "Nope/Nowhere")).text
