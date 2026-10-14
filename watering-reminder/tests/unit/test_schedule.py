from datetime import date, time
from zoneinfo import ZoneInfo

import pytest

from tests.fakes import utc
from waterbot.domain.models import Plant
from waterbot.domain.schedule import (
    is_due,
    local_slot_to_utc,
    next_allowed_send,
    next_due_on,
    next_send_slot,
)

SANTIAGO = "America/Santiago"
MADRID = "Europe/Madrid"


def plant(last: date, summer=7, winter=14) -> Plant:
    return Plant(1, 1, "Catalina", "Dólar", summer, winter, last, utc(2026, 1, 1))


def test_next_due_uses_the_season_of_the_watering_day():
    # Santiago, south: January is summer (7 days), June is winter (14 days).
    assert next_due_on(plant(date(2026, 1, 10)), SANTIAGO) == date(2026, 1, 17)
    assert next_due_on(plant(date(2026, 6, 10)), SANTIAGO) == date(2026, 6, 24)
    # Madrid, north: the same dates give the opposite intervals.
    assert next_due_on(plant(date(2026, 1, 10)), MADRID) == date(2026, 1, 24)
    assert next_due_on(plant(date(2026, 6, 10)), MADRID) == date(2026, 6, 17)


def test_interval_is_chosen_on_the_watering_day_not_the_due_day():
    # Watered on 28 Mar (south summer, 7 days): due 4 Apr even though April is winter.
    assert next_due_on(plant(date(2026, 3, 28)), SANTIAGO) == date(2026, 4, 4)


@pytest.mark.parametrize(
    "zone,expected_utc",
    [
        ("America/Santiago", utc(2026, 1, 15, 11, 0)),  # UTC-3 in January (summer time)
        ("Europe/Madrid", utc(2026, 1, 15, 7, 0)),  # UTC+1
        ("Asia/Kolkata", utc(2026, 1, 15, 2, 30)),  # UTC+5:30
        ("Australia/Lord_Howe", utc(2026, 1, 14, 21, 0)),  # UTC+11 in January
    ],
)
def test_local_slot_to_utc(zone, expected_utc):
    assert local_slot_to_utc(date(2026, 1, 15), time(8, 0), zone) == expected_utc


def test_same_plant_has_different_utc_time_in_different_zones():
    d = date(2026, 3, 1)
    assert local_slot_to_utc(d, time(8), SANTIAGO) != local_slot_to_utc(d, time(8), MADRID)


def test_dst_transition_days_keep_local_eight():
    # Madrid switches to summer time on 2026-03-29; 08:00 local is 06:00 UTC afterwards.
    assert local_slot_to_utc(date(2026, 3, 28), time(8), MADRID) == utc(2026, 3, 28, 7)
    assert local_slot_to_utc(date(2026, 3, 29), time(8), MADRID) == utc(2026, 3, 29, 6)
    assert local_slot_to_utc(date(2026, 3, 30), time(8), MADRID) == utc(2026, 3, 30, 6)


def test_not_due_before_eight_local_on_the_due_day():
    p = plant(date(2026, 1, 10))  # Santiago summer: due 17 Jan; 08:00 local = 11:00 UTC
    assert not is_due(p, SANTIAGO, utc(2026, 1, 17, 10, 59))
    assert is_due(p, SANTIAGO, utc(2026, 1, 17, 11, 0))
    assert is_due(p, SANTIAGO, utc(2026, 1, 20, 3, 0))  # overdue stays due


def test_next_allowed_send_window():
    # Santiago summer = UTC-3.
    inside = utc(2026, 1, 17, 15, 0)  # 12:00 local
    assert next_allowed_send(SANTIAGO, inside) == inside
    night = utc(2026, 1, 18, 2, 30)  # 23:30 local on the 17th -> 08:00 on the 18th
    assert next_allowed_send(SANTIAGO, night) == utc(2026, 1, 18, 11, 0)
    early = utc(2026, 1, 17, 8, 0)  # 05:00 local -> 08:00 same day
    assert next_allowed_send(SANTIAGO, early) == utc(2026, 1, 17, 11, 0)


@pytest.mark.parametrize(
    "sent_local_hour,sent_local_minute,expected_local",
    [(8, 0, "12:00"), (12, 0, "16:00"), (16, 0, "20:00"), (13, 10, "16:00"), (8, 5, "12:00")],
)
def test_next_send_slot_same_day(sent_local_hour, sent_local_minute, expected_local):
    sent = local_slot_to_utc(date(2026, 1, 17), time(sent_local_hour, sent_local_minute), MADRID)
    nxt = next_send_slot(MADRID, sent).astimezone(ZoneInfo(MADRID))
    assert nxt.date() == date(2026, 1, 17)
    assert nxt.strftime("%H:%M") == expected_local


def test_after_last_slot_next_is_eight_the_next_day():
    sent = local_slot_to_utc(date(2026, 1, 17), time(20, 0), MADRID)
    assert next_send_slot(MADRID, sent) == local_slot_to_utc(date(2026, 1, 18), time(8), MADRID)


def test_slots_follow_local_wall_clock_across_dst():
    sent = local_slot_to_utc(date(2026, 3, 29), time(8), MADRID)  # DST day
    assert next_send_slot(MADRID, sent) == local_slot_to_utc(date(2026, 3, 29), time(12), MADRID)
