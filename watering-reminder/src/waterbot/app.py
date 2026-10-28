"""FastAPI app: health check for the uptime monitor and the Telegram webhook."""

import hmac
import logging
from contextlib import asynccontextmanager
from typing import Any, Protocol

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from waterbot.config import Settings
from waterbot.logging_config import setup_logging
from waterbot.storage.postgres import PostgresRepository

log = logging.getLogger(__name__)


class Runtime(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def process_update(self, data: dict[str, Any]) -> None: ...


class HealthRepository(Protocol):
    async def health_check(self) -> bool: ...


def create_app(
    webhook_secret: str, webhook_secret_token: str, repo: HealthRepository, runtime: Runtime
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await runtime.start()
        try:
            yield
        finally:
            await runtime.stop()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    @app.api_route("/healthz", methods=["GET", "HEAD"])
    async def healthz() -> JSONResponse:
        if await repo.health_check():
            return JSONResponse({"status": "healthy"})
        return JSONResponse({"status": "degraded"}, status_code=503)

    @app.post("/webhook/{secret}")
    async def webhook(secret: str, request: Request) -> JSONResponse:
        if not webhook_secret or not hmac.compare_digest(secret, webhook_secret):
            return JSONResponse({"detail": "not found"}, status_code=404)
        header = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not hmac.compare_digest(header, webhook_secret_token):
            return JSONResponse({"detail": "forbidden"}, status_code=403)
        try:
            await runtime.process_update(await request.json())
        except Exception:
            # Always answer 200, otherwise Telegram keeps retrying the same update.
            log.exception("failed to hand the update to the bot")
        return JSONResponse({})

    return app


def build_app() -> FastAPI:
    """Factory used by uvicorn: `uvicorn waterbot.app:build_app --factory`."""
    from waterbot.runtime import BotRuntime

    settings = Settings.from_env()
    setup_logging([settings.bot_token, settings.webhook_secret, settings.webhook_secret_token])
    repo = PostgresRepository(settings.database_url)
    runtime = BotRuntime(settings, repo)
    return create_app(settings.webhook_secret, settings.webhook_secret_token, repo, runtime)
