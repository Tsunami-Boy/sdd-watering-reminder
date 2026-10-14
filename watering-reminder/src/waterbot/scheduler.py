"""Database-driven reminder loop. State lives in the database, never in process memory."""

import asyncio
import logging
from datetime import datetime

from waterbot.domain.clock import Clock
from waterbot.domain.schedule import (
    in_send_window,
    is_due,
    next_allowed_send,
    next_due_on,
    next_send_slot,
)
from waterbot.notifier import Notifier
from waterbot.storage.interface import Repository

log = logging.getLogger(__name__)

TICK_SECONDS = 60
LEASE_SECONDS = 120


async def _create_new_reminders(repo: Repository, now: datetime) -> None:
    for plant, user in await repo.plants_without_reminder():
        zone = user.timezone
        if zone and is_due(plant, zone, now):
            due_on = next_due_on(plant, zone)
            await repo.create_reminder(plant.id, due_on, next_allowed_send(zone, now))


async def _send_due_reminders(repo: Repository, notifier: Notifier, now: datetime) -> None:
    for item in await repo.claim_due_reminders(now, LEASE_SECONDS):
        plant, zone = item.plant, item.user.timezone
        if not zone:
            continue
        if not in_send_window(zone, now):
            await repo.set_next_send_at(plant.id, next_allowed_send(zone, now))
            continue
        try:
            message_id = await notifier.send_reminder(
                plant.chat_id,
                plant.name,
                plant.plant_type,
                plant.id,
                repeat=item.reminder.send_count > 0,
            )
        except Exception:
            # The lease on next_send_at expires and the next tick retries.
            log.exception("failed to send reminder plant_id=%s chat_id=%s", plant.id, plant.chat_id)
            continue
        await repo.record_sent(plant.id, now, next_send_slot(zone, now), message_id)


async def tick(repo: Repository, notifier: Notifier, clock: Clock) -> None:
    now = clock.now()
    await _create_new_reminders(repo, now)
    await _send_due_reminders(repo, notifier, now)


async def run_forever(
    repo: Repository, notifier: Notifier, clock: Clock, interval: float = TICK_SECONDS
) -> None:
    while True:
        try:
            await tick(repo, notifier, clock)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("scheduler tick failed")
        await asyncio.sleep(interval)
