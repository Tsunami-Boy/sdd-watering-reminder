import pytest

from waterbot.config import ConfigError, Settings

BASE = {"BOT_TOKEN": "t", "DATABASE_URL": "postgresql://x"}
WEBHOOK = {
    **BASE,
    "WEBHOOK_SECRET": "a",
    "WEBHOOK_SECRET_TOKEN": "b",
    "RENDER_EXTERNAL_URL": "https://x.test/",
}


def test_webhook_mode_requires_secrets():
    with pytest.raises(ConfigError, match="WEBHOOK_SECRET"):
        Settings.from_env(BASE)
    s = Settings.from_env(WEBHOOK)
    assert s.run_mode == "webhook" and s.public_url == "https://x.test"


def test_polling_mode_needs_only_token_and_database():
    s = Settings.from_env(
        {**BASE, "RUN_MODE": "polling", "CLOCK_OFFSET_HOURS": "5", "PORT": "9000"}
    )
    assert s.run_mode == "polling" and s.clock_offset_hours == 5 and s.port == 9000


@pytest.mark.parametrize("bad", [{"RUN_MODE": "x"}, {"CLOCK_OFFSET_HOURS": "abc"}, {"PORT": "x"}])
def test_invalid_values(bad):
    with pytest.raises(ConfigError):
        Settings.from_env({**WEBHOOK, **bad})


def test_missing_token_is_reported_without_leaking_values():
    with pytest.raises(ConfigError) as exc:
        Settings.from_env({"DATABASE_URL": "postgresql://user:pw@h/db", "RUN_MODE": "polling"})
    assert "BOT_TOKEN" in str(exc.value) and "pw" not in str(exc.value)


def test_secrets_are_not_in_repr():
    assert "postgresql" not in repr(Settings.from_env(WEBHOOK)) and "'t'" not in repr(
        Settings.from_env(WEBHOOK)
    )
