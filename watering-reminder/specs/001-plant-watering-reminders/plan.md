# Implementation Plan: Plant Watering Reminders

**Branch**: `001-plant-watering-reminders` | **Date**: 2026-10-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-plant-watering-reminders/spec.md`

## Summary

A Telegram bot that registers plants with summer/winter watering intervals, derives the season
from a user-selected IANA time zone, and sends a watering reminder at 08:00 local time, repeating
every 4 hours (08:00–20:00) until the user confirms. It runs as a single web service on Render
(free tier) that receives Telegram updates by webhook and exposes a health URL that UptimeRobot
pings every 10 minutes so the instance does not sleep. All state lives in an external managed
PostgreSQL database, and a database-driven scheduler loop (not in-memory jobs) decides which
reminders are due, so restarts and Render redeploys never lose reminders.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: `python-telegram-bot` (async, v21+), `FastAPI` + `uvicorn` (webhook and
health endpoints), `psycopg` 3 (PostgreSQL), `tzdata` + stdlib `zoneinfo` (time zones)

**Storage**: PostgreSQL on an external free managed provider (Neon), accessed through `DATABASE_URL`.
Render's free filesystem is ephemeral, so SQLite on local disk is rejected (see research.md).

**Testing**: `pytest` + `pytest-asyncio`; scheduling logic tested against a fake clock and an
in-memory fake of the storage interface; storage tested against a real PostgreSQL instance

**Target Platform**: Render free Web Service (Linux container, public HTTPS URL)

**Project Type**: single backend service (bot over webhook)

**Performance Goals**: reminders delivered within 5 minutes of their scheduled time; command
replies in under 2 seconds under normal conditions

**Constraints**: free-tier hosting (instance spins down after ~15 min without inbound HTTP traffic;
UptimeRobot every 10 minutes keeps it awake); no local persistent disk; secrets only via
environment variables; a single running instance

**Scale/Scope**: one owner, designed to allow a few dozen users; ~5 commands; 3 tables

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | How the plan satisfies it |
|-----------|--------|---------------------------|
| I. Simplicity First | PASS | One service, one database, one scheduler loop. No queue, no Redis, no ORM, no separate worker. |
| II. Test-First for Reminder Logic | PASS | Pure `domain` module (seasons, due dates, reminder state) with no Telegram or DB imports; Telegram sits behind a `Notifier` interface. |
| III. Reliable Reminders | PASS | Due reminders are rows in PostgreSQL polled each minute; missed ones are sent on recovery; failed sends are retried next tick and logged; explicit IANA zones. |
| IV. Privacy and Secrets | PASS | `BOT_TOKEN`, `WEBHOOK_SECRET`, `DATABASE_URL` only via env vars; webhook verified with Telegram secret token; only chat id, time zone, plant data stored. |
| V. Specification as Source of Truth | PASS | Spec updated for the time zone decision before planning; tasks will trace to FR numbers. |

Post-design re-check: PASS. No complexity violations, so no Complexity Tracking entries.

Technical Constraints check: Python 3.12 + `uv` + `pyproject.toml` locked, Spanish messages. PASS.
The constitution's TODOs (PERSISTENCE, HOSTING) are resolved by this plan: PostgreSQL (Neon) and Render.

## Project Structure

### Documentation (this feature)

```text
specs/001-plant-watering-reminders/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── bot-commands.md
│   └── http-endpoints.md
└── tasks.md             # created later by /speckit-tasks
```

### Source Code (repository root)

```text
pyproject.toml
uv.lock
render.yaml
src/
└── waterbot/
    ├── domain/            # pure logic, no I/O
    │   ├── seasons.py     # hemisphere + season from time zone and date
    │   ├── schedule.py    # next due date, 08:00 local → UTC, 4h repeat window
    │   └── models.py      # User, Plant, Reminder dataclasses
    ├── storage/
    │   ├── interface.py   # Repository protocol
    │   ├── postgres.py    # psycopg implementation
    │   └── schema.sql
    ├── notifier.py        # Notifier protocol + Telegram implementation
    ├── scheduler.py       # tick loop: find due reminders, send, record
    ├── bot/
    │   ├── handlers.py    # /start /zona /agregar /plantas /eliminar /cancelar + callbacks
    │   ├── timezones.py   # time zone picker (regions, pages, validation)
    │   └── messages.py    # Spanish texts
    ├── app.py             # FastAPI app: /webhook/{secret}, /healthz, lifespan
    └── config.py          # env var loading

tests/
├── unit/                  # domain, timezones, messages
├── integration/           # scheduler + repository, handlers with fake notifier
└── contract/              # command and endpoint contracts
```

**Structure Decision**: single Python project. `domain` is isolated so reminder logic is testable
without network or database (Principle II). `storage` and `notifier` are the only I/O boundaries.

## Complexity Tracking

No violations to justify.
