<!--
Sync Impact Report
- Version change: (template, unversioned) → 1.0.0
- Modified principles: none (initial adoption)
- Added sections: Core Principles (5), Technical Constraints, Development Workflow, Governance
- Removed sections: none
- Deferred TODOs:
  - TODO(PERSISTENCE): storage mechanism for reminders not chosen; decide in /speckit-plan.
  - TODO(HOSTING): where the bot runs (local, VPS, serverless) not chosen; decide in /speckit-plan.
-->
# Watering Reminder Constitution

## Core Principles

### I. Simplicity First
The project MUST start with the smallest solution that satisfies the spec. Every added
dependency, abstraction layer, or service MUST be justified in the plan. Features not
required by the current spec MUST NOT be built (YAGNI).
Rationale: this is a personal project; maintenance cost matters more than extensibility.

### II. Test-First for Reminder Logic
Logic that decides when a plant must be watered (scheduling, intervals, snooze, timezone
handling) MUST have tests written before the implementation, and those tests MUST fail
before the code is written. Telegram API calls MUST be isolated behind an interface so the
logic can be tested without network access.
Rationale: scheduling bugs are silent and only show up days later.

### III. Reliable Reminders
A due reminder MUST NOT be lost silently. If a send fails, the bot MUST retry and MUST log
the failure. Pending reminders MUST survive a bot restart. Reminder times MUST be computed
with explicit timezones.
Rationale: the only value of the bot is that the reminder arrives.

### IV. Privacy and Secrets
The Telegram bot token and any credentials MUST be read from environment variables and MUST
NOT be committed to git. The bot MUST store only the data needed to send reminders (chat
identifier, plant names, schedules) and MUST NOT send user data to third-party services
other than Telegram.
Rationale: leaked tokens allow bot takeover; minimal data limits exposure.

### V. Specification as Source of Truth
Every change to behavior MUST go through the Spec Kit flow: spec → plan → tasks →
implement. If the code and the spec disagree, the spec MUST be updated or the code fixed
before the work is considered done.
Rationale: keeps AI-assisted work predictable and reviewable.

## Technical Constraints

- The product is a Telegram bot.
- The implementation language is Python 3.12, with `uv` for dependency management, matching
  the Devbox environment. Project dependencies MAY be added to `devbox.json` when needed.
- Bot dependencies MUST be declared in the project's `pyproject.toml` and locked.
- User-facing messages are in Spanish unless a spec states otherwise.
- Persistence mechanism and hosting are decided in the plan (see Sync Impact Report TODOs).

## Development Workflow

- This is a solo personal project: pull request review is NOT required.
- Work MAY be committed directly to `main`, in small commits with descriptive messages.
- Tests for reminder logic MUST pass before a task is marked complete.
- Each plan MUST include a Constitution Check against the principles above.

## Governance

This constitution supersedes other project practices. Amendments are made with
`/speckit-constitution`, and MUST update the version and the last-amended date.

Versioning follows semantic versioning: MAJOR for removing or redefining a principle in an
incompatible way, MINOR for adding a principle or materially expanding guidance, PATCH for
wording clarifications.

Compliance is checked during `/speckit-plan` (Constitution Check) and when reviewing
completed tasks. Any deviation from a principle MUST be justified in writing in the plan.

**Version**: 1.0.0 | **Ratified**: 2026-10-13 | **Last Amended**: 2026-10-13
