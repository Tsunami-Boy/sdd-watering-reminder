from datetime import UTC, datetime

import pytest

from waterbot.domain.seasons import season_at, season_on
from waterbot.domain.zones import canonical_zone, hemisphere_of, selectable_zones


@pytest.mark.parametrize(
    "zone,expected",
    [
        ("America/Santiago", "south"),
        ("Australia/Sydney", "south"),
        ("America/Argentina/Buenos_Aires", "south"),
        ("Europe/Madrid", "north"),
        ("America/Mexico_City", "north"),
        ("Asia/Tokyo", "north"),
    ],
)
def test_hemisphere(zone, expected):
    assert hemisphere_of(zone) == expected


def test_opposite_seasons_on_the_same_date():
    now = datetime(2026, 1, 15, 12, tzinfo=UTC)
    assert season_at("America/Santiago", now) == "summer"
    assert season_at("Europe/Madrid", now) == "winter"
    july = datetime(2026, 7, 15, 12, tzinfo=UTC)
    assert season_at("America/Santiago", july) == "winter"
    assert season_at("Europe/Madrid", july) == "summer"


@pytest.mark.parametrize(
    "zone,month,expected",
    [
        ("America/Santiago", 3, "summer"),
        ("America/Santiago", 4, "winter"),
        ("America/Santiago", 9, "winter"),
        ("America/Santiago", 10, "summer"),
        ("Europe/Madrid", 3, "winter"),
        ("Europe/Madrid", 4, "summer"),
        ("Europe/Madrid", 9, "summer"),
        ("Europe/Madrid", 10, "winter"),
    ],
)
def test_month_boundaries(zone, month, expected):
    from datetime import date

    assert season_on(zone, date(2026, month, 15)) == expected


def test_season_uses_the_local_month_near_utc_midnight():
    # 2026-04-01 01:00 UTC is still March 31st (21:00) in Santiago (UTC-4 in April? -03/-04).
    now = datetime(2026, 4, 1, 1, 0, tzinfo=UTC)
    assert season_at("America/Santiago", now) == "summer"  # local date: March 31
    assert season_at("Asia/Tokyo", now) == "summer"  # local date: April 1 10:00 -> north summer
    assert season_at("Europe/London", datetime(2026, 3, 31, 23, 30, tzinfo=UTC)) == "summer"


def test_every_selectable_zone_has_a_hemisphere():
    zones = selectable_zones()
    assert len(zones) > 300
    assert all(hemisphere_of(z) in {"north", "south"} for z in zones)


def test_canonical_zone_accepts_case_and_spaces_and_rejects_garbage():
    assert canonical_zone("america/santiago") == "America/Santiago"
    assert canonical_zone("  Europe/Madrid ") == "Europe/Madrid"
    for bad in ["", "   ", "Nope/Nowhere", "../etc/passwd", "UTC", "US/Eastern"]:
        assert canonical_zone(bad) is None
