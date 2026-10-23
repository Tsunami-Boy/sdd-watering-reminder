# Feature Specification: Production Deployment

**Feature Branch**: `002-production-deployment`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Despliegue a producción del bot Watering Reminder (feature 001, ya implementada y probada con tests). Objetivo: dejar el bot funcionando 24/7 en la nube con costo cero: base PostgreSQL en Neon, bot de Telegram real creado con BotFather con secretos solo en variables de entorno de Render, servicio web en Render (runtime Docker, plan gratuito) desde render.yaml, monitor UptimeRobot sobre /healthz cada 10 minutos con contacto de alerta. Verificación en producción: /healthz responde 200, /start funciona vía webhook, un redeploy conserva un recordatorio pendiente y se envía igual, recorrido de los 12 escenarios de quickstart.md contra el stack real, y una planta real con intervalo de 1 día cuyo aviso de las 08:00 llega en la zona horaria real del usuario. Reemplaza las tareas T059 y T062–T068 de la 001. No incluye cambios de funcionalidad del bot."

**Depends on**: `001-plant-watering-reminders` (implemented; all behaviour is specified there).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bot online and reachable (Priority: P1)

As the owner, I want the bot running in the cloud so that I can use it from Telegram without
keeping my own computer on. The bot, its database and its secrets are created in the chosen free
services, and the bot answers me.

**Why this priority**: Nothing else in this feature can be verified until the bot is live.

**Independent Test**: Open the service's health address and verify it reports healthy, then send
`/start` to the real bot and verify the welcome message arrives.

**Acceptance Scenarios**:

1. **Given** the database, the real bot and the service are created, **When** I open the health
   address, **Then** it answers "healthy" (HTTP 200).
2. **Given** the service is live, **When** I send `/start` to the real bot in Telegram, **Then** I
   receive the welcome message with all commands.
3. **Given** the repository and the service configuration, **When** I search them for the bot
   token and the other secrets, **Then** none are found; secrets exist only in the hosting
   service's environment settings.
4. **Given** a request to the bot's entry point with a wrong path secret or a wrong secret header,
   **When** it is received, **Then** it is rejected and nothing reaches the bot logic.

---

### User Story 2 - Always on and monitored (Priority: P1)

As the owner, I want the free service to stay awake and to be told when it goes down, so that
8:00 reminders are not missed because the service was idle or broken.

**Why this priority**: A reminder bot that sleeps misses its main job (SC-002 of 001).

**Independent Test**: Leave the bot untouched for longer than the hosting plan's idle period and
verify it still answers; stop the service on purpose and verify an alert reaches me.

**Acceptance Scenarios**:

1. **Given** an external monitor checks the health address every 10 minutes, **When** the bot
   receives no messages for several hours, **Then** it still answers `/start` immediately.
2. **Given** the monitor is active, **When** the health address stops answering, **Then** I receive
   an alert through my configured contact.
3. **Given** the chosen free plans, **When** I review their current terms, **Then** the free
   instance hours cover one always-on service for a full month and the free database limits cover
   this bot's data; the findings are recorded.

---

### User Story 3 - Real-world verification (Priority: P1)

As the owner, I want to confirm in production the behaviour already proven by tests in 001, so I
can trust the bot with my real plants.

**Why this priority**: Closes feature 001 (previous task T059) and proves the deployment end to end.

**Independent Test**: Walk through the 12 scenarios of `001-plant-watering-reminders/quickstart.md`
against the live bot and record each result.

**Acceptance Scenarios**:

1. **Given** the live bot, **When** I run the 12 quickstart scenarios (using the clock-offset
   setting instead of waiting for 08:00 where needed), **Then** each produces the expected result
   and the outcome of each is recorded.
2. **Given** a pending, unsent reminder, **When** the service is redeployed, **Then** the reminder
   is still sent afterwards (FR-014, SC-005 of 001).
3. **Given** a real plant registered with a 1-day interval in my real time zone, **When** the next
   08:00 local arrives, **Then** the reminder arrives within 5 minutes, and after I confirm it the
   next watering date shown is one day later.

---

### Edge Cases

- The free database or service plan changes its terms or limits before or after deployment: the
  recorded findings must make this visible so the owner can react.
- The service restarts while the monitor is checking: a brief failed check must not be treated as
  data loss; stored data and pending reminders survive.
- The test bot and the real bot are mixed up: the test bot's token must never be configured in
  production, and the production token never used in tests.
- A secret is accidentally committed: it must be rotated, since removing it from history is not
  enough.
- The clock-offset testing setting is left on in production: it must be off when verification ends.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The bot MUST run continuously in the cloud on free plans, without depending on the
  owner's computer.
- **FR-002**: Persistent data MUST live in a managed cloud database separate from the service's
  own storage, so redeploys and restarts do not erase it.
- **FR-003**: A real bot identity MUST exist for production, distinct from any identity used for
  tests.
- **FR-004**: Secrets (bot token, webhook secrets, database connection) MUST exist only in the
  hosting service's environment settings, never in the repository, logs or documents.
- **FR-005**: The service MUST expose a health address that answers healthy (200) when the bot
  and its database are reachable.
- **FR-006**: An external monitor MUST check the health address every 10 minutes and alert the
  owner through a configured contact when it fails.
- **FR-007**: The service MUST be created from the repository's declared service configuration,
  so it can be recreated without manual guesswork.
- **FR-008**: After each redeploy, due and pending reminders MUST still be delivered (FR-014 of 001).
- **FR-009**: The verification results of the 12 quickstart scenarios MUST be recorded with date
  and outcome.
- **FR-010**: The current free-tier terms of the chosen services MUST be checked and recorded
  before declaring the deployment complete.
- **FR-011**: Deployment MUST NOT change the bot's functional behaviour; any defect found must be
  handled as a fix to feature 001 or a new feature.

### Key Entities

- **Deployment environment**: The set of cloud services (service host, database, monitor) and the
  settings that make the bot run; holds the secrets.
- **Verification record**: Dated list of scenarios checked in production with expected result,
  actual result and pass/fail.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The health address answers 200 and `/start` replies within 10 seconds of being sent.
- **SC-002**: The bot remains responsive after at least 24 hours without any user message.
- **SC-003**: An induced outage produces an alert to the owner within 15 minutes.
- **SC-004**: 12 of 12 quickstart scenarios pass in production, or each failure is recorded with
  a follow-up.
- **SC-005**: A reminder pending during a redeploy is delivered afterwards; none is lost.
- **SC-006**: The first real 08:00 reminder arrives within 5 minutes of 08:00 in the owner's time
  zone.
- **SC-007**: Total monthly cost of the deployment is zero, with the plan terms verified and
  recorded.
- **SC-008**: A search of the repository finds no secret values.

## Assumptions

- **Chosen services (owner decision)**: Neon (database), Render (service, Docker, free plan),
  UptimeRobot (monitoring, free plan), BotFather (bot identity). Changing providers is a new
  decision, not part of this feature.
- **Idle behaviour**: the free service plan may sleep when idle; the 10-minute monitor is the
  mechanism that keeps it awake, and SC-002 verifies that it works.
- **Owner-run steps**: account creation and secret entry are done by the owner in each
  provider's dashboard; they cannot be automated here.
- **Single instance**: one service instance and one database; no high availability or scaling is
  required.
- **Region and legal**: no specific data-residency requirement; the bot stores only chat ids,
  time zones and plant data.
- **Replaces**: tasks T059 and T062–T068 of `001-plant-watering-reminders/tasks.md`.
- **Out of scope**: changes to bot features, paid plans, custom domains, CI/CD pipelines,
  multi-region setups and backups beyond the provider's defaults.
