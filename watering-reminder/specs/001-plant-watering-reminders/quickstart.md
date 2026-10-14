# Quickstart: Plant Watering Reminders

Validation guide: how to run the bot and prove the feature works. Command and endpoint details are
in [contracts/](contracts/); tables are in [data-model.md](data-model.md).

## Prerequisites

- `devbox shell` (provides Python 3.12 and `uv`).
- A bot token from Telegram's BotFather (a separate test bot is recommended).
- A PostgreSQL database: local container or a free Neon database. Set `DATABASE_URL`.

## Local run (polling mode)

1. `uv sync`
2. Export `BOT_TOKEN`, `DATABASE_URL`, `RUN_MODE=polling`.
3. `uv run python -m waterbot` (entry point defined in the project).
4. Run the tests: `uv run pytest`.

## Scenario checks (map to the spec)

| # | Do | Expect |
|---|----|--------|
| 1 | `/start` | Welcome with all 5 commands (FR-001) |
| 2 | `/agregar` before `/zona` | Asked to set a time zone first (FR-005) |
| 3 | `/zona` → pick a region and zone | Confirmation with local time and season (FR-002, FR-003) |
| 4 | `/zona` with text `Nope/Nowhere` | Error, stored zone unchanged |
| 5 | `/agregar` → Catalina, Dólar, 7, 14 | Summary and first reminder date (FR-004, FR-013) |
| 6 | `/agregar` with the same name | Rejected (FR-006) |
| 7 | `/plantas` | Plant listed with next date (FR-007) |
| 8 | Set the plant's `last_watered_on` back in the database, wait one tick | Reminder arrives (use the test clock/hook to avoid waiting until 08:00) (FR-009) |
| 9 | Ignore it | Another message at the next slot (FR-011) |
| 10 | Tap `✅ Ya regué` | Message edited, no more messages, next date shown (FR-010, FR-012) |
| 11 | `/eliminar` → plant → Sí | Plant gone, pending reminder gone (FR-008) |
| 12 | Stop the bot with a due reminder, restart it | Reminder sent after restart (FR-014) |

A test-only setting `CLOCK_OFFSET_HOURS` (or an injectable clock in tests) lets the checks run
without waiting for 08:00.

## Deploy on Render + UptimeRobot

1. Create the Neon database; copy its connection string.
2. Push the repository to GitHub; create a Render **Web Service** from it using `render.yaml`
   (free plan, build `uv sync --frozen`, start command running `uvicorn waterbot.app:app`).
3. Set environment variables from [contracts/http-endpoints.md](contracts/http-endpoints.md) in the
   Render dashboard (never in git).
4. After the first deploy, open `https://<service>.onrender.com/healthz` and expect `200`.
5. In UptimeRobot, create an HTTP(s) monitor for that URL with a 10-minute interval.
6. Send `/start` to the bot in Telegram and repeat the scenario checks above.
7. Redeploy once and confirm a pending reminder is still sent afterwards.
