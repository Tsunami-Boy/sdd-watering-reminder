"""Storage boundary. The scheduler and the bot only talk to this protocol."""

from datetime import date, datetime
from typing import Protocol

from waterbot.domain.models import DueReminder, Plant, Reminder, User


class DuplicatePlantName(Exception):
    """The user already has a plant with this name (case-insensitive)."""


class Repository(Protocol):
    async def ensure_user(self, chat_id: int, now: datetime) -> User: ...

    async def get_user(self, chat_id: int) -> User | None: ...

    async def set_timezone(self, chat_id: int, zone: str) -> None: ...

    async def add_plant(
        self,
        chat_id: int,
        name: str,
        plant_type: str,
        summer_days: int,
        winter_days: int,
        last_watered_on: date,
        now: datetime,
    ) -> Plant:
        """Raises DuplicatePlantName."""
        ...

    async def list_plants(self, chat_id: int) -> list[Plant]: ...

    async def get_plant(self, chat_id: int, plant_id: int) -> Plant | None: ...

    async def delete_plant(self, chat_id: int, plant_id: int) -> bool: ...

    async def mark_watered(self, plant_id: int, on: date) -> None: ...

    async def plants_without_reminder(self) -> list[tuple[Plant, User]]:
        """Plants of users that have a time zone and no pending reminder."""
        ...

    async def create_reminder(self, plant_id: int, due_on: date, next_send_at: datetime) -> bool:
        """False if the plant already has a reminder."""
        ...

    async def claim_due_reminders(self, now: datetime, lease_seconds: int) -> list[DueReminder]:
        """Atomically return reminders with next_send_at <= now, pushing their next_send_at
        `lease_seconds` ahead so no other worker claims them and a failed send retries later."""
        ...

    async def record_sent(
        self, plant_id: int, sent_at: datetime, next_send_at: datetime, message_id: int | None
    ) -> None: ...

    async def get_reminder(self, plant_id: int) -> Reminder | None: ...

    async def delete_reminder(self, plant_id: int) -> bool: ...

    async def reminders_for_user(self, chat_id: int) -> list[Reminder]: ...

    async def set_next_send_at(self, plant_id: int, when: datetime) -> None: ...

    async def health_check(self) -> bool: ...
