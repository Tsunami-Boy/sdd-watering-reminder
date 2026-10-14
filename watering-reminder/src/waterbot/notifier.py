"""Outgoing messages. The Telegram implementation lives next to the protocol."""

from typing import Protocol

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from waterbot.bot import messages


class Notifier(Protocol):
    async def send_reminder(
        self, chat_id: int, plant_name: str, plant_type: str, plant_id: int, repeat: bool
    ) -> int:
        """Send a reminder with its confirm button; return the Telegram message id."""
        ...


class TelegramNotifier:
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send_reminder(
        self, chat_id: int, plant_name: str, plant_type: str, plant_id: int, repeat: bool
    ) -> int:
        markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton(messages.CONFIRM_BUTTON, callback_data=f"water:{plant_id}")]]
        )
        message = await self._bot.send_message(
            chat_id, messages.reminder_text(plant_name, plant_type, repeat), reply_markup=markup
        )
        return message.message_id
