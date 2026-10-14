"""Summer/winter by hemisphere. Southern summer: Oct-Mar. Northern summer: Apr-Sep."""

from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from waterbot.domain.zones import hemisphere_of

Season = Literal["summer", "winter"]

_SOUTH_SUMMER = {10, 11, 12, 1, 2, 3}
_NORTH_SUMMER = {4, 5, 6, 7, 8, 9}


def season_for_month(zone: str, month: int) -> Season:
    summer = _SOUTH_SUMMER if hemisphere_of(zone) == "south" else _NORTH_SUMMER
    return "summer" if month in summer else "winter"


def season_on(zone: str, local_date: date) -> Season:
    return season_for_month(zone, local_date.month)


def season_at(zone: str, now: datetime) -> Season:
    """Season in effect at the instant `now`, using the month in the user's local time."""
    return season_for_month(zone, now.astimezone(ZoneInfo(zone)).month)
