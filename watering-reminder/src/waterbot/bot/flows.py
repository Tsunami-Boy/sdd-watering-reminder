"""Conversation logic, independent of the Telegram library so it can be tested directly.

Handlers translate Telegram updates into calls on `BotService` and render the `Reply`
objects it returns.
"""

import logging
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

from waterbot.bot import messages, timezones
from waterbot.domain import plants as plant_rules
from waterbot.domain.clock import Clock
from waterbot.domain.models import Plant
from waterbot.domain.schedule import local_date, next_due_on
from waterbot.domain.seasons import season_at
from waterbot.services import change_timezone, confirm_watering
from waterbot.storage.interface import DuplicatePlantName, Repository

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Button:
    text: str
    data: str


@dataclass(frozen=True)
class Reply:
    text: str
    buttons: list[list[Button]] = field(default_factory=list)
    edit: bool = False  # edit the message the callback came from instead of sending a new one
    alert: str | None = None  # short popup answering a callback


@dataclass
class _Registration:
    step: str = "name"
    name: str = ""
    plant_type: str = ""
    summer_days: int = 0


class BotService:
    def __init__(self, repo: Repository, clock: Clock) -> None:
        self._repo = repo
        self._clock = clock
        self._registrations: dict[int, _Registration] = {}

    # commands ---------------------------------------------------------------------------

    async def start(self, chat_id: int) -> Reply:
        await self._repo.ensure_user(chat_id, self._clock.now())
        return Reply(messages.welcome())

    async def zona(self, chat_id: int) -> Reply:
        await self._repo.ensure_user(chat_id, self._clock.now())
        self._registrations.pop(chat_id, None)
        return self._regions_reply()

    async def agregar(self, chat_id: int) -> Reply:
        user = await self._repo.ensure_user(chat_id, self._clock.now())
        if not user.timezone:
            return Reply(messages.NEED_TIMEZONE)
        self._registrations[chat_id] = _Registration()
        return Reply(messages.ASK_NAME)

    async def plantas(self, chat_id: int) -> Reply:
        user = await self._repo.get_user(chat_id)
        plants = await self._repo.list_plants(chat_id)
        if not plants or user is None or not user.timezone:
            return Reply(messages.NO_PLANTS)
        lines = [messages.plant_line(p, next_due_on(p, user.timezone)) for p in plants]
        return Reply("\n\n".join(lines))

    async def eliminar(self, chat_id: int) -> Reply:
        plants = await self._repo.list_plants(chat_id)
        if not plants:
            return Reply(messages.NO_PLANTS)
        buttons = [[Button(p.name, f"del:{p.id}")] for p in plants]
        return Reply(messages.DELETE_CHOOSE, buttons)

    async def cancelar(self, chat_id: int) -> Reply:
        if self._registrations.pop(chat_id, None) is None:
            return Reply(messages.NOTHING_TO_CANCEL)
        return Reply(messages.CANCELLED)

    # free text --------------------------------------------------------------------------

    async def text(self, chat_id: int, text: str) -> Reply:
        registration = self._registrations.get(chat_id)
        if registration is not None:
            return await self._registration_step(chat_id, registration, text)
        zone = timezones.validate_zone(text)
        if zone is not None:
            return await self._save_zone(chat_id, zone)
        if "/" in text and " " not in text.strip():
            return Reply(messages.ZONA_INVALID)  # looked like a zone name, but is not one
        return Reply(messages.HELP)

    # inline buttons ---------------------------------------------------------------------

    async def callback(self, chat_id: int, data: str) -> Reply:
        kind, _, rest = data.partition(":")
        if kind == "tz":
            return await self._timezone_callback(chat_id, rest)
        if kind == "water":
            return await self._water_callback(chat_id, rest)
        if kind == "del":
            return await self._delete_ask(chat_id, rest)
        if kind == "delok":
            return await self._delete_confirm(chat_id, rest)
        if kind == "delno":
            return Reply(messages.DELETE_CANCELLED, edit=True)
        return Reply(messages.HELP, alert=messages.HELP)

    # time zone --------------------------------------------------------------------------

    def _regions_reply(self, edit: bool = False) -> Reply:
        regions = list(timezones.REGIONS.items())
        rows = [
            [
                Button(label, timezones.region_callback(key))
                for key, (label, _) in regions[i : i + 2]
            ]
            for i in range(0, len(regions), 2)
        ]
        return Reply(messages.ZONA_CHOOSE_REGION, rows, edit=edit)

    def _zones_reply(self, region: str, page_number: int) -> Reply:
        page = timezones.zones_page(region, page_number)
        rows = [[Button(timezones.zone_label(z), timezones.zone_callback(z))] for z in page.zones]
        nav = []
        if page.has_prev:
            nav.append(Button("◀", timezones.page_callback(region, page.page - 1)))
        if page.has_next:
            nav.append(Button("▶", timezones.page_callback(region, page.page + 1)))
        rows.append(nav + [Button("⬅ Regiones", timezones.BACK_CALLBACK)])
        return Reply(messages.ZONA_CHOOSE_ZONE, rows, edit=True)

    async def _timezone_callback(self, chat_id: int, rest: str) -> Reply:
        action, _, arg = rest.partition(":")
        if action == "b":
            return self._regions_reply(edit=True)
        if action == "r" and arg in timezones.REGIONS:
            return self._zones_reply(arg, 0)
        if action == "p":
            region, _, page = arg.partition(":")
            if region in timezones.REGIONS and page.isdigit():
                return self._zones_reply(region, int(page))
        if action == "s":
            zone = timezones.validate_zone(arg)
            if zone is not None:
                reply = await self._save_zone(chat_id, zone)
                return Reply(reply.text, edit=True)
        return Reply(messages.ZONA_INVALID, alert=messages.ZONA_INVALID)

    async def _save_zone(self, chat_id: int, zone: str) -> Reply:
        now = self._clock.now()
        await self._repo.ensure_user(chat_id, now)
        await change_timezone(self._repo, chat_id, zone, now)
        local_time = now.astimezone(ZoneInfo(zone)).strftime("%H:%M")
        return Reply(messages.zona_saved(zone, local_time, season_at(zone, now)))

    # plant registration -----------------------------------------------------------------

    async def _registration_step(self, chat_id: int, reg: _Registration, text: str) -> Reply:
        try:
            if reg.step == "name":
                reg.name = plant_rules.validate_name(text)
                if await self._name_taken(chat_id, reg.name):
                    return Reply(messages.NAME_TAKEN)
                reg.step = "type"
                return Reply(messages.ASK_TYPE)
            if reg.step == "type":
                reg.plant_type = plant_rules.validate_type(text)
                reg.step = "summer"
                return Reply(messages.ASK_SUMMER)
            if reg.step == "summer":
                reg.summer_days = plant_rules.parse_interval(text)
                reg.step = "winter"
                return Reply(messages.ASK_WINTER)
            winter_days = plant_rules.parse_interval(text)
        except plant_rules.ValidationError as exc:
            return Reply(str(exc))
        return await self._finish_registration(chat_id, reg, winter_days)

    async def _name_taken(self, chat_id: int, name: str) -> bool:
        wanted = name.lower()
        return any(p.name.lower() == wanted for p in await self._repo.list_plants(chat_id))

    async def _finish_registration(self, chat_id: int, reg: _Registration, winter: int) -> Reply:
        user = await self._repo.get_user(chat_id)
        if user is None or not user.timezone:
            self._registrations.pop(chat_id, None)
            return Reply(messages.NEED_TIMEZONE)
        now = self._clock.now()
        try:
            plant = await self._repo.add_plant(
                chat_id,
                reg.name,
                reg.plant_type,
                reg.summer_days,
                winter,
                local_date(user.timezone, now),
                now,
            )
        except DuplicatePlantName:
            reg.step = "name"
            return Reply(messages.NAME_TAKEN)
        self._registrations.pop(chat_id, None)
        return Reply(messages.plant_saved(plant, next_due_on(plant, user.timezone)))

    # watering confirmation and deletion -------------------------------------------------

    async def _water_callback(self, chat_id: int, raw_id: str) -> Reply:
        user = await self._repo.get_user(chat_id)
        if not raw_id.isdigit() or user is None or not user.timezone:
            return Reply(messages.REMINDER_INACTIVE, alert=messages.REMINDER_INACTIVE)
        result = await confirm_watering(
            self._repo, chat_id, int(raw_id), user.timezone, self._clock.now()
        )
        if result is None:
            return Reply(messages.REMINDER_INACTIVE, alert=messages.REMINDER_INACTIVE)
        return Reply(messages.watered(result.next_due), edit=True)

    async def _own_plant(self, chat_id: int, raw_id: str) -> Plant | None:
        if not raw_id.isdigit():
            return None
        return await self._repo.get_plant(chat_id, int(raw_id))

    async def _delete_ask(self, chat_id: int, raw_id: str) -> Reply:
        plant = await self._own_plant(chat_id, raw_id)
        if plant is None:
            return Reply(messages.PLANT_GONE, edit=True)
        buttons = [[Button("Sí", f"delok:{plant.id}"), Button("No", "delno")]]
        return Reply(messages.delete_ask(plant.name), buttons, edit=True)

    async def _delete_confirm(self, chat_id: int, raw_id: str) -> Reply:
        plant = await self._own_plant(chat_id, raw_id)
        if plant is None or not await self._repo.delete_plant(chat_id, plant.id):
            return Reply(messages.PLANT_GONE, edit=True)
        return Reply(messages.deleted(plant.name), edit=True)
