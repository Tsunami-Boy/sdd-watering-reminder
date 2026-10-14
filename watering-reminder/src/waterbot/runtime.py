"""Wires Telegram, the scheduler and storage together and owns their lifecycle."""

import asyncio
import contextlib
import logging
from typing import Any

from telegram import BotCommand, Update
from telegram.ext import Application

from waterbot import scheduler
from waterbot.bot import messages
from waterbot.bot.flows import BotService
from waterbot.bot.handlers import register_handlers
from waterbot.config import Settings
from waterbot.domain.clock import clock_from_offset
from waterbot.notifier import TelegramNotifier
from waterbot.storage.postgres import PostgresRepository

log = logging.getLogger(__name__)


class BotRuntime:
    def __init__(self, settings: Settings, repo: PostgresRepository) -> None:
        self._settings = settings
        self._repo = repo
        builder = Application.builder().token(settings.bot_token)
        if settings.run_mode == "webhook":
            builder = builder.updater(None)  # updates arrive through our own HTTP endpoint
        self._application = builder.build()
        clock = clock_from_offset(settings.clock_offset_hours)
        register_handlers(self._application, BotService(repo, clock))
        self._notifier = TelegramNotifier(self._application.bot)
        self._clock = clock
        self._scheduler_task: asyncio.Task | None = None

    async def start(self) -> None:
        await self._repo.apply_schema()
        app = self._application
        await app.initialize()
        await app.bot.set_my_commands([BotCommand(n, d) for n, d in messages.COMMANDS])
        await app.start()
        if self._settings.run_mode == "webhook":
            await app.bot.set_webhook(
                url=f"{self._settings.public_url}/webhook/{self._settings.webhook_secret}",
                secret_token=self._settings.webhook_secret_token,
                allowed_updates=Update.ALL_TYPES,
            )
        else:
            await app.bot.delete_webhook()
            await app.updater.start_polling()
        self._scheduler_task = asyncio.create_task(
            scheduler.run_forever(self._repo, self._notifier, self._clock)
        )
        log.info("bot started in %s mode", self._settings.run_mode)

    async def stop(self) -> None:
        if self._scheduler_task:
            self._scheduler_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._scheduler_task
        app = self._application
        if app.updater and app.updater.running:
            await app.updater.stop()
        if app.running:
            await app.stop()
        await app.shutdown()

    async def process_update(self, data: dict[str, Any]) -> None:
        update = Update.de_json(data, self._application.bot)
        await self._application.update_queue.put(update)
