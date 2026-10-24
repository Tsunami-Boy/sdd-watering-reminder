"""The real Telegram wiring builds and routes updates without touching the network."""

from telegram import Update

from tests.fakes import FakeClock, utc
from waterbot.bot.flows import BotService, Button, Reply
from waterbot.bot.handlers import _markup, register_handlers
from waterbot.config import Settings
from waterbot.runtime import BotRuntime
from waterbot.storage.postgres import PostgresRepository

ENV = {
    "BOT_TOKEN": "123456:test-token",
    "DATABASE_URL": "postgresql://u:p@localhost/db",
    "RUN_MODE": "webhook",
    "WEBHOOK_SECRET": "a",
    "WEBHOOK_SECRET_TOKEN": "b",
    "RENDER_EXTERNAL_URL": "https://example.test",
}


async def test_runtime_builds_and_queues_updates():
    runtime = BotRuntime(Settings.from_env(ENV), PostgresRepository(ENV["DATABASE_URL"]))
    await runtime.process_update(
        {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "date": 0,
                "chat": {"id": 5, "type": "private"},
                "text": "/start",
                "entities": [{"type": "bot_command", "offset": 0, "length": 6}],
            },
        }
    )
    queued = runtime._application.update_queue.get_nowait()
    assert isinstance(queued, Update) and queued.message.text == "/start"


def test_all_commands_and_callbacks_are_registered(fake_repo):
    runtime = BotRuntime(Settings.from_env(ENV), PostgresRepository(ENV["DATABASE_URL"]))
    handlers = runtime._application.handlers[0]
    commands = {c for h in handlers if hasattr(h, "commands") for c in h.commands}
    assert {"start", "zona", "agregar", "plantas", "regar", "eliminar", "cancelar"} <= commands
    assert len(handlers) == 10  # 7 commands + callbacks + text + unknown command


def test_reply_buttons_become_inline_keyboard():
    markup = _markup(Reply("x", [[Button("A", "a"), Button("B", "b")], [Button("C", "c")]]))
    assert [[b.callback_data for b in row] for row in markup.inline_keyboard] == [["a", "b"], ["c"]]
    assert _markup(Reply("x")) is None


def test_register_handlers_exposes_the_service(fake_repo):
    from telegram.ext import Application

    app = Application.builder().token("123456:test-token").build()
    service = BotService(fake_repo, FakeClock(utc(2026, 1, 1)))
    register_handlers(app, service)
    assert app.bot_data["service"] is service
