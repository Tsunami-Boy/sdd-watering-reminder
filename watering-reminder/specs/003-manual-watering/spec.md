# Feature Specification: Manual Watering

**Feature Branch**: `003-manual-watering`

**Created**: 2026-10-23

**Status**: Draft

**Input**: User description: "Comando /regar: se usa cuando el usuario riega una planta por su cuenta antes de que llegue la alerta. Al usarlo, el bot pide cuál de las plantas registradas se va a regar. Luego de seleccionar, muestra un mensaje para confirmar el riego. Si se confirma, se actualiza la fecha de último riego de esa planta y se corre la fecha de la próxima notificación según corresponda. Si no se confirma, no se hace nada."

**Depends on**: `001-plant-watering-reminders` (plants, intervals, reminders and the `/eliminar` choose-then-confirm pattern), `002-production-deployment` (live bot).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Register a watering done ahead of the reminder (Priority: P1)

As a plant owner, I want to tell the bot that I already watered a plant on my own, so that the
bot counts that watering and moves the next reminder forward instead of reminding me too soon.

**Why this priority**: It is the whole feature. Without it, watering early leaves the old
schedule in place and the bot nags about a plant that was just watered.

**Independent Test**: With at least one registered plant, send `/regar`, pick the plant, confirm,
and check with `/plantas` that the next watering date moved to today plus the plant's interval.

**Acceptance Scenarios**:

1. **Given** I have registered plants, **When** I send `/regar`, **Then** the bot shows one
   choice per plant and asks which one I watered.
2. **Given** the list of plants is shown, **When** I choose a plant, **Then** the bot asks me to
   confirm that I watered that plant, naming it, with a yes and a no option.
3. **Given** the confirmation question is shown, **When** I confirm, **Then** the plant's last
   watering date becomes today (in my time zone), its next reminder is scheduled one interval
   after today using the interval of the current season, and the bot replies with a message
   stating the plant and the date of its next watering.
4. **Given** the confirmation question is shown, **When** I decline, **Then** nothing changes
   for that plant and the bot replies that no watering was registered.
5. **Given** I watered a plant that was not yet due, **When** I confirm, **Then** the plant gets
   no reminder on the date it was originally due, and the next reminder arrives on the new date.

---

### User Story 2 - Watering a plant whose reminder is already pending (Priority: P2)

As a plant owner, I want `/regar` to also work when the reminder for that plant has already been
sent but I have not tapped "Ya regué", so that I stop receiving the repeated reminders.

**Why this priority**: Likely in practice (watering before replying to the reminder), but the
feature is useful without it.

**Independent Test**: Let a plant become due so its reminder is pending, use `/regar` for that
plant and confirm, and verify the repeated reminders for it stop.

**Acceptance Scenarios**:

1. **Given** a plant has a pending reminder, **When** I register its watering with `/regar` and
   confirm, **Then** the pending reminder stops repeating and the plant's next watering date
   moves forward as in User Story 1.
2. **Given** I registered a watering with `/regar` while a reminder message was pending, **When**
   I later tap "Ya regué" on that old reminder message, **Then** the bot tells me the reminder is
   no longer active and does not change the watering date again.

---

### User Story 3 - Nothing to water or flow interrupted (Priority: P3)

As a plant owner, I want clear behavior when I have no plants or when I abandon the flow, so
that I am never left in a confusing state.

**Why this priority**: Guards against dead ends; not needed for the main value.

**Independent Test**: Send `/regar` with no plants registered, and separately start the flow and
abort it with `/cancelar`.

**Acceptance Scenarios**:

1. **Given** I have no registered plants, **When** I send `/regar`, **Then** the bot tells me I
   have no plants and explains how to add one with `/agregar`.
2. **Given** I have not set my time zone, **When** I send `/regar`, **Then** the bot asks me to
   set it with `/zona` first.
3. **Given** I am in the middle of `/regar`, **When** I send `/cancelar`, **Then** the flow ends
   and nothing changes.

---

### Edge Cases

- The plant is deleted between choosing it and confirming: the bot says the plant no longer
  exists and changes nothing.
- The user taps a choice or confirmation from an old `/regar` message (for example the next day
  or after a restart): the action applies to the plant and today's date at the moment of
  confirming, or the bot says the plant no longer exists. It never corrupts another plant.
- The user confirms the same plant twice in a row: the second confirmation simply sets the last
  watering date to today again; the next watering date does not change.
- The season changes between registering and the next due date: the interval used is the one of
  the season in effect on the day of watering, as for confirmations from reminders.
- The user changes time zone: "today" is always the current date in the user's current time zone.
- Another user cannot choose or confirm a plant that is not theirs.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The bot MUST provide a `/regar` command, listed in the welcome message and in the
  command menu, for registering a watering done by the user outside a reminder.
- **FR-002**: On `/regar`, the bot MUST show the user's registered plants as choices, one per
  plant, and ask which one was watered.
- **FR-003**: After a plant is chosen, the bot MUST ask for confirmation, naming the plant, with
  a yes and a no option, before changing any data.
- **FR-004**: On confirmation, the bot MUST set the plant's last watering date to today's local
  date in the user's time zone.
- **FR-005**: On confirmation, the bot MUST schedule the plant's next reminder one interval after
  today, using the interval of the season in effect today (same rule as FR-012 of 001).
- **FR-006**: On confirmation, the bot MUST reply with a message stating the plant and the date of
  its next watering.
- **FR-007**: If the user declines, the bot MUST NOT change any data and MUST reply that no
  watering was registered.
- **FR-008**: If the plant has a pending, unconfirmed reminder when the watering is confirmed, the
  bot MUST stop that reminder from repeating, and a later tap on its old "Ya regué" button MUST
  be answered as "no longer active" without changing data.
- **FR-009**: With no registered plants, `/regar` MUST reply explaining how to add one; without a
  time zone it MUST ask the user to set it first.
- **FR-010**: `/cancelar` MUST abort the `/regar` flow without changing data.
- **FR-011**: The bot MUST NOT let a user choose or confirm a plant that belongs to another user.
- **FR-012**: All messages MUST be in Spanish and follow the tone of the existing commands.

### Key Entities *(include if feature involves data)*

- **Plant**: An existing registered plant. This feature updates its last watering date, which
  determines its next watering date. No new fields.
- **Reminder**: The existing pending-reminder record for a plant that is due and unconfirmed.
  This feature removes it when the user registers the watering with `/regar`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can register a manual watering in at most 3 interactions after sending
  `/regar` (command, plant choice, confirmation).
- **SC-002**: After a confirmed `/regar`, the plant's next watering date equals today plus its
  seasonal interval in 100% of cases, and no reminder is sent for that plant before that date.
- **SC-003**: After a declined or cancelled `/regar`, the plant's data is identical to before in
  100% of cases.
- **SC-004**: After a confirmed `/regar` on a plant with a pending reminder, no further reminder
  for that plant is sent before its new due date.
- **SC-005**: The bot answers each step of the flow in under 2 seconds under normal conditions.

## Assumptions

- The command is `/regar` as a Telegram command (the request wrote it as `./regar`).
- "Today" means the current date in the user's time zone; the feature does not let the user pick
  a different watering date.
- The next reminder date is computed exactly as after tapping "Ya regué": last watering date plus
  the seasonal interval, with the reminder sent at 08:00 local time.
- The choose-then-confirm interaction mirrors `/eliminar` (a button per plant, then yes/no).
- A plant can be watered manually even if it is not yet due, and also if it is overdue or has a
  pending reminder.
- Only private chats are served, as in the existing bot.
- No new data is stored and no history of manual waterings is kept.
