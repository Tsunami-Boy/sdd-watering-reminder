"""Use cases that combine the repository with the domain rules."""

from dataclasses import dataclass, replace
from datetime import date, datetime

from waterbot.domain.models import Plant
from waterbot.domain.schedule import local_date, next_allowed_send, next_due_on
from waterbot.storage.interface import Repository


async def change_timezone(repo: Repository, chat_id: int, zone: str, now: datetime) -> None:
    """Store the zone and move pending reminders to the new zone's send window."""
    await repo.set_timezone(chat_id, zone)
    for reminder in await repo.reminders_for_user(chat_id):
        await repo.set_next_send_at(reminder.plant_id, next_allowed_send(zone, now))


@dataclass(frozen=True)
class WateredResult:
    plant: Plant
    next_due: date


async def confirm_watering(
    repo: Repository, chat_id: int, plant_id: int, zone: str, now: datetime
) -> WateredResult | None:
    """None when the reminder is no longer active (already confirmed, deleted, or not theirs)."""
    plant = await repo.get_plant(chat_id, plant_id)
    if plant is None:
        return None
    if not await repo.delete_reminder(plant_id):
        return None
    today = local_date(zone, now)
    await repo.mark_watered(plant_id, today)
    updated = replace(plant, last_watered_on=today)
    return WateredResult(updated, next_due_on(updated, zone))
