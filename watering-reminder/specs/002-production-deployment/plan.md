# Implementation Plan: Production Deployment

**Branch**: `002-production-deployment` | **Date**: 2026-10-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-production-deployment/spec.md`

## Summary

Put the already-implemented bot (001) online on free plans: Neon PostgreSQL, a real BotFather bot,
one Render Docker web service created from `render.yaml`, and an UptimeRobot monitor on `/healthz`.
No bot behaviour changes. The work is mostly owner-run setup in provider dashboards plus a small
number of repository fixes found while preparing the plan (see research.md, section 1), followed by
a recorded verification pass in production.

## Technical Context

**Language/Version**: Python 3.12 (unchanged, see 001)

**Primary Dependencies**: none added

**Storage**: Neon PostgreSQL (external, free tier), via `DATABASE_URL`

**Testing**: existing `pytest` suite must stay green; production checks are manual scenarios recorded in `verification.md`

**Target Platform**: Render free Web Service (Docker runtime); UptimeRobot free monitor

**Project Type**: single project, deployment only

**Performance Goals**: `/start` answered within 10 s (SC-001); 08:00 reminder within 5 min (SC-006)

**Constraints**: zero monthly cost; secrets only in Render's environment; one instance

**Scale/Scope**: one owner, a handful of plants

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Result |
|-----------|--------|
| I. Simplicity First | Pass. No new dependency or service beyond those already decided in 001 research. |
| II. Test-First for Reminder Logic | Pass / N/A. No reminder logic changes; existing tests must stay green. |
| III. Reliable Reminders | Pass. Verified in production by the redeploy check (SC-005). |
| IV. Privacy and Secrets | Pass. Secrets only in Render's environment; `.env` stays ignored; SC-008 scans the repository. |
| V. Spec as Source of Truth | Pass. Any defect found becomes a fix to 001 or a new spec (FR-011). |

Re-check after design: unchanged. No complexity violations.

## Project Structure

### Documentation (this feature)

```text
specs/002-production-deployment/
├── plan.md           # This file
├── research.md       # Phase 0: repository findings and provider decisions
├── quickstart.md     # Phase 1: ordered runbook (owner-run steps)
├── verification.md   # Created during execution: dated record of checks (FR-009, FR-010)
└── tasks.md          # /speckit-tasks
```

No `data-model.md` (no new data) and no `contracts/` (the HTTP contract is
`001-plant-watering-reminders/contracts/http-endpoints.md`, unchanged).

### Source Code (repository root)

Only deployment files are touched:

```text
render.yaml          # moved to the repo root, rootDir: watering-reminder (research.md §1)
watering-reminder/.env.example   # was missing; created (research.md §1)
README.md            # deployment section points to this runbook
```

**Structure Decision**: no code layout change.

## Complexity Tracking

No violations.
