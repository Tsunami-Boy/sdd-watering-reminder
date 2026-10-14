"""Plain data objects shared by every layer (see specs/.../data-model.md)."""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class User:
    chat_id: int
    timezone: str | None
    created_at: datetime


@dataclass(frozen=True)
class Plant:
    id: int
    chat_id: int
    name: str
    plant_type: str
    summer_days: int
    winter_days: int
    last_watered_on: date
    created_at: datetime


@dataclass(frozen=True)
class Reminder:
    plant_id: int
    due_on: date
    next_send_at: datetime
    last_sent_at: datetime | None
    send_count: int
    message_id: int | None


@dataclass(frozen=True)
class DueReminder:
    """A claimed reminder together with the plant and user it belongs to."""

    reminder: Reminder
    plant: Plant
    user: User
