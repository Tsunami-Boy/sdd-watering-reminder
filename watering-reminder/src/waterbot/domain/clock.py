"""Time source. Domain functions receive `now` as a parameter; only callers read a clock."""

from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class OffsetClock:
    """System clock shifted by a number of hours; lets manual checks skip waiting for 08:00."""

    def __init__(self, hours: float) -> None:
        self._offset = timedelta(hours=hours)

    def now(self) -> datetime:
        return datetime.now(UTC) + self._offset


def clock_from_offset(hours: float) -> Clock:
    return OffsetClock(hours) if hours else SystemClock()
