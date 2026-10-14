# Feature Specification: Plant Watering Reminders

**Feature Branch**: `001-plant-watering-reminders`

**Created**: 2026-10-13

**Status**: Draft

**Update 2026-10-13**: country replaced by a user-selected time zone (decided in `/speckit-plan`).

**Input**: User description: "Un bot de Telegram que me recuerde regar mis plantas. Puedo registrar una planta con su nombre, qué planta es, cada cuánto regarla (verano e invierno). El bot identifica en qué temporada estamos en mi país (registrado con un comando). Me recordará regarla y debo confirmarlo. Si no confirmo, insiste cada 4 horas. El aviso se envía a las 08:00 hrs del país indicado."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get started and set my time zone (Priority: P1)

When I add the bot for the first time, it greets me and lists the commands I can use. I then
choose my time zone from a list, which the bot uses to know my local time and which season it is for me.

**Why this priority**: Without a time zone the bot cannot know when 08:00 is nor which season
applies, so no reminder can work. It is the foundation for everything else.

**Independent Test**: Start the bot, verify the command list is shown, choose a time zone and verify
the bot confirms it and keeps it for later conversations.

**Acceptance Scenarios**:

1. **Given** a user who has never used the bot, **When** they start it, **Then** the bot shows a
   welcome message listing every available command with a short description.
2. **Given** a user with no time zone set, **When** they use the time zone command and pick one
   from the list (or type a valid zone name), **Then** the bot confirms the time zone, the local
   time there, and the season currently in effect.
3. **Given** a user with a time zone already set, **When** they use the time zone command again
   and pick another, **Then** the time zone is replaced and the bot confirms the change.
4. **Given** a user using the time zone command, **When** they type a name that is not a valid
   time zone, **Then** the bot explains the problem and asks again without changing the stored time zone.

---

### User Story 2 - Register a plant (Priority: P1)

I register a plant by giving its name, what kind of plant it is, and how many days to wait
between waterings in summer and in winter (for example: Name: Catalina, Type: Dólar, Summer:
7 days, Winter: 14 days).

**Why this priority**: Plants are the data every reminder depends on.

**Independent Test**: With a time zone set, register a plant and verify the bot confirms it with all
the values entered.

**Acceptance Scenarios**:

1. **Given** a user with a time zone set, **When** they register a plant with a name, type, summer
   interval and winter interval, **Then** the bot confirms the plant was saved and shows its data.
2. **Given** a user with no time zone set, **When** they try to register a plant, **Then** the bot
   asks them to set a time zone first.
3. **Given** a user registering a plant, **When** an interval is not a positive whole number of
   days, **Then** the bot rejects it, explains why, and asks for it again.
4. **Given** a user who already has a plant named "Catalina", **When** they register another plant
   with the same name, **Then** the bot rejects it and asks for a different name.

---

### User Story 3 - Receive and confirm a watering reminder (Priority: P1)

On the day a plant needs water, the bot sends me a message at 08:00 local time of my time zone. I
confirm that I watered it, and the bot starts counting the next interval based on the season
at that moment.

**Why this priority**: This is the core value of the product.

**Independent Test**: Register a plant with a short interval, wait for (or simulate) the due day,
verify the 08:00 message arrives, confirm it, and verify the next reminder is scheduled one
interval later.

**Acceptance Scenarios**:

1. **Given** a plant whose watering is due today, **When** it is 08:00 in the user's time zone,
   **Then** the bot sends one reminder naming the plant with a way to confirm the watering.
2. **Given** a pending reminder, **When** the user confirms, **Then** the bot acknowledges, stops
   reminding for that watering, and schedules the next one using the interval of the season in
   effect on the confirmation day.
3. **Given** a plant registered during summer, **When** the season changes to winter in the user's
   time zone, **Then** the next interval counted after a confirmation uses the winter value.
4. **Given** a freshly registered plant, **When** it is registered, **Then** it is treated as just
   watered and its first reminder falls one interval later at 08:00.

---

### User Story 4 - Persistent reminders when I don't confirm (Priority: P2)

If I do not confirm a reminder, the bot keeps insisting every 4 hours until I confirm.

**Why this priority**: It prevents forgotten waterings, but the basic reminder (Story 3) already
delivers value without it.

**Independent Test**: Receive a reminder, ignore it, and verify a new reminder arrives 4 hours later,
repeating until confirmed.

**Acceptance Scenarios**:

1. **Given** an unconfirmed reminder sent at 08:00, **When** 4 hours pass, **Then** the bot sends
   another reminder for the same plant.
2. **Given** an insisting reminder sequence, **When** the user confirms, **Then** no further
   reminders are sent for that watering.
3. **Given** an unconfirmed reminder at the end of the day, **When** the night starts, **Then** the
   bot does not send messages overnight and resumes the next day (see Assumptions).

---

### User Story 5 - See and delete my plants (Priority: P2)

I can list my registered plants, with the data of each one and when it will next need water, and
I can delete a plant I no longer have.

**Why this priority**: Needed to manage mistakes and changes, but not to receive reminders.

**Independent Test**: Register two plants, list them and verify both appear; delete one and verify
it no longer appears and stops generating reminders.

**Acceptance Scenarios**:

1. **Given** a user with registered plants, **When** they use the list command, **Then** the bot
   shows each plant with its name, type, summer interval, winter interval and next watering date.
2. **Given** a user with no plants, **When** they use the list command, **Then** the bot says there
   are no plants and explains how to register one.
3. **Given** a user with plants, **When** they use the delete command and choose a plant, **Then**
   the bot asks for confirmation, removes the plant, and no longer sends reminders for it.
4. **Given** a pending reminder for a plant, **When** the user deletes that plant, **Then** the
   insisting reminders stop.

---

### Edge Cases

- The bot is offline at 08:00: when it recovers, reminders that were due and not sent MUST be
  sent, not skipped.
- The user changes time zone while reminders are pending: future reminders use the new time zone's
  08:00 and season; pending ones are not duplicated.
- Several plants are due on the same day: each plant gets its own reminder and its own confirmation.
- The user confirms a watering after several days of delay: the next interval counts from the
  confirmation day, not from the original due day.
- The user sends a command with missing or invalid input in the middle of a registration: the
  bot explains and lets them retry or cancel.
- The user blocks the bot or never answers: the bot keeps its data and does not fail for other users.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When a user starts the bot, it MUST show a welcome message listing all available
  commands and what each does.
- **FR-002**: The bot MUST provide a command to set or change the user's time zone, letting the
  user pick it from a list of valid time zones instead of naming a country.
- **FR-003**: The bot MUST determine, from the user's time zone, its local time and the current
  season (summer or winter) there, including the opposite seasons between hemispheres.
- **FR-004**: The bot MUST provide a command to register a plant with: name, plant type, watering
  interval in days for summer, and watering interval in days for winter.
- **FR-005**: The bot MUST require a time zone to be set before registering a plant.
- **FR-006**: The bot MUST validate that intervals are positive whole numbers of days and that
  plant names are non-empty and unique per user.
- **FR-007**: The bot MUST provide a command to list the user's plants, showing name, type,
  both intervals and the next watering date.
- **FR-008**: The bot MUST provide a command to delete a plant, asking for confirmation first.
- **FR-009**: The bot MUST send a watering reminder at 08:00 local time of the user's time zone on
  the day a plant is due.
- **FR-010**: Each reminder MUST let the user confirm the watering from the same message.
- **FR-011**: If a reminder is not confirmed, the bot MUST repeat it every 4 hours until the user
  confirms or deletes the plant.
- **FR-012**: On confirmation, the bot MUST schedule the next reminder after the interval of the
  season in effect on the confirmation day, counted from that day.
- **FR-013**: A newly registered plant MUST be treated as just watered on its registration day.
- **FR-014**: Reminders and data MUST survive a bot restart; due reminders missed while the bot
  was offline MUST be sent once it is back.
- **FR-015**: Each user's time zone and plants MUST be kept separate from every other user's, so
  the bot can serve more than one user without mixing data.
- **FR-016**: The bot MUST reply in Spanish and handle unknown commands or invalid input with a
  helpful message instead of failing silently.

### Key Entities

- **User**: A person chatting with the bot. Has a time zone (and the hemisphere derived from it).
- **Plant**: Belongs to one user. Has a name (unique per user), a type, a summer interval in days, a
  winter interval in days, and the date of its last watering.
- **Reminder**: A pending notice that a plant needs water. Has the plant, the date it became due,
  the time of the last message sent, and whether it was confirmed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new user can set a time zone and register their first plant in under 2 minutes.
- **SC-002**: 100% of due reminders are delivered at 08:00 local time of the user's time zone, with
  a tolerance of 5 minutes.
- **SC-003**: After a missed confirmation, the repeat reminder arrives 4 hours (±5 minutes) after
  the previous one, with no more than one pending reminder per plant at a time.
- **SC-004**: After confirming a watering, the user receives no further reminders for that watering.
- **SC-005**: No scheduled reminder is lost after the bot restarts.
- **SC-006**: In a test with a Southern Hemisphere time zone and a Northern Hemisphere time zone on the
  same date, each is assigned the opposite season.

## Assumptions

- **Season rule**: only two seasons exist (summer and winter). Summer is the warm half of the year:
  October–March in the Southern Hemisphere and April–September in the Northern Hemisphere;
  winter is the other half. Hemisphere is derived from the chosen time zone's location.
- **Time zone instead of country**: the user picks a standard (IANA) time zone, which avoids
  ambiguity in countries that span several zones.
- **First watering**: a new plant counts as watered on the day it is registered; the first
  reminder comes one interval (of the current season) later at 08:00.
- **Insistence window**: repeat reminders are sent every 4 hours starting from 08:00 (08:00, 12:00,
  16:00, 20:00) and are not sent at night. If still unconfirmed, they resume the next day at 08:00
  and continue until confirmed. No more than one pending reminder per plant exists at a time.
- **Per-plant messages**: if several plants are due the same day, each has its own message and
  confirmation.
- **Multi-user ready**: the bot is built for its owner, but data is separated per user so others
  can use it later without changes to the behavior. Access control beyond that is out of scope.
- **Out of scope**: editing a plant (users delete and re-register), configurable reminder time,
  configurable repeat interval, more than two seasons, photos, and plant care advice.
- **Dependencies**: the user has a Telegram account; the bot has internet access to send messages.
