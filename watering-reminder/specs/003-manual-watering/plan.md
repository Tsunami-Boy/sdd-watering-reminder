# Implementation Plan: Manual Watering

**Branch**: `003-manual-watering` | **Date**: 2026-10-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-manual-watering/spec.md`

## Summary

Add the `/regar` command: choose a plant, confirm, and the bot sets `last_watered_on` to the local
today, drops any pending reminder for that plant, and replies with the next watering date. It
reuses the existing choose-then-confirm pattern of `/eliminar` and the existing repository
operations (`mark_watered`, `delete_reminder`). No schema change, no new dependency.

## Technical Context

**Language/Version**: Python 3.12 (as in 001)

**Primary Dependencies**: python-telegram-bot (existing); none added

**Storage**: PostgreSQL via the existing `Repository`; no schema change

**Testing**: pytest with the existing fake repository and `FakeClock`

**Target Platform**: Render free Web Service (live since 002)

**Project Type**: Telegram bot (single project)

**Performance Goals**: each step answers in under 2 s (SC-005); trivially met, one or two queries per step

**Constraints**: Spanish messages; callback data ≤ 64 bytes; only private chats

**Scale/Scope**: personal use, a handful of plants per user

## Constitution Check

| Principle | Result |
|-----------|--------|
| I. Simplicity First | Pass. Reuses existing repo methods and the `/eliminar` pattern; no new tables, dependencies or state. |
| II. Test-First for Reminder Logic | Pass, with obligation. The new service function changes when reminders are due, so its tests are written first and must fail before the code. |
| III. Reliable Reminders | Pass. Only a reminder for a plant that was just watered is removed; other reminders and restart survival are untouched. |
| IV. Privacy and Secrets | Pass. No new data stored or sent anywhere. |
| V. Specification as Source of Truth | Pass. Spec 003 precedes the code; `001/contracts/bot-commands.md` gets `/regar` added when implemented. |

Re-check after design: still pass; no violations, nothing in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/003-manual-watering/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── bot-commands.md
└── tasks.md              # created by /speckit-tasks
```

### Source Code

```text
src/waterbot/
├── services.py           # add water_plant(): clear reminder + mark_watered
└── bot/
    ├── flows.py          # add regar() command and reg / regok / regno callbacks
    ├── handlers.py       # register the /regar CommandHandler
    └── messages.py       # texts and the command-menu / welcome entry

tests/
├── unit/                 # none needed
└── integration/
    └── test_regar_flow.py
```

**Structure Decision**: single existing project; the feature touches four existing modules and adds
one test file.

## Complexity Tracking

No violations.
