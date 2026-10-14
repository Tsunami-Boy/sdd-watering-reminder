"""IANA time zones the user can choose, with the hemisphere of each.

The list comes from `zone.tab` shipped in the `tzdata` package (one canonical zone per row,
with the latitude of its reference location). Latitude sign gives the hemisphere.
"""

from functools import lru_cache
from importlib import resources
from typing import Literal

Hemisphere = Literal["north", "south"]


def _parse_latitude(coordinates: str) -> float:
    """`+4044-07400` / `-3450-05824` / `+404251-0740023` -> signed decimal degrees."""
    split = max(coordinates.rfind("+"), coordinates.rfind("-"))
    lat = coordinates[:split]
    sign = -1 if lat[0] == "-" else 1
    digits = lat[1:]
    degrees, minutes = int(digits[:2]), int(digits[2:4])
    seconds = int(digits[4:6]) if len(digits) >= 6 else 0
    return sign * (degrees + minutes / 60 + seconds / 3600)


@lru_cache(maxsize=1)
def _latitudes() -> dict[str, float]:
    text = resources.files("tzdata.zoneinfo").joinpath("zone.tab").read_text(encoding="utf-8")
    latitudes: dict[str, float] = {}
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        _country, coordinates, zone, *_ = line.split("\t")
        latitudes[zone] = _parse_latitude(coordinates)
    return latitudes


def selectable_zones() -> list[str]:
    return sorted(_latitudes())


def canonical_zone(text: str) -> str | None:
    """Return the canonical spelling of a typed zone name, or None if it is not selectable."""
    wanted = text.strip().replace(" ", "_").lower()
    if not wanted:
        return None
    for zone in _latitudes():
        if zone.lower() == wanted:
            return zone
    return None


def hemisphere_of(zone: str) -> Hemisphere:
    return "south" if _latitudes()[zone] < 0 else "north"
