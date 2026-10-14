import pytest

from waterbot.bot import timezones
from waterbot.domain.zones import selectable_zones


def test_regions_cover_every_selectable_zone_exactly_once():
    seen = []
    for key in timezones.REGIONS:
        seen += timezones.zones_in_region(key)
    assert sorted(seen) == selectable_zones()


def test_regions_match_research():
    labels = [label for label, _ in timezones.REGIONS.values()]
    assert "América" in labels and "Europa" in labels and "Asia" in labels
    assert "África" in labels and "Oceanía" in labels and "Antártida" in labels


def test_paging():
    first = timezones.zones_page("am", 0)
    assert len(first.zones) <= timezones.PAGE_SIZE
    assert not first.has_prev and first.has_next
    last = timezones.zones_page("am", 10_000)  # clamped to the last page
    assert last.has_prev and not last.has_next
    an = timezones.zones_in_region("an")
    pages = -(-len(an) // timezones.PAGE_SIZE)
    assert timezones.zones_page("an", pages - 1).has_next is False
    assert sum(len(timezones.zones_page("an", i).zones) for i in range(pages)) == len(an)


def test_callback_data_fits_telegram_limit():
    for zone in selectable_zones():
        assert len(timezones.zone_callback(zone).encode()) <= 64
    for key in timezones.REGIONS:
        assert len(timezones.page_callback(key, 99).encode()) <= 64


@pytest.mark.parametrize("text", ["Nope/Nowhere", "", "   ", "../etc", "America/"])
def test_invalid_zones_rejected(text):
    assert timezones.validate_zone(text) is None


def test_valid_zone_accepted():
    assert timezones.validate_zone("America/Santiago") == "America/Santiago"
