"""Pure scheduling rules: when a plant is due and when reminders may be sent.

Send window: messages go out between 08:00 and 22:00 local time. Repeats follow the slots
08:00, 12:00, 16:00 and 20:00; after the last slot the next send is 08:00 the next day.
"""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from waterbot.domain.models import Plant
from waterbot.domain.seasons import Season, season_on

REMINDER_TIME = time(8, 0)
SLOT_HOURS = (8, 12, 16, 20)
WINDOW_START_HOUR = 8
WINDOW_END_HOUR = 22


def local_date(zone: str, now: datetime) -> date:
    return now.astimezone(ZoneInfo(zone)).date()


def interval_days(plant: Plant, season: Season) -> int:
    return plant.summer_days if season == "summer" else plant.winter_days


def next_due_on(plant: Plant, zone: str) -> date:
    """Last watering + the interval of the season in effect on the day it was watered."""
    season = season_on(zone, plant.last_watered_on)
    return plant.last_watered_on + timedelta(days=interval_days(plant, season))


def local_slot_to_utc(day: date, at: time, zone: str) -> datetime:
    return datetime.combine(day, at, tzinfo=ZoneInfo(zone)).astimezone(UTC)


def is_due(plant: Plant, zone: str, now: datetime) -> bool:
    """True once the local clock has reached 08:00 on (or after) the due date."""
    return now >= local_slot_to_utc(next_due_on(plant, zone), REMINDER_TIME, zone)


def in_send_window(zone: str, now: datetime) -> bool:
    hour = now.astimezone(ZoneInfo(zone)).hour
    return WINDOW_START_HOUR <= hour < WINDOW_END_HOUR


def next_allowed_send(zone: str, now: datetime) -> datetime:
    """`now` if inside the send window, otherwise the next 08:00 local."""
    local = now.astimezone(ZoneInfo(zone))
    if in_send_window(zone, now):
        return now
    day = local.date() if local.hour < WINDOW_START_HOUR else local.date() + timedelta(days=1)
    return local_slot_to_utc(day, REMINDER_TIME, zone)


def next_send_slot(zone: str, sent_at: datetime) -> datetime:
    """First slot strictly after `sent_at`, else 08:00 the next local day."""
    local = sent_at.astimezone(ZoneInfo(zone))
    for hour in SLOT_HOURS:
        if local.time() < time(hour):
            return local_slot_to_utc(local.date(), time(hour), zone)
    return local_slot_to_utc(local.date() + timedelta(days=1), REMINDER_TIME, zone)
