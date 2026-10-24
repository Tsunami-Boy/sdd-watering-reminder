# Verification Record: Production Deployment

| Date | Check | Expected | Actual | Pass |
|------|-------|----------|--------|------|
| 2026-10-22 | Neon database reachable with the production `DATABASE_URL` (pooled endpoint, `sslmode=require`) | `select version()` answers | PostgreSQL 18.6 | Yes |
| 2026-10-23 | First Render deploy (`rootDir: watering-reminder`, Docker) | Image builds, app starts | Built. First start failed: `WEBHOOK_SECRET_TOKEN` had characters Telegram rejects; fixed by regenerating with letters and digits only | Yes (after fix) |
| 2026-10-23 | `GET /healthz` | 200 `{"status":"ok"}` | 200, 0.7 s | Yes |
| 2026-10-23 | `HEAD /healthz` | 200 | 200 | Yes |
| 2026-10-23 | `POST /webhook/<wrong>` | 404 | 404 | Yes |
| 2026-10-23 | `/start` to the real bot | Welcome message | Bot answered (owner confirmed) | Yes |
| 2026-10-23 | UptimeRobot monitor on `/healthz`, 10 min, email contact | Monitor shows Up | Active (owner confirmed) | Yes |
| 2026-10-23 | Induced outage (SC-003): service suspended 00:25 | Down alert within 15 min | Down email at 00:35 (10 min) | Yes |
| 2026-10-23 | Recovery after resume | Up email, monitor green | Up email at 00:40 | Yes |
| 2026-10-23 | `/start` after 24 h without messages (SC-002) | Answers immediately | Answered immediately (owner confirmed) | Yes |

## Free-tier findings (FR-010)

- Neon: Free plan, 1 GB storage, 100 compute hours per month. Compute suspends when idle, so 100 h is enough unless the database stays awake around the clock.
- Render: Free plan, 750 instance hours per month shared across all projects. One always-on service uses 744 h in a 31-day month, so it fits while `waterbot` is the only free service.
- UptimeRobot: Free plan, minimum interval 5 minutes (the monitor uses 10).
- Cost (SC-007): no payment method registered on Render, Neon or UptimeRobot; all three show the Free plan. Monthly cost is zero (owner confirmed).

## Not yet checked

- Wrong header with correct path secret → 403 (needs the secret; optional)
- 12 scenarios (T012), redeploy (T013), real plant (T015)
