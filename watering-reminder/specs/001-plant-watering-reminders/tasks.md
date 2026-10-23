---

description: "Task list for Plant Watering Reminders"
---

# Tasks: Plant Watering Reminders

**Input**: Design documents from `/specs/001-plant-watering-reminders/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: INCLUDED. Constitution Principle II requires tests before implementation for reminder
logic, and the request asks for a test structure. Write each test first and confirm it FAILS
before implementing.

**Organization**: Tasks are grouped by user story so each can be implemented and tested alone.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story the task belongs to (US1–US5)
- Paths are relative to the repository root `watering-reminder/` (single project, see plan.md)

## Where the requested items land

| Requested item | Where |
|----------------|-------|
| Docker with what is needed | Phase 1: T004–T006 |
| DB configuration | Phase 1 (compose database) + Phase 2 (schema, repository) |
| Render | **Files prepared now (T007); actual deploy moved to `specs/002-production-deployment` (was T062–T068)**, because it needs the working bot and a Neon database. Nothing in Phases 1–7 requires Render. |
| Test structure | Phase 1: T009; fakes in Phase 2 (T016) |
| Everything about time zone | Phase 3 (US1) |
| Register plants, verify they are saved | Phase 4 (US2), incl. read-back tests T027–T028 |
| Reminder logic by registered zone | Phase 5 (US3) and Phase 6 (US4) |
| Cover the specifications | US1–US5 map to every spec story; traceability table at the end |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project, Docker and test scaffolding

- [X] T001 Create `pyproject.toml` for package `waterbot` (Python 3.12, `src/` layout) with dependencies `python-telegram-bot>=21`, `fastapi`, `uvicorn`, `psycopg[binary]>=3`, `tzdata`; dev dependencies `pytest`, `pytest-asyncio`, `httpx`, `ruff`; pytest config (`asyncio_mode = "auto"`, `testpaths = ["tests"]`, marker `postgres` for tests that need `TEST_DATABASE_URL`); ruff config
- [X] T002 [P] Create package skeleton with empty `__init__.py` in `src/waterbot/`, `src/waterbot/domain/`, `src/waterbot/storage/`, `src/waterbot/bot/`
- [X] T003 [P] Create `.gitignore` (`.venv/`, `.devbox/`, `.env`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`) and `.env.example` listing `BOT_TOKEN`, `WEBHOOK_SECRET`, `WEBHOOK_SECRET_TOKEN`, `DATABASE_URL`, `TEST_DATABASE_URL`, `RENDER_EXTERNAL_URL`, `PORT`, `RUN_MODE`, `CLOCK_OFFSET_HOURS` with placeholder values only
- [X] T004 [P] Create `Dockerfile`: base `python:3.12-slim`, install `uv`, copy `pyproject.toml` and `uv.lock`, run `uv sync --frozen --no-dev`, copy `src/`, run as non-root user, `CMD` starts `uvicorn waterbot.app:app --host 0.0.0.0 --port ${PORT:-8000}`
- [X] T005 [P] Create `.dockerignore` (`.git`, `.venv`, `.devbox`, `.env`, `tests`, `specs`, `.specify`, `.claude`, `__pycache__`)
- [X] T006 [P] Create `docker-compose.yml` with service `db` (`postgres:16`, volume for data, healthcheck `pg_isready`, exposed on `localhost:5432`, second database for tests created via `POSTGRES_MULTIPLE` init script or a documented `TEST_DATABASE_URL` pointing to a `waterbot_test` database) and service `app` (built from `Dockerfile`, `env_file: .env`, `RUN_MODE=polling`, depends on `db` healthy, port 8000)
- [X] T007 [P] Create `render.yaml` describing one free Web Service (`runtime: docker`, health check path `/healthz`, env var keys from `.env.example` with `sync: false` for secrets). Do NOT deploy yet (see T062)
- [X] T008 Run `uv lock` to generate `uv.lock` and confirm `uv sync` succeeds (depends on T001)
- [X] T009 [P] Create test structure: `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`, `tests/contract/__init__.py`, and `tests/conftest.py` with a `postgres_repo` fixture that reads `TEST_DATABASE_URL`, applies `schema.sql`, truncates tables between tests, and skips tests marked `postgres` when the variable is unset

**Checkpoint**: `uv sync` works, `docker compose config` is valid, `uv run pytest` runs (0 tests) without errors

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Config, data layer, clock, notifier boundary, and the HTTP app. No story starts before this.

**⚠️ CRITICAL**: Complete before any user story.

- [X] T010 [P] Contract tests for HTTP endpoints in `tests/contract/test_http_endpoints.py` per `contracts/http-endpoints.md`: `/healthz` → 200 `{"status":"ok"}` with working repo and 503 `{"status":"degraded"}` when the repo health check fails (also for `HEAD`); `POST /webhook/{wrong_secret}` → 404; correct path with wrong `X-Telegram-Bot-Api-Secret-Token` → 403; correct both → 200
- [X] T011 [P] Implement `src/waterbot/config.py`: load `BOT_TOKEN`, `WEBHOOK_SECRET`, `WEBHOOK_SECRET_TOKEN`, `DATABASE_URL`, `RENDER_EXTERNAL_URL`, `PORT` (default 8000), `RUN_MODE` (`webhook` default, or `polling`), `CLOCK_OFFSET_HOURS` (default 0) from environment only; fail fast with a clear message when a required variable is missing; never log secret values
- [X] T012 [P] Implement `src/waterbot/domain/models.py` dataclasses `User(chat_id, timezone | None, created_at)`, `Plant(id, chat_id, name, plant_type, summer_days, winter_days, last_watered_on, created_at)`, `Reminder(plant_id, due_on, next_send_at, last_sent_at | None, send_count, message_id | None)` per `data-model.md`
- [X] T013 [P] Implement `src/waterbot/domain/clock.py`: `Clock` protocol (`now() -> aware UTC datetime`), `SystemClock`, and an offset clock driven by `CLOCK_OFFSET_HOURS`; domain functions MUST receive `now` as a parameter and never read the system time
- [X] T014 Write `src/waterbot/storage/schema.sql` (idempotent `CREATE TABLE IF NOT EXISTS`), all timestamps `timestamptz` UTC: `users(chat_id bigint primary key, timezone text null, created_at timestamptz)`; `plants(id bigint generated always as identity primary key, chat_id bigint references users on delete cascade, name text, plant_type text, summer_days integer, winter_days integer, last_watered_on date, created_at timestamptz)` with `CHECK (char_length(btrim(name)) BETWEEN 1 AND 40)`, `CHECK (char_length(btrim(plant_type)) BETWEEN 1 AND 60)`, `CHECK (summer_days BETWEEN 1 AND 365)`, `CHECK (winter_days BETWEEN 1 AND 365)` and `UNIQUE INDEX ON (chat_id, lower(name))`; `reminders(plant_id bigint primary key references plants on delete cascade, due_on date, next_send_at timestamptz, last_sent_at timestamptz null, send_count integer, message_id bigint null)`
- [X] T015 Define `src/waterbot/storage/interface.py` `Repository` protocol: `ensure_user`, `get_user`, `set_timezone`, `add_plant`, `list_plants`, `get_plant`, `delete_plant`, `mark_watered`, `plants_needing_reminder(now)`, `create_reminder`, `due_reminders(now)` (row-locking, `FOR UPDATE SKIP LOCKED` semantics), `record_sent`, `get_reminder`, `delete_reminder`, `reschedule_reminders_for_user`, `health_check()`; plus typed errors `DuplicatePlantName`, `PlantNotFound`
- [X] T016 [P] Create `tests/fakes.py`: `FakeClock` (settable time), `FakeNotifier` (records sent messages, can be set to fail N times), `FakeRepository` (in-memory implementation of the T015 protocol with the same constraints: name uniqueness case-insensitive, interval ranges)
- [X] T017 Implement `src/waterbot/storage/postgres.py` `PostgresRepository` with `psycopg` 3: apply `schema.sql` at startup, short-lived connections or a small pool with reconnect on closed connections, `health_check()` running `SELECT 1` with a short timeout (depends on T014, T015)
- [X] T018 [P] Define `src/waterbot/notifier.py` `Notifier` protocol (`send_reminder(chat_id, text, plant_id) -> message_id`, `edit_message(chat_id, message_id, text)`); Telegram implementation is added in US3 (T045)
- [X] T019 [P] Configure structured logging in `src/waterbot/logging_config.py` (INFO default, failures logged with plant id and chat id, never tokens)
- [X] T020 [P] Create `src/waterbot/bot/messages.py` with the Spanish texts used so far: welcome with all commands, generic help, unknown input, "Primero elige tu zona con /zona" (stories add more texts)
- [X] T021 Implement `src/waterbot/app.py` FastAPI app: `GET`/`HEAD /healthz` (200/503 via `repo.health_check()`), `POST /webhook/{secret}` (404 on wrong path secret, 403 on wrong header token, always 200 once handed to the bot, errors logged), lifespan that applies the schema, registers the command menu, calls `setWebhook` with `RENDER_EXTERNAL_URL` and the secret token, and starts/stops the scheduler loop (hook added in T044). Makes T010 pass (depends on T011, T015, T017)
- [X] T022 Implement `src/waterbot/__main__.py` for `RUN_MODE=polling` (local/dev and compose): same handlers and scheduler loop as the app, long polling instead of webhook (depends on T021)

**Checkpoint**: T010 passes; `docker compose up db` + `uv run pytest -m postgres` can connect; app starts and `/healthz` returns 200

---

## Phase 3: User Story 1 - Get started and set my time zone (Priority: P1) 🎯 MVP

**Goal**: `/start` lists commands; `/zona` lets the user pick a valid IANA time zone from a list (or type one) and shows local time and season.

**Independent Test**: Run `/start`, then `/zona`; choose a region and a zone; the bot confirms zone, local time and season and keeps it after a restart. An invalid typed zone is rejected without changing the stored one.

### Tests for User Story 1 ⚠️ (write first, must fail)

- [X] T023 [P] [US1] Unit tests for season/hemisphere in `tests/unit/test_seasons.py`: `America/Santiago` and `Australia/Sydney` are southern (summer Oct–Mar), `Europe/Madrid` and `America/Mexico_City` northern (summer Apr–Sep); the same date gives opposite seasons across hemispheres (SC-006); month boundaries (Mar 31 / Apr 1, Sep 30 / Oct 1) use the **local** month near UTC midnight; every zone offered by the picker has a hemisphere
- [X] T024 [P] [US1] Unit tests for the picker in `tests/unit/test_timezones.py`: regions list matches `research.md`; paging returns ≤ 10 zones per page with correct prev/next flags; callback data ≤ 64 bytes for every zone; `validate_zone("America/Santiago")` is accepted, `"Nope/Nowhere"`, `""` and `"../etc"` are rejected
- [X] T025 [P] [US1] Integration tests for `/start` and `/zona` handlers in `tests/integration/test_zona_flow.py` using `FakeRepository`: welcome lists `/zona /agregar /plantas /eliminar /cancelar`; picking region → page → zone stores the zone and replies with zone, local time, season; typed valid zone stores it; typed invalid zone keeps the previous one; changing zone replaces it
- [X] T026 [P] [US1] Postgres test in `tests/integration/test_users_repo.py` (marker `postgres`): `ensure_user` is idempotent, `set_timezone` persists and is returned by `get_user` from a new repository instance

### Implementation for User Story 1

- [X] T027 [P] [US1] Implement `src/waterbot/domain/seasons.py`: `hemisphere_of(zone_name)`, `season_at(zone_name, now_utc)` returning `"summer"|"winter"` with the rule: Southern summer = October–March, Northern summer = April–September, month taken in the local zone
- [X] T028 [P] [US1] Implement `src/waterbot/bot/timezones.py`: region list (América, Europa, Asia, África, Oceanía, Atlántico/Índico/Pacífico, Antártida) built from `zoneinfo.available_timezones()`, `zones_in_region(region, page)`, `validate_zone(text)`, compact callback encoding (`tz:r:<region>`, `tz:p:<region>:<page>`, `tz:s:<zone>`; index-based if > 64 bytes), and the hemisphere lookup from `zone.tab` in the `tzdata` package. If `zone.tab` is not in the installed package, generate `src/waterbot/domain/zones.json` from the IANA tables and add a test that every selectable zone is present
- [X] T029 [US1] Implement `/start` and `/zona` handlers (plus text fallback for typed zones and unknown input) in `src/waterbot/bot/handlers.py` per `contracts/bot-commands.md`; ignore non-private chats; add the Spanish texts to `messages.py` (depends on T027, T028)
- [X] T030 [US1] Implement `ensure_user`, `get_user`, `set_timezone` in `PostgresRepository` (`src/waterbot/storage/postgres.py`) and register the command menu (`setMyCommands`) at startup in `src/waterbot/app.py`
- [X] T031 [US1] On time zone change, call `reschedule_reminders_for_user` (no-op until US3 adds reminders) from the `/zona` handler in `src/waterbot/bot/handlers.py`

**Checkpoint**: US1 works alone; T023–T026 pass; manual check of scenarios 1, 3, 4 in `quickstart.md`

---

## Phase 4: User Story 2 - Register a plant (Priority: P1)

**Goal**: `/agregar` guides the user through name, type, summer days, winter days, validates them, and **saves the plant so it can be read back**.

**Independent Test**: With a time zone set, run `/agregar` with Catalina / Dólar / 7 / 14; the bot shows a summary; querying the database (or `/plantas` after US5) returns exactly those values; a duplicate name or invalid interval is rejected.

### Tests for User Story 2 ⚠️

- [X] T032 [P] [US2] Unit tests for plant validation in `tests/unit/test_plant_validation.py`: name 1–40 chars after trimming (empty/whitespace rejected, 41 chars rejected), type 1–60 chars, intervals whole numbers 1–365 (`0`, `-3`, `7.5`, `abc`, `366` rejected; `1` and `365` accepted)
- [X] T033 [P] [US2] Postgres tests in `tests/integration/test_plants_repo.py` (marker `postgres`): **read-back after save** — `add_plant` then `get_plant`/`list_plants` from a **new** repository instance returns identical name, type, `summer_days`, `winter_days` and `last_watered_on` equal to the registration local date (FR-013); duplicate name differing only by case raises `DuplicatePlantName`; same name for two different users is allowed; database `CHECK` constraints reject out-of-range values; deleting a user cascades to plants
- [X] T034 [P] [US2] Integration tests for the `/agregar` conversation in `tests/integration/test_agregar_flow.py` with `FakeRepository`: no time zone → "Primero elige tu zona con /zona" and nothing saved; happy path stores the plant and the summary shows the four values and the first reminder date; invalid interval re-asks the same step; duplicate name re-asks the name step; `/cancelar` at each step saves nothing

### Implementation for User Story 2

- [X] T035 [P] [US2] Implement validators in `src/waterbot/domain/plants.py`: `validate_name` (1–40 chars, trimmed), `validate_type` (1–60 chars), `parse_interval` (whole number 1–365) returning Spanish error messages from `messages.py`
- [X] T036 [US2] Implement `add_plant`, `list_plants`, `get_plant` in `PostgresRepository` (`src/waterbot/storage/postgres.py`): `last_watered_on` set to the user's **local** date at registration; map the unique-index violation to `DuplicatePlantName`
- [X] T037 [US2] Implement the `/agregar` `ConversationHandler` and `/cancelar` in `src/waterbot/bot/handlers.py` (steps and prompts exactly as in `contracts/bot-commands.md`); the summary shows name, type, summer days, winter days and the date of the first reminder; add Spanish texts to `messages.py` (depends on T035, T036)

**Checkpoint**: US1 + US2 work; T032–T034 pass; scenarios 2, 5, 6 in `quickstart.md`

---

## Phase 5: User Story 3 - Receive and confirm a watering reminder (Priority: P1)

**Goal**: At 08:00 local time of the user's time zone, a due plant triggers one reminder; tapping `✅ Ya regué` stops it and schedules the next watering using the season in effect that day.

**Independent Test**: Register a plant with a short interval, advance the fake clock to the due day 08:00 in the user's zone, run one scheduler tick, and verify exactly one reminder is sent; confirm it and verify `last_watered_on` is today and the next due date uses the current season's interval.

### Tests for User Story 3 ⚠️ (write first, must fail: Principle II)

- [X] T038 [P] [US3] Unit tests for scheduling in `tests/unit/test_schedule.py`: `next_due_on(last_watered_on, summer_days, winter_days, zone)` uses the interval of the season in effect **on `last_watered_on`** (FR-012); `local_slot_to_utc(date, 08:00, zone)` for `America/Santiago`, `Europe/Madrid`, `Asia/Kolkata` (UTC+5:30) and `Australia/Lord_Howe`; DST transition days produce exactly one 08:00 and it is the local 08:00; the same plant yields different UTC send times for different zones; a reminder is not created before 08:00 local on the due day
- [X] T039 [P] [US3] Integration tests for the scheduler in `tests/integration/test_scheduler.py` using `FakeClock`, `FakeNotifier`, `FakeRepository`: one due plant at 08:00 local → exactly one message; two due plants → two messages, one each; plant not yet due → none; user without time zone → none; a second tick right after sends nothing; failed send leaves the reminder unchanged and the next tick retries (and logs); after "bot offline" at 08:00 and restart at 10:00 the reminder is sent once (FR-014)
- [X] T040 [P] [US3] Integration tests for confirmation in `tests/integration/test_confirm_flow.py`: tapping `water:<plant_id>` deletes the reminder, sets `last_watered_on` to the local today, edits the message to "Regada ✅. Próximo riego: <fecha>"; a second tap answers "Este recordatorio ya no está activo"; a callback from another chat is rejected; confirming 3 days late counts the next interval from the confirmation day; summer→winter boundary uses the winter interval
- [X] T041 [P] [US3] Postgres tests in `tests/integration/test_reminders_repo.py` (marker `postgres`): `create_reminder` is unique per plant; `due_reminders` returns only rows with `next_send_at <= now` and two concurrent transactions never receive the same row (`SKIP LOCKED`); reminders survive a new repository instance (FR-014); deleting the plant removes the reminder

### Implementation for User Story 3

- [X] T042 [P] [US3] Implement `src/waterbot/domain/schedule.py`: `next_due_on`, `local_slot_to_utc`, `is_reminder_due(plant, user_zone, now)`; all pure, `now` passed in (depends on T027)
- [X] T043 [US3] Implement `plants_needing_reminder`, `create_reminder`, `due_reminders`, `record_sent`, `get_reminder`, `delete_reminder`, `mark_watered`, `reschedule_reminders_for_user` in `PostgresRepository` (`src/waterbot/storage/postgres.py`) following the transitions in `data-model.md`
- [X] T044 [US3] Implement `src/waterbot/scheduler.py`: async loop with a 60-second tick (interval configurable for tests) that (1) creates reminders for newly due plants at/after 08:00 local, (2) sends each due reminder through the `Notifier`, (3) calls `record_sent` only after a successful send, logging and keeping the row on failure; wire it into the lifespan in `src/waterbot/app.py` and into `__main__.py` (depends on T042, T043)
- [X] T045 [US3] Implement `TelegramNotifier` in `src/waterbot/notifier.py` (reminder text `💧 Hoy toca regar «<nombre>» (<tipo>)` with a `✅ Ya regué` button, callback data `water:<plant_id>`; `edit_message`) and add reminder/confirmation texts to `messages.py`
- [X] T046 [US3] Implement the `water:<plant_id>` callback handler in `src/waterbot/bot/handlers.py` per `contracts/bot-commands.md` (ownership check, already-confirmed case, message edit, next due date shown)

**Checkpoint**: MVP complete (US1–US3): set zone, register plant, receive and confirm reminders at 08:00 local; T038–T041 pass; scenarios 8 and 10 in `quickstart.md`

---

## Phase 6: User Story 4 - Persistent reminders when I don't confirm (Priority: P2)

**Goal**: An unconfirmed reminder repeats every 4 hours in the window 08:00–20:00 local, then resumes next day at 08:00, one pending reminder per plant.

**Independent Test**: Advance the fake clock from 08:00 to 12:00, 16:00, 20:00 and the next day 08:00 without confirming; verify one new message at each slot and none at night; confirming stops them.

### Tests for User Story 4 ⚠️

- [X] T047 [P] [US4] Unit tests for `next_send_slot(sent_at_utc, zone)` in `tests/unit/test_repeat_slots.py`: 08:00→12:00, 12:00→16:00, 16:00→20:00, 20:00→08:00 next local day; a late send at 13:10 → next slot 16:00 (computed from actual send time, never a burst); DST day slots stay on local wall-clock hours
- [X] T048 [P] [US4] Integration tests in `tests/integration/test_repeat_reminders.py`: unconfirmed → message at 12:00, 16:00, 20:00, none at 22:00/03:00, one at next 08:00; never two pending reminders for the same plant; confirming at 14:00 stops all later messages; deleting the plant stops them; changing time zone recomputes `next_send_at` without a duplicate; bot offline for 6 hours sends **one** message on recovery, not one per missed slot

### Implementation for User Story 4

- [X] T049 [US4] Implement `next_send_slot` in `src/waterbot/domain/schedule.py` (slots 08:00, 12:00, 16:00, 20:00 local) and use it in the scheduler's `record_sent` step in `src/waterbot/scheduler.py`
- [X] T050 [US4] Implement `reschedule_reminders_for_user` logic in `src/waterbot/storage/postgres.py` and `FakeRepository` so a time zone change recomputes `next_send_at` for pending reminders; prefix repeated messages with `Recordatorio:` in `src/waterbot/notifier.py` when `send_count > 0`

**Checkpoint**: T047–T048 pass; scenario 9 in `quickstart.md`

---

## Phase 7: User Story 5 - See and delete my plants (Priority: P2)

**Goal**: `/plantas` lists plants with their data and next watering date; `/eliminar` removes a plant after confirmation and stops its reminders.

**Independent Test**: Register two plants; `/plantas` shows both; delete one via `/eliminar` → it disappears from the list and its pending reminder stops.

### Tests for User Story 5 ⚠️

- [X] T051 [P] [US5] Integration tests in `tests/integration/test_list_delete.py` with `FakeRepository`: `/plantas` shows name, type, summer days, winter days and next date for each plant; with no plants shows the "usa /agregar" message; `/eliminar` shows one button per plant, "Sí" deletes, "No" keeps; deleting a plant with a pending reminder removes the reminder; deleting a plant that no longer exists answers gracefully
- [X] T052 [P] [US5] Postgres test in `tests/integration/test_delete_repo.py` (marker `postgres`): `delete_plant` removes the plant and cascades to its reminder, and does not affect other users' plants (FR-015)

### Implementation for User Story 5

- [X] T053 [US5] Implement `delete_plant` in `PostgresRepository` (`src/waterbot/storage/postgres.py`), scoped by `chat_id`
- [X] T054 [US5] Implement `/plantas` and the `/eliminar` conversation (inline buttons, Sí/No confirmation) in `src/waterbot/bot/handlers.py` per `contracts/bot-commands.md`; add Spanish texts to `messages.py`

**Checkpoint**: all five stories work; scenario 7 and 11 in `quickstart.md`

---

## Phase 8: Polish, Docker run and Render deploy

> `[~]` = moved out of this feature. T059 and T062–T068 are now tracked in `specs/002-production-deployment`; this feature is closed once that one is verified.

**Purpose**: Cross-cutting checks, containerized run, and production deployment (deferred until now)

- [X] T055 [P] Add multi-user isolation test in `tests/integration/test_multi_user.py`: two chats with different time zones and a plant of the same name get independent reminders at their own 08:00 and cannot read or delete each other's plants (FR-015)
- [X] T056 [P] Add unknown command and invalid input tests in `tests/integration/test_unknown_input.py` (FR-016): unknown command, plain text outside a flow, group-chat messages ignored
- [X] T057 [P] Security pass in `src/waterbot/`: confirm no token or secret in logs or exceptions, webhook path and header verified with constant-time comparison, callback ownership checks, no secrets in git (`git grep` for the token pattern)
- [X] T058 Build and run with Docker (image builds; db + schema + persistence across `docker compose restart db` verified; the full app container needs a real BOT_TOKEN, see T059): `docker compose up --build`; verify `/healthz` returns 200 at `http://localhost:8000/healthz`, the app reaches the `db` service, and data persists after `docker compose restart app`
- [~] T059 MOVED to `specs/002-production-deployment`: (PENDING: needs a real BotFather token; the same behaviour is covered by the automated tests) Walk through all 12 scenarios in `quickstart.md` against the Docker stack and record results (use `CLOCK_OFFSET_HOURS` instead of waiting for 08:00)
- [X] T060 [P] Write `README.md` for the project (what it does, commands, local run with Docker, tests, env vars) in Spanish
- [X] T061 Run `uv run ruff check .` and `uv run pytest` (including `-m postgres` against the compose database) and fix any failure
- [~] T062 MOVED to `specs/002-production-deployment`: Create the Neon PostgreSQL database; confirm current free-tier terms (**verify**, per `research.md`); store `DATABASE_URL` only in Render's environment
- [~] T063 MOVED to `specs/002-production-deployment`: Create the Telegram bot token with BotFather (use a separate bot for tests); set `BOT_TOKEN`, `WEBHOOK_SECRET`, `WEBHOOK_SECRET_TOKEN` as random values in Render's environment
- [~] T064 MOVED to `specs/002-production-deployment`: Push the repository to GitHub and create the Render Web Service from `render.yaml` (Docker runtime, free plan); confirm free instance hours are enough for one always-on service (**verify**)
- [~] T065 MOVED to `specs/002-production-deployment`: After the first deploy, open `https://<service>.onrender.com/healthz` and confirm `200`; send `/start` to the bot and confirm the webhook works
- [~] T066 MOVED to `specs/002-production-deployment`: Create the UptimeRobot HTTP(s) monitor for the `/healthz` URL with a 10-minute interval and an alert contact
- [~] T067 MOVED to `specs/002-production-deployment`: Redeploy once with a pending reminder and confirm it is still sent afterwards (FR-014, SC-005)
- [~] T068 MOVED to `specs/002-production-deployment`: Register one real plant with a one-day interval and confirm the 08:00 reminder arrives in your real time zone on the following morning, then confirm and verify the next date

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: no dependencies
- **Phase 2 (Foundational)**: after Phase 1; blocks all stories
- **Phases 3–7 (Stories)**: after Phase 2
  - US1 → US2 (needs a time zone to register) → US3 (needs plants) → US4 (extends the scheduler)
  - US5 needs US2 (plants) and can run in parallel with US3/US4
- **Phase 8 (Polish and deploy)**: after the stories you want to ship; **Render tasks (T062–T068) happen last**

### Within each story

- Tests first and failing → domain (pure) → repository → handlers
- Same-file tasks (`handlers.py`, `postgres.py`, `messages.py`) are sequential, not `[P]`

### Parallel Opportunities

- Phase 1: T002–T007 and T009 together after T001
- Phase 2: T010–T013, T016, T018–T020 together; T014→T015→T017 in order
- US1: T023–T026 together, then T027 ∥ T028
- US3: T038–T041 together, then T042 before T043–T046
- US4 and US5 can proceed in parallel once US3's scheduler exists

### Parallel Example: User Story 3 tests

```bash
Task: "Unit tests for scheduling in tests/unit/test_schedule.py"
Task: "Scheduler integration tests in tests/integration/test_scheduler.py"
Task: "Confirmation tests in tests/integration/test_confirm_flow.py"
Task: "Reminder repository tests in tests/integration/test_reminders_repo.py"
```

---

## Implementation Strategy

### MVP First (US1 + US2 + US3)

1. Phase 1 → Phase 2
2. US1 → US2 → US3, stopping to validate after each checkpoint
3. Run the bot locally with Docker (T058–T059) before touching Render
4. Deploy (T062–T068) once US3 passes; then add US4 and US5 and redeploy

### Incremental Delivery

Each story adds value without breaking the previous: zone → plants → reminders → insistence → list/delete.

---

## Spec Traceability

| Requirement | Tasks |
|-------------|-------|
| FR-001 welcome with commands | T020, T025, T029 |
| FR-002 set/change time zone | T024, T025, T028, T029 |
| FR-003 local time and season | T023, T027 |
| FR-004 register plant | T034, T036, T037 |
| FR-005 time zone required first | T034, T037 |
| FR-006 validation, unique names | T014, T032, T033, T035 |
| FR-007 list plants | T051, T054 |
| FR-008 delete with confirmation | T051, T052, T053, T054 |
| FR-009 08:00 local reminder | T038, T039, T042, T044 |
| FR-010 confirm from message | T040, T045, T046 |
| FR-011 repeat every 4 hours | T047, T048, T049 |
| FR-012 next interval by season on confirmation | T038, T040, T046 |
| FR-013 new plant counts as watered | T033, T036 |
| FR-014 survive restarts, catch up | T033, T039, T041, T067 |
| FR-015 per-user isolation | T033, T052, T055 |
| FR-016 Spanish, helpful errors | T020, T056 |
| SC-001 … SC-006 | T059, T068 (SC-001, SC-002), T048 (SC-003), T040 (SC-004), T067 (SC-005), T023 (SC-006) |

## Notes

- Commit after each task or logical group (solo project, direct to `main` is allowed by the constitution).
- Render is not needed until T062; local development uses Docker Compose with PostgreSQL.
- Re-verify third-party free-tier terms (Render, Neon, UptimeRobot) when you reach T062–T066.
