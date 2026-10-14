"""Time zone picker: regions, pages of zones and callback encoding."""

from dataclasses import dataclass

from waterbot.domain.zones import canonical_zone, selectable_zones

PAGE_SIZE = 10

# key -> (label shown to the user, IANA prefixes that belong to the region)
REGIONS: dict[str, tuple[str, tuple[str, ...]]] = {
    "am": ("América", ("America",)),
    "eu": ("Europa", ("Europe",)),
    "as": ("Asia", ("Asia",)),
    "af": ("África", ("Africa",)),
    "oc": ("Oceanía", ("Australia", "Pacific")),
    "at": ("Atlántico / Índico / Ártico", ("Atlantic", "Indian", "Arctic")),
    "an": ("Antártida", ("Antarctica",)),
}


@dataclass(frozen=True)
class Page:
    zones: list[str]
    page: int
    has_prev: bool
    has_next: bool


def zones_in_region(region: str) -> list[str]:
    prefixes = REGIONS[region][1]
    return [z for z in selectable_zones() if z.split("/", 1)[0] in prefixes]


def zones_page(region: str, page: int) -> Page:
    zones = zones_in_region(region)
    last = max(0, (len(zones) - 1) // PAGE_SIZE)
    page = min(max(page, 0), last)
    chunk = zones[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]
    return Page(chunk, page, has_prev=page > 0, has_next=page < last)


def zone_label(zone: str) -> str:
    return zone.split("/", 1)[1].replace("_", " ")


def validate_zone(text: str) -> str | None:
    """Canonical zone name if `text` is a selectable zone, else None."""
    return canonical_zone(text)


# Callback data (Telegram limit: 64 bytes) --------------------------------------------------


def region_callback(region: str) -> str:
    return f"tz:r:{region}"


def page_callback(region: str, page: int) -> str:
    return f"tz:p:{region}:{page}"


def zone_callback(zone: str) -> str:
    return f"tz:s:{zone}"


BACK_CALLBACK = "tz:b"
