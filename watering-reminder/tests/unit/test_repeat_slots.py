from datetime import date, time
from zoneinfo import ZoneInfo

from waterbot.domain.schedule import in_send_window, local_slot_to_utc, next_send_slot

MADRID = "Europe/Madrid"


def at(day: date, hour: int, minute: int = 0):
    return local_slot_to_utc(day, time(hour, minute), MADRID)


def local(dt):
    return dt.astimezone(ZoneInfo(MADRID))


def test_full_day_sequence():
    d = date(2026, 1, 17)
    chain = [at(d, 8)]
    for _ in range(4):
        chain.append(next_send_slot(MADRID, chain[-1]))
    assert [local(c).strftime("%d %H:%M") for c in chain] == [
        "17 08:00",
        "17 12:00",
        "17 16:00",
        "17 20:00",
        "18 08:00",
    ]


def test_late_send_is_not_followed_by_a_burst():
    late = at(date(2026, 1, 17), 13, 10)
    assert next_send_slot(MADRID, late) == at(date(2026, 1, 17), 16)


def test_window_excludes_night():
    d = date(2026, 1, 17)
    assert in_send_window(MADRID, at(d, 8))
    assert in_send_window(MADRID, at(d, 21, 59))
    assert not in_send_window(MADRID, at(d, 22))
    assert not in_send_window(MADRID, at(d, 3))
