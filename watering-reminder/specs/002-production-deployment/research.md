# Research: Production Deployment

Items marked **verify** depend on provider terms and MUST be re-checked on the provider's site
during execution; results go in `verification.md` (FR-010).

## 1. Repository findings that block or affect the deploy

Found by inspecting the repository while planning:

1. **The git root is one level above the project.** The repository contains `watering-reminder/`
   as a subfolder, so `render.yaml`, `Dockerfile` and `pyproject.toml` are not at the repo root.
   Render looks for `render.yaml` at the repo root by default, and builds Docker from the service's
   root directory. **Decision (applied)**: `render.yaml` moved to the repo root (where Render
   looks by default, so no custom Blueprint path is needed) and the service sets
   `rootDir: watering-reminder`, which makes the Docker build context and `Dockerfile` resolve
   inside the project. Moving the whole project up was rejected: it changes many paths for no
   gain. **verify** on the first deploy that the build finds `Dockerfile` and `uv.lock`.
2. **`.env.example` does not exist**, although `tasks.md` T003 is marked done and `README.md` and
   `render.yaml` refer to it. **Decision**: create it with placeholder values only.
3. **Webhook URL**: the app requires `RENDER_EXTERNAL_URL` in webhook mode; Render provides it
   automatically for web services (**verify** that it is injected at runtime).
4. **Secrets in git**: `.env` is ignored and not tracked (checked). SC-008 repeats the scan at the end.

## 2. Neon database

- **Decision**: Neon free project, one database, connection string with `sslmode=require` as
  `DATABASE_URL` in Render only.
- **Rationale**: decided in 001 research (Render's own free Postgres expires).
- **verify**: free-tier storage and compute limits, idle suspend and wake time, whether the
  connection string should use the pooled endpoint.

## 3. Render service

- **Decision**: one free Docker Web Service from `render.yaml`, `RUN_MODE=webhook`, health check
  `/healthz`. Secrets (`BOT_TOKEN`, `WEBHOOK_SECRET`, `WEBHOOK_SECRET_TOKEN`, `DATABASE_URL`)
  entered in the dashboard (`sync: false`). Generate the two webhook values with a random
  generator (at least 32 characters).
- **verify**: monthly free instance hours cover one always-on service (a 31-day month is 744 h);
  free instances sleep after about 15 minutes without inbound traffic.
- **Risk**: first request after a cold start is slow; the monitor prevents sleep in normal operation.

## 4. Bot identity

- **Decision**: create a new production bot in BotFather; keep a second bot for tests. Never reuse
  the test token in Render.
- **Rationale**: FR-003; a leaked test token must not endanger production.

## 5. UptimeRobot

- **Decision**: HTTP(s) monitor on `https://<service>.onrender.com/healthz`, 10-minute interval
  (free plan minimum is **verify**), alert contact by email. Induce an outage once to prove the alert (SC-003).

## 6. Verification approach

- **Decision**: all 12 scenarios of `001/quickstart.md` run against the live bot. Scenarios that need
  08:00 use `CLOCK_OFFSET_HOURS` set temporarily in Render; it is removed afterwards and the
  removal is recorded. The 1-day real plant test runs last, with no offset.
- **Redeploy check**: create a pending reminder, trigger a manual redeploy, confirm the reminder
  arrives after the service is back.
