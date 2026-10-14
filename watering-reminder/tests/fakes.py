"""Test doubles: controllable clock, recording notifier and an in-memory repository."""

from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta

from waterbot.domain.models import DueReminder, Plant, Reminder, User
from waterbot.storage.interface import DuplicatePlantName


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def set(self, now: datetime) -> None:
        self._now = now

    def advance(self, **kwargs: float) -> None:
        self._now += timedelta(**kwargs)


@dataclass
class Sent:
    chat_id: int
    plant_name: str
    plant_type: str
    plant_id: int
    repeat: bool


class FakeNotifier:
    def __init__(self) -> None:
        self.sent: list[Sent] = []
        self.fail_next = 0
        self._next_id = 1000

    async def send_reminder(
        self, chat_id: int, plant_name: str, plant_type: str, plant_id: int, repeat: bool
    ) -> int:
        if self.fail_next:
            self.fail_next -= 1
            raise RuntimeError("telegram unavailable")
        self.sent.append(Sent(chat_id, plant_name, plant_type, plant_id, repeat))
        self._next_id += 1
        return self._next_id


class FakeRepository:
    """Same behaviour as PostgresRepository, including constraints and claim leases."""

    def __init__(self) -> None:
        self.users: dict[int, User] = {}
        self.plants: dict[int, Plant] = {}
        self.reminders: dict[int, Reminder] = {}
        self._next_plant_id = 1
        self.healthy = True

    async def ensure_user(self, chat_id: int, now: datetime) -> User:
        return self.users.setdefault(chat_id, User(chat_id, None, now))

    async def get_user(self, chat_id: int) -> User | None:
        return self.users.get(chat_id)

    async def set_timezone(self, chat_id: int, zone: str) -> None:
        self.users[chat_id] = replace(self.users[chat_id], timezone=zone)

    async def add_plant(
        self, chat_id, name, plant_type, summer_days, winter_days, last_watered_on, now
    ) -> Plant:
        if not 1 <= len(name.strip()) <= 40 or not 1 <= len(plant_type.strip()) <= 60:
            raise ValueError("check constraint")
        if not (1 <= summer_days <= 365 and 1 <= winter_days <= 365):
            raise ValueError("check constraint")
        if any(
            p.chat_id == chat_id and p.name.lower() == name.lower() for p in self.plants.values()
        ):
            raise DuplicatePlantName(name)
        plant = Plant(
            self._next_plant_id,
            chat_id,
            name,
            plant_type,
            summer_days,
            winter_days,
            last_watered_on,
            now,
        )
        self._next_plant_id += 1
        self.plants[plant.id] = plant
        return plant

    async def list_plants(self, chat_id: int) -> list[Plant]:
        found = [p for p in self.plants.values() if p.chat_id == chat_id]
        return sorted(found, key=lambda p: p.name.lower())

    async def get_plant(self, chat_id: int, plant_id: int) -> Plant | None:
        plant = self.plants.get(plant_id)
        return plant if plant and plant.chat_id == chat_id else None

    async def delete_plant(self, chat_id: int, plant_id: int) -> bool:
        if await self.get_plant(chat_id, plant_id) is None:
            return False
        del self.plants[plant_id]
        self.reminders.pop(plant_id, None)
        return True

    async def mark_watered(self, plant_id: int, on: date) -> None:
        self.plants[plant_id] = replace(self.plants[plant_id], last_watered_on=on)

    async def plants_without_reminder(self) -> list[tuple[Plant, User]]:
        return [
            (p, self.users[p.chat_id])
            for p in self.plants.values()
            if self.users[p.chat_id].timezone and p.id not in self.reminders
        ]

    async def create_reminder(self, plant_id: int, due_on: date, next_send_at: datetime) -> bool:
        if plant_id in self.reminders:
            return False
        self.reminders[plant_id] = Reminder(plant_id, due_on, next_send_at, None, 0, None)
        return True

    async def claim_due_reminders(self, now: datetime, lease_seconds: int) -> list[DueReminder]:
        claimed = []
        for rem in sorted(self.reminders.values(), key=lambda r: r.next_send_at):
            if rem.next_send_at <= now:
                self.reminders[rem.plant_id] = replace(
                    rem, next_send_at=now + timedelta(seconds=lease_seconds)
                )
                plant = self.plants[rem.plant_id]
                claimed.append(DueReminder(rem, plant, self.users[plant.chat_id]))
        return claimed

    async def record_sent(self, plant_id, sent_at, next_send_at, message_id) -> None:
        rem = self.reminders[plant_id]
        self.reminders[plant_id] = replace(
            rem,
            last_sent_at=sent_at,
            next_send_at=next_send_at,
            message_id=message_id,
            send_count=rem.send_count + 1,
        )

    async def get_reminder(self, plant_id: int) -> Reminder | None:
        return self.reminders.get(plant_id)

    async def delete_reminder(self, plant_id: int) -> bool:
        return self.reminders.pop(plant_id, None) is not None

    async def reminders_for_user(self, chat_id: int) -> list[Reminder]:
        return [r for r in self.reminders.values() if self.plants[r.plant_id].chat_id == chat_id]

    async def set_next_send_at(self, plant_id: int, when: datetime) -> None:
        self.reminders[plant_id] = replace(self.reminders[plant_id], next_send_at=when)

    async def health_check(self) -> bool:
        return self.healthy


def utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)
