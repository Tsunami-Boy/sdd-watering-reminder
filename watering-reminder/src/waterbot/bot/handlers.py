"""Thin adapter between python-telegram-bot and `BotService`."""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from waterbot.bot import messages
from waterbot.bot.flows import BotService, Reply

log = logging.getLogger(__name__)

_SERVICE_KEY = "service"
_PRIVATE = filters.ChatType.PRIVATE


def _markup(reply: Reply) -> InlineKeyboardMarkup | None:
    if not reply.buttons:
        return None
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(b.text, callback_data=b.data) for b in row] for row in reply.buttons]
    )


def _service(context: ContextTypes.DEFAULT_TYPE) -> BotService:
    return context.application.bot_data[_SERVICE_KEY]


def _command(method: str):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat = update.effective_chat
        if chat is None or update.message is None:
            return
        reply: Reply = await getattr(_service(context), method)(chat.id)
        await update.message.reply_text(reply.text, reply_markup=_markup(reply))

    return handler


async def _on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat is None or update.message is None or not update.message.text:
        return
    reply = await _service(context).text(update.effective_chat.id, update.message.text)
    await update.message.reply_text(reply.text, reply_markup=_markup(reply))


async def _on_unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is not None:
        await update.message.reply_text(messages.HELP)


async def _on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.message is None or query.data is None:
        return
    reply = await _service(context).callback(query.message.chat.id, query.data)
    await query.answer(text=reply.alert)
    if reply.edit:
        await query.edit_message_text(reply.text, reply_markup=_markup(reply))
    elif not reply.alert:
        await query.message.reply_text(reply.text, reply_markup=_markup(reply))


async def _on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("unhandled error while processing an update", exc_info=context.error)


def register_handlers(application: Application, service: BotService) -> None:
    application.bot_data[_SERVICE_KEY] = service
    for name, method in [
        ("start", "start"),
        ("zona", "zona"),
        ("agregar", "agregar"),
        ("plantas", "plantas"),
        ("eliminar", "eliminar"),
        ("cancelar", "cancelar"),
    ]:
        application.add_handler(CommandHandler(name, _command(method), filters=_PRIVATE))
    application.add_handler(CallbackQueryHandler(_on_callback))
    application.add_handler(MessageHandler(_PRIVATE & filters.TEXT & ~filters.COMMAND, _on_text))
    application.add_handler(MessageHandler(_PRIVATE & filters.COMMAND, _on_unknown_command))
    application.add_error_handler(_on_error)
