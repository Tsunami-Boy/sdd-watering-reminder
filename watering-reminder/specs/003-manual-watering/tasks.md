---

description: "Task list for Manual Watering"
---

# Tasks: Manual Watering

**Input**: `specs/003-manual-watering/` (plan.md, spec.md, research.md, data-model.md, contracts/bot-commands.md, quickstart.md)

**Tests**: Required. Constitution II: tests for logic that decides when a plant is due are written first and must fail before the implementation. All tests go in `tests/integration/test_regar_flow.py` using `fake_repo`, `FakeClock` and `BotService` as in `tests/integration/test_confirm_flow.py`.

**Format**: `[ID] [P?] [Story] Description`. All commands run from `watering-reminder/`.

## Phase 1: Foundational (blocks all stories)

- [X] T001 Add Spanish texts to `src/waterbot/bot/messages.py`: `REGAR_CHOOSE = "¿Qué planta regaste?"`, `regar_ask(name)` → `¿Confirmas que regaste «<name>»?`, `regar_done(name, next_due)` → `Regada ✅ «<name>». Próximo riego: <dd/mm/aaaa>` (same date format as `watered()`), `REGAR_CANCELLED = "No se registró ningún riego."`; reuse the existing `NEED_TIMEZONE`, `NO_PLANTS` and `PLANT_GONE`
- [X] T002 Add `("regar", "Registrar un riego que ya hiciste")` to `COMMANDS` in `src/waterbot/bot/messages.py` so it appears in the welcome message and the command menu (FR-001); update any existing test that asserts the exact list of commands

**Checkpoint**: texts exist; nothing is wired yet.

## Phase 2: User Story 1 - Register a watering ahead of the reminder (P1) 🎯 MVP

**Goal**: `/regar` → choose plant → confirm → `last_watered_on` = local today, next date shown.

**Independent test**: with one plant, run the flow and check `/plantas` shows today + seasonal interval; decline and check nothing changed.

### Tests first (must fail)

- [X] T003 [US1] In `tests/integration/test_regar_flow.py`: `BotService.regar(CHAT)` returns `REGAR_CHOOSE` with one button per plant, callback data `reg:<id>` (FR-002)
- [X] T004 [US1] Same file: callback `reg:<id>` returns an edited reply asking confirmation with the plant name and buttons `Sí` (`regok:<id>`) and `No` (`regno`); no data changed (FR-003)
- [X] T005 [US1] Same file: callback `regok:<id>` on a not-yet-due plant sets `last_watered_on` to local today and replies with today + seasonal interval; assert the season used is the one in effect today, using a date in the other season than registration (FR-004, FR-005, FR-006, SC-002)
- [X] T006 [US1] Same file: callback `regno` replies `REGAR_CANCELLED` and `last_watered_on` is unchanged (FR-007, SC-003)
- [X] T007 [US1] Same file: after `regok`, run `scheduler.tick` on the original due date and assert no reminder is created for that plant (acceptance scenario 5)

### Implementation

- [X] T008 [US1] Add `water_plant(repo, chat_id, plant_id, zone, now) -> WateredResult | None` to `src/waterbot/services.py`: `get_plant` (None if missing or not the chat's), `delete_reminder` ignoring its result, `mark_watered(plant_id, local_date(zone, now))`, return `WateredResult(updated, next_due_on(updated, zone))`; leave `confirm_watering` unchanged (research §1)
- [X] T009 [US1] Add `BotService.regar()` to `src/waterbot/bot/flows.py`: buttons built like `eliminar()` with data `reg:<id>`
- [X] T010 [US1] In `BotService.callback` (`src/waterbot/bot/flows.py`) dispatch `reg` → ask confirmation (via `_own_plant`, `PLANT_GONE` if missing), `regok` → `water_plant` then `regar_done`, `regno` → `REGAR_CANCELLED`; all with `edit=True`
- [X] T011 [US1] Register `("regar", "regar")` in the `register_handlers` list in `src/waterbot/bot/handlers.py`

**Checkpoint**: T003–T007 pass; `/regar` works end to end for a plant with no pending reminder.

## Phase 3: User Story 2 - Pending reminder (P2)

**Goal**: confirming `/regar` also stops a reminder that is already pending.

**Independent test**: make a plant due, `tick`, run `/regar` and confirm, check no reminder remains and no repeats are sent.

- [X] T012 [US2] Test (fails first if T008 skipped the reminder delete): plant due and `tick` run so a reminder exists; `regok` → `get_reminder(plant.id)` is `None`, `last_watered_on` is today (FR-008)
- [X] T013 [US2] Test: advance the clock past the next repeat slot and `tick`; assert no further message is sent for that plant (SC-004)
- [X] T014 [US2] Test: after T012, callback `water:<id>` (old "Ya regué") answers `REMINDER_INACTIVE` and does not change `last_watered_on` (FR-008)

**Checkpoint**: T012–T014 pass; if any fails, fix `water_plant` in `src/waterbot/services.py`.

## Phase 4: User Story 3 - Edge flows (P3)

**Goal**: no dead ends.

- [X] T015 [US3] Test + implement in `BotService.regar()`: user without time zone → `NEED_TIMEZONE`; user with zone but no plants → `NO_PLANTS` (FR-009)
- [X] T016 [P] [US3] Test: `reg:<id>` / `regok:<id>` for a plant deleted in between, or belonging to another chat, replies `PLANT_GONE` and changes nothing (FR-011)
- [X] T017 [P] [US3] Test: `/cancelar` after `/regar` replies the existing "nothing to cancel" message and data is unchanged (FR-010)
- [X] T018 [P] [US3] Test: `regok` twice in a row keeps `last_watered_on` and next date unchanged the second time (edge case)
- [X] T019 [P] [US3] Test: non-numeric ids in `reg:` / `regok:` (for example `regok:abc`) reply `PLANT_GONE` without raising

**Checkpoint**: all scenarios of spec 003 covered.

## Phase 5: Polish and close

- [X] T020 Run `uv run pytest` and `uv run ruff check .`; both must pass (constitution: tests pass before a task is complete)
- [X] T021 [P] Add the `/regar` row and flow to `specs/001-plant-watering-reminders/contracts/bot-commands.md` (principle V), copying from `specs/003-manual-watering/contracts/bot-commands.md`
- [X] T022 Commit to `main` and push so Render redeploys
- [X] T023 [O] Run the manual steps of `quickstart.md` against the live bot and record results in `specs/003-manual-watering/verification.md`
- [X] T024 Set `Status` to Implemented in `specs/003-manual-watering/spec.md`

## Dependencies

- T001–T002 first. Within a story, tests (T003–T007) before implementation (T008–T011).
- US2 and US3 depend on US1 (same flow); US2 and US3 are independent of each other.
- T021 is independent of the code once US1 is done. T022–T024 last.

```text
T001–T002 → T003–T007 → T008–T011 → T012–T014
                                   → T015–T019   (T016–T019 in parallel)
                        → T020 → T021 [P] → T022 → T023 → T024
```

## Implementation Strategy

- **MVP**: Phases 1–2 (T001–T011). `/regar` works for the normal case and can be deployed alone.
- Then US2 (pending reminder), then US3 (edges), then polish and deploy.
- Total: 24 tasks. US1: 9 (T003–T011), US2: 3, US3: 5, shared/close: 7.
