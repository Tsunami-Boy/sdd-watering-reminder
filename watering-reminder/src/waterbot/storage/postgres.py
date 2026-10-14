"""PostgreSQL implementation (psycopg 3, one short-lived connection per operation).

Short-lived connections suit the free managed database, which closes idle connections.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, datetime
from importlib import resources

import psycopg

from waterbot.domain.models import DueReminder, Plant, Reminder, User
from waterbot.storage.interface import DuplicatePlantName

log = logging.getLogger(__name__)

_PLANT_COLS = "p.id, p.chat_id, p.name, p.plant_type, p.summer_days, p.winter_days, "
_PLANT_COLS += "p.last_watered_on, p.created_at"
_REMINDER_COLS = "r.plant_id, r.due_on, r.next_send_at, r.last_sent_at, r.send_count, r.message_id"


def _user(row) -> User:
    return User(chat_id=row[0], timezone=row[1], created_at=row[2])


def _plant(row) -> Plant:
    return Plant(*row[:8])


def _reminder(row) -> Reminder:
    return Reminder(*row[:6])


class PostgresRepository:
    def __init__(self, dsn: str, connect_timeout: int = 10) -> None:
        self._dsn = dsn
        self._connect_timeout = connect_timeout

    @asynccontextmanager
    async def _conn(self) -> AsyncIterator[psycopg.AsyncConnection]:
        conn = await psycopg.AsyncConnection.connect(
            self._dsn, connect_timeout=self._connect_timeout, options="-c timezone=UTC"
        )
        try:
            async with conn:  # commits on success, rolls back on error, then closes
                yield conn
        finally:
            await conn.close()

    async def apply_schema(self) -> None:
        schema = resources.files("waterbot.storage").joinpath("schema.sql").read_text("utf-8")
        async with self._conn() as conn:
            await conn.execute(schema)

    async def health_check(self) -> bool:
        try:
            async with self._conn() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception:
            log.exception("database health check failed")
            return False

    # users ------------------------------------------------------------------------------

    async def ensure_user(self, chat_id: int, now: datetime) -> User:
        async with self._conn() as conn:
            await conn.execute(
                "INSERT INTO users (chat_id, created_at) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (chat_id, now),
            )
            cur = await conn.execute(
                "SELECT chat_id, timezone, created_at FROM users WHERE chat_id = %s", (chat_id,)
            )
            return _user(await cur.fetchone())

    async def get_user(self, chat_id: int) -> User | None:
        async with self._conn() as conn:
            cur = await conn.execute(
                "SELECT chat_id, timezone, created_at FROM users WHERE chat_id = %s", (chat_id,)
            )
            row = await cur.fetchone()
            return _user(row) if row else None

    async def set_timezone(self, chat_id: int, zone: str) -> None:
        async with self._conn() as conn:
            await conn.execute("UPDATE users SET timezone = %s WHERE chat_id = %s", (zone, chat_id))

    # plants -----------------------------------------------------------------------------

    async def add_plant(
        self,
        chat_id: int,
        name: str,
        plant_type: str,
        summer_days: int,
        winter_days: int,
        last_watered_on: date,
        now: datetime,
    ) -> Plant:
        try:
            async with self._conn() as conn:
                cur = await conn.execute(
                    "INSERT INTO plants (chat_id, name, plant_type, summer_days, winter_days,"
                    " last_watered_on, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                    " RETURNING id, chat_id, name, plant_type, summer_days, winter_days,"
                    " last_watered_on, created_at",
                    (chat_id, name, plant_type, summer_days, winter_days, last_watered_on, now),
                )
                return _plant(await cur.fetchone())
        except psycopg.errors.UniqueViolation as exc:
            raise DuplicatePlantName(name) from exc

    async def list_plants(self, chat_id: int) -> list[Plant]:
        async with self._conn() as conn:
            cur = await conn.execute(
                f"SELECT {_PLANT_COLS} FROM plants p WHERE p.chat_id = %s ORDER BY lower(p.name)",
                (chat_id,),
            )
            return [_plant(r) for r in await cur.fetchall()]

    async def get_plant(self, chat_id: int, plant_id: int) -> Plant | None:
        async with self._conn() as conn:
            cur = await conn.execute(
                f"SELECT {_PLANT_COLS} FROM plants p WHERE p.id = %s AND p.chat_id = %s",
                (plant_id, chat_id),
            )
            row = await cur.fetchone()
            return _plant(row) if row else None

    async def delete_plant(self, chat_id: int, plant_id: int) -> bool:
        async with self._conn() as conn:
            cur = await conn.execute(
                "DELETE FROM plants WHERE id = %s AND chat_id = %s", (plant_id, chat_id)
            )
            return cur.rowcount > 0

    async def mark_watered(self, plant_id: int, on: date) -> None:
        async with self._conn() as conn:
            await conn.execute(
                "UPDATE plants SET last_watered_on = %s WHERE id = %s", (on, plant_id)
            )

    # reminders --------------------------------------------------------------------------

    async def plants_without_reminder(self) -> list[tuple[Plant, User]]:
        async with self._conn() as conn:
            cur = await conn.execute(
                f"SELECT {_PLANT_COLS}, u.chat_id, u.timezone, u.created_at"
                " FROM plants p JOIN users u ON u.chat_id = p.chat_id"
                " WHERE u.timezone IS NOT NULL"
                " AND NOT EXISTS (SELECT 1 FROM reminders r WHERE r.plant_id = p.id)"
                " ORDER BY p.id"
            )
            return [(_plant(r[:8]), _user(r[8:11])) for r in await cur.fetchall()]

    async def create_reminder(self, plant_id: int, due_on: date, next_send_at: datetime) -> bool:
        async with self._conn() as conn:
            cur = await conn.execute(
                "INSERT INTO reminders (plant_id, due_on, next_send_at) VALUES (%s, %s, %s)"
                " ON CONFLICT DO NOTHING",
                (plant_id, due_on, next_send_at),
            )
            return cur.rowcount > 0

    async def claim_due_reminders(self, now: datetime, lease_seconds: int) -> list[DueReminder]:
        async with self._conn() as conn:
            cur = await conn.execute(
                "WITH due AS ("
                "  SELECT plant_id FROM reminders WHERE next_send_at <= %(now)s"
                "  ORDER BY next_send_at FOR UPDATE SKIP LOCKED),"
                " claimed AS ("
                "  UPDATE reminders r"
                "  SET next_send_at = %(now)s + make_interval(secs => %(lease)s)"
                "  FROM due WHERE r.plant_id = due.plant_id"
                f" RETURNING {_REMINDER_COLS})"
                f" SELECT {_REMINDER_COLS.replace('r.', 'claimed.')}, {_PLANT_COLS},"
                " u.chat_id, u.timezone, u.created_at"
                " FROM claimed JOIN plants p ON p.id = claimed.plant_id"
                " JOIN users u ON u.chat_id = p.chat_id ORDER BY claimed.due_on, p.id",
                {"now": now, "lease": lease_seconds},
            )
            return [
                DueReminder(_reminder(r[:6]), _plant(r[6:14]), _user(r[14:17]))
                for r in await cur.fetchall()
            ]

    async def record_sent(
        self, plant_id: int, sent_at: datetime, next_send_at: datetime, message_id: int | None
    ) -> None:
        async with self._conn() as conn:
            await conn.execute(
                "UPDATE reminders SET last_sent_at = %s, next_send_at = %s, message_id = %s,"
                " send_count = send_count + 1 WHERE plant_id = %s",
                (sent_at, next_send_at, message_id, plant_id),
            )

    async def get_reminder(self, plant_id: int) -> Reminder | None:
        async with self._conn() as conn:
            cur = await conn.execute(
                f"SELECT {_REMINDER_COLS} FROM reminders r WHERE r.plant_id = %s", (plant_id,)
            )
            row = await cur.fetchone()
            return _reminder(row) if row else None

    async def delete_reminder(self, plant_id: int) -> bool:
        async with self._conn() as conn:
            cur = await conn.execute("DELETE FROM reminders WHERE plant_id = %s", (plant_id,))
            return cur.rowcount > 0

    async def reminders_for_user(self, chat_id: int) -> list[Reminder]:
        async with self._conn() as conn:
            cur = await conn.execute(
                f"SELECT {_REMINDER_COLS} FROM reminders r JOIN plants p ON p.id = r.plant_id"
                " WHERE p.chat_id = %s",
                (chat_id,),
            )
            return [_reminder(r) for r in await cur.fetchall()]

    async def set_next_send_at(self, plant_id: int, when: datetime) -> None:
        async with self._conn() as conn:
            await conn.execute(
                "UPDATE reminders SET next_send_at = %s WHERE plant_id = %s", (when, plant_id)
            )
