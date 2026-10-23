---

description: "Task list for Production Deployment"
---

# Tasks: Production Deployment

**Input**: `specs/002-production-deployment/` (plan.md, spec.md, research.md, quickstart.md)

**Tests**: No new automated tests (no behaviour change). Existing suite must stay green; production checks are recorded in `verification.md`.

**Format**: `[ID] [P?] [Story] Description`. **[O]** = owner-run in a provider dashboard (cannot be done by the assistant).

Replaces T059 and T062–T068 of `001-plant-watering-reminders/tasks.md`.

## Phase 1: Repository preparation

- [X] T001 [US1] Create `.env.example` (placeholders only) listing `BOT_TOKEN`, `WEBHOOK_SECRET`, `WEBHOOK_SECRET_TOKEN`, `DATABASE_URL`, `TEST_DATABASE_URL`, `RENDER_EXTERNAL_URL`, `PORT`, `RUN_MODE`, `CLOCK_OFFSET_HOURS`; confirm `.env` is untracked (research §1.2, §1.4)
- [X] T002 [US1] Verify and fix how Render finds the project inside the repo (git root is one level above `watering-reminder/`): set `rootDir` in `render.yaml` and decide the Blueprint path, or move the project up (research §1.1). Done: `render.yaml` moved to repo root with `rootDir: watering-reminder`; README updated
- [X] T003 Run `uv run ruff check .` and `uv run pytest`; both must pass before pushing (ruff clean, 154 passed)
- [X] T004 [US1] Secret scan: `git grep` for token-shaped strings and check `git ls-files` for `.env` (SC-008)

**Checkpoint**: repo is deployable from GitHub with no secrets in it.

## Phase 2: Cloud services (US1)

- [ ] T005 [O] [US1] Create the Neon database; record free-tier limits and idle behaviour in `verification.md` (FR-002, FR-010)
- [ ] T006 [O] [US1] Create the production bot in BotFather; generate `WEBHOOK_SECRET` and `WEBHOOK_SECRET_TOKEN` (32+ random characters) (FR-003, FR-004)
- [ ] T007 [O] [US1] Push to GitHub; create the Render Web Service from `render.yaml`; enter the four secrets in the dashboard; record free instance hours vs a 744 h month (FR-001, FR-004, FR-007, FR-010)
- [ ] T008 [US1] Open `/healthz` and expect `200`; send `/start` to the real bot; check wrong path secret → `404` and wrong header → `403` (FR-005, SC-001)

**Checkpoint**: bot is live and answers.

## Phase 3: Always on and monitored (US2)

- [ ] T009 [O] [US2] Create the UptimeRobot monitor on `/healthz`, 10-minute interval, email alert contact (FR-006)
- [ ] T010 [O] [US2] Induce an outage (suspend the service), confirm the alert arrives within 15 minutes, resume (SC-003)
- [ ] T011 [US2] After 24 h without messages confirm `/start` still answers immediately (SC-002)

## Phase 4: Real-world verification (US3)

- [ ] T012 [O] [US3] Temporarily set `CLOCK_OFFSET_HOURS`; run the 12 scenarios of `001/quickstart.md` against the live bot; record each in `verification.md` (FR-009, SC-004). Replaces 001 T059
- [ ] T013 [US3] Redeploy with a pending reminder; confirm it is delivered afterwards (FR-008, SC-005)
- [ ] T014 [O] [US3] Remove `CLOCK_OFFSET_HOURS` from Render and confirm it is gone (edge case)
- [ ] T015 [O] [US3] Register a real plant, 1-day interval, real time zone; confirm the 08:00 reminder arrives within 5 minutes, confirm it, check the next date is +1 day (SC-006)

## Phase 5: Close

- [ ] T016 Finish `verification.md` (dates, results, free-tier findings); confirm monthly cost is zero (SC-007)
- [ ] T017 Update `Status` to Implemented in `001` and `002` specs; close the `[~]` tasks in `001/tasks.md`

## Dependencies

T001–T004 → T005–T008 (T005, T006 can be done in parallel) → T009–T011 → T012–T015 → T016–T017.
