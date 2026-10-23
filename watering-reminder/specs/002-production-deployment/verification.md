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

## Free-tier findings (FR-010)

- Neon: _pending, write the limits seen in the dashboard_
- Render: _pending, free instance hours vs 744 h month_

## Not yet checked

- Wrong header with correct path secret → 403 (needs the secret; optional)
- 24 h idle check (T011), 12 scenarios (T012), redeploy (T013), real plant (T015)
