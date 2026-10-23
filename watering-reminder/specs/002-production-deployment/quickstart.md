# Quickstart: Production Deployment Runbook

Owner-run steps in order. Record every result in `verification.md` (create it from the template at the end).

## Before starting

- [ ] `uv run pytest` and `uv run ruff check .` pass locally.
- [x] `.env.example` exists and `render.yaml` (repo root, `rootDir: watering-reminder`) is in place (research.md §1).
- [ ] `git grep` for token-shaped strings returns nothing.

## 1. Database (Neon)

1. Create a project and database. Copy the connection string (needs `sslmode=require`).
2. Note the free-tier limits seen on the page (FR-010).

## 2. Bot identity (BotFather)

1. `/newbot` for production; keep the token private. Use a separate bot for tests.
2. Generate two random strings (32+ characters) for `WEBHOOK_SECRET` and `WEBHOOK_SECRET_TOKEN`.

## 3. Service (Render)

1. Push to GitHub.
2. Create the Web Service from `render.yaml` (Docker, free plan, correct root directory).
3. Enter `BOT_TOKEN`, `WEBHOOK_SECRET`, `WEBHOOK_SECRET_TOKEN`, `DATABASE_URL` in the dashboard.
4. After the first deploy open `https://<service>.onrender.com/healthz`, expect `200` `{"status":"ok"}`.
5. Send `/start` to the bot, expect the welcome message.
6. Wrong-secret check: `POST /webhook/wrong` expects `404`; correct path with a wrong header expects `403`.

## 4. Monitor (UptimeRobot)

1. Create the HTTP(s) monitor on `/healthz`, 10-minute interval, email alert contact.
2. Prove the alert once: suspend the service, wait for the email, resume it.

## 5. Verification in production

1. Temporarily set `CLOCK_OFFSET_HOURS` in Render, then run the 12 scenarios of
   `specs/001-plant-watering-reminders/quickstart.md`. Remove the variable when done.
2. Redeploy with a pending reminder; confirm it is still delivered.
3. Leave the bot idle for 24 h; confirm `/start` still answers immediately (SC-002).
4. Register a real plant with a 1-day interval in your real time zone; confirm the 08:00 reminder
   arrives next morning, confirm it, and check the next date is one day later.

## 6. Close

- [ ] `CLOCK_OFFSET_HOURS` is not set in Render.
- [ ] Free-tier findings written in `verification.md`.
- [ ] `001` and `002` statuses updated to Implemented.

## `verification.md` template

| Date | Check | Expected | Actual | Pass |
|------|-------|----------|--------|------|
