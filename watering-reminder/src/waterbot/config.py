"""Settings loaded from environment variables only (never from files committed to git)."""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    bot_token: str = field(repr=False)
    database_url: str = field(repr=False)
    run_mode: str = "webhook"
    webhook_secret: str = field(default="", repr=False)
    webhook_secret_token: str = field(default="", repr=False)
    public_url: str = ""
    port: int = 8000
    clock_offset_hours: float = 0.0

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env
        mode = env.get("RUN_MODE", "webhook").strip().lower()
        if mode not in {"webhook", "polling"}:
            raise ConfigError("RUN_MODE must be 'webhook' or 'polling'")
        required = ["BOT_TOKEN", "DATABASE_URL"]
        if mode == "webhook":
            required += ["WEBHOOK_SECRET", "WEBHOOK_SECRET_TOKEN", "RENDER_EXTERNAL_URL"]
        missing = [name for name in required if not env.get(name)]
        if missing:
            raise ConfigError("Missing environment variables: " + ", ".join(missing))
        try:
            offset = float(env.get("CLOCK_OFFSET_HOURS", "0") or 0)
            port = int(env.get("PORT", "8000") or 8000)
        except ValueError as exc:
            raise ConfigError("CLOCK_OFFSET_HOURS must be a number and PORT an integer") from exc
        return cls(
            bot_token=env["BOT_TOKEN"],
            database_url=env["DATABASE_URL"],
            run_mode=mode,
            webhook_secret=env.get("WEBHOOK_SECRET", ""),
            webhook_secret_token=env.get("WEBHOOK_SECRET_TOKEN", ""),
            public_url=env.get("RENDER_EXTERNAL_URL", "").rstrip("/"),
            port=port,
            clock_offset_hours=offset,
        )
