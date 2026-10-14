# Research: Plant Watering Reminders

Items marked **verify** are based on knowledge of each provider's free tier at the time of writing
and MUST be re-checked on the provider's site before deploying; they do not change the design.

## 1. Hosting on Render with UptimeRobot

- **Decision**: One Render free Web Service. UptimeRobot monitors `GET /healthz` every 10 minutes.
- **Rationale**: Render free web services spin down after roughly 15 minutes without inbound HTTP
  traffic, so a 10-minute ping keeps the instance up. A single always-on free service fits the
  monthly free instance hours (**verify**). Telegram webhook calls are also inbound traffic and can
  wake a sleeping instance.
- **Alternatives**: Render Background Worker (paid, no free tier); long polling in a non-web
  process (would sleep and cannot be pinged); other hosts (rejected by the user's choice).
- **Risk**: an instance can still restart or redeploy. The design never relies on process memory
  for reminders (see 3 and 4). `/healthz` should also check the database so the monitor flags it
  when storage is down.

## 2. Telegram integration: webhook vs long polling

- **Decision**: Webhook, using `python-telegram-bot` inside a FastAPI app. The webhook is
  registered at startup on `https://<render-url>/webhook/<WEBHOOK_SECRET>` with Telegram's
  `secret_token`, and each request's `X-Telegram-Bot-Api-Secret-Token` header is verified.
- **Rationale**: the service already needs a public HTTP port for UptimeRobot; webhook avoids
  holding an outbound polling connection and lets Telegram traffic wake the instance. The
  secret path plus header protects the endpoint (Principle IV).
- **Alternatives**: long polling (simplest locally, but wastes the web service and does not wake
  a sleeping instance); PTB's built-in webhook server (cannot also serve a custom `/healthz`
  route cleanly, so FastAPI hosts both).
- Use polling only for local development (documented in quickstart).

## 3. Persistence

- **Decision**: External managed PostgreSQL (Neon free tier), via `DATABASE_URL`, using `psycopg` 3
  with plain SQL and a `schema.sql` applied at startup (idempotent).
- **Rationale**: Render's free web service filesystem is ephemeral, so SQLite on disk would lose
  reminders on every restart/redeploy, violating Principle III. Render's own free PostgreSQL
  expires after about 30 days (**verify**), so an external provider with no expiry is safer. Neon
  free tier suspends compute when idle and wakes on connect (**verify**); the first query after
  idle may take a second, which is acceptable.
- **Alternatives**: Render persistent disk (paid); Render Postgres free (expires); Supabase
  (similar, heavier); SQLite + Litestream/S3 (more moving parts, violates Principle I).
- Use short-lived connections or a small pool with reconnect, because the provider closes idle
  connections.

## 4. Scheduling and reminder reliability

- **Decision**: A background `asyncio` task started in the FastAPI lifespan runs a **tick every 60
  seconds**. Each tick queries PostgreSQL for plants whose reminder is due (`due_at <= now`) and for
  active reminders whose `next_send_at <= now`, sends them through the `Notifier`, and updates
  `last_sent_at`/`next_send_at` only after a successful send.
- **Rationale**: state is in the database, not in scheduler memory, so after a restart the first
  tick sends everything missed (FR-014). A failed send leaves the row unchanged and is retried on
  the next tick and logged (Principle III). Only one instance runs, so no distributed locking; a
  row-level `FOR UPDATE SKIP LOCKED` is still used so an overlapping deploy cannot double-send.
- **Alternatives**: APScheduler / `JobQueue` with a persistent job store (extra dependency and
  per-job state to reconcile with a changing time zone or season); cron on Render (paid).
- **Repeat rule**: send times are 08:00, 12:00, 16:00, 20:00 local; after the 20:00 message the
  next send is 08:00 the next day. After a late recovery, only **one** message is sent per tick per
  plant and the next send is computed from the actual send time (no burst of backlog messages).

## 5. Time zone selection and season

- **Decision**: Use stdlib `zoneinfo` backed by the `tzdata` package (so Render's slim image does
  not depend on system tz files). The user picks a zone through the bot: first a region
  (América, Europa, Asia, África, Oceanía, Atlántico/Índico/Ártico, Antártida), then a paged
  inline keyboard of zones in that region. Typing a zone name (for example `America/Santiago`) is
  also accepted and validated against `zoneinfo.available_timezones()`.
- **Hemisphere**: derived from the latitude sign of the zone's reference location in the IANA
  `zone.tab` shipped with `tzdata` (**verified**: `tzdata` 2026.5 ships `zone.tab`; only the canonical zones listed in it are
  selectable, and a test checks that each one has a hemisphere).
- **Season rule** (from spec): Southern Hemisphere summer = October–March; Northern Hemisphere
  summer = April–September; the rest is winter. The month is taken in the user's local time.
- **Alternatives**: `pytz` (legacy API, `country_timezones` ties back to countries the user wanted
  to avoid); `pycountry` (country-based); asking for location (privacy cost).

## 6. Conversation state for `/agregar` and `/eliminar`

- **Decision**: in-memory per-chat state kept in `BotService` (framework-independent, so it is
  testable without Telegram), with the PTB handlers as a thin adapter, plus `/cancelar`.
- **Rationale**: a registration takes under a minute; losing a half-finished form on a restart is
  acceptable and simpler than persisting conversation state (Principle I). Reminders and plants
  are always persisted.
- **Alternatives**: persisting conversation state in PostgreSQL (extra complexity, no spec need).

## 7. Testing approach

- **Decision**: `pytest`; the `domain` package is tested with a controllable clock (`now` passed as
  a parameter, never read inside domain functions). Time zone edge cases to cover: DST changes,
  zones with half-hour offsets, hemisphere flip, 08:00 on a DST transition day.
- Scheduler and handlers are tested with a fake `Notifier` and the repository protocol; storage
  gets tests against a real PostgreSQL (local container or a throwaway Neon branch).
