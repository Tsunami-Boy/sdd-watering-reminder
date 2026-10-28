# Contract: HTTP Endpoints

Served by the single FastAPI app on the port Render provides (`PORT`).

## `GET /healthz` (also answers `HEAD`)

Used by UptimeRobot (every 10 minutes) and as Render's health check path.

| Case | Response |
|------|----------|
| App up and database reachable | `200` with `{"status": "healthy"}` |
| App up, database unreachable | `503` with `{"status": "degraded"}` |

No authentication, no user data in the response. The check must be fast (query `SELECT 1` with a
short timeout) so that a slow database does not make the monitor time out.

## `POST /webhook/{secret}`

Receives Telegram updates.

- `{secret}` MUST equal `WEBHOOK_SECRET`; otherwise `404`.
- The header `X-Telegram-Bot-Api-Secret-Token` MUST equal `WEBHOOK_SECRET_TOKEN`; otherwise `403`.
- Body: a Telegram `Update` JSON. Response `200` with an empty JSON object once the update is
  handed to the bot; handler errors are logged and never turned into non-200 (Telegram would retry).

## Startup / shutdown behavior

- Startup: apply `schema.sql`, set the Telegram commands menu, call `setWebhook` with the public
  URL (`RENDER_EXTERNAL_URL`) and secret token, start the scheduler loop.
- Shutdown: stop the scheduler loop, close the database connections.

## Environment variables

| Name | Purpose |
|------|---------|
| `BOT_TOKEN` | Telegram bot token (secret) |
| `WEBHOOK_SECRET` | Random string used in the webhook path (secret) |
| `WEBHOOK_SECRET_TOKEN` | Value for Telegram's secret-token header (secret) |
| `DATABASE_URL` | PostgreSQL connection string (secret) |
| `RENDER_EXTERNAL_URL` | Provided by Render; base public URL |
| `PORT` | Provided by Render |
| `RUN_MODE` | `webhook` (default) or `polling` for local development |
