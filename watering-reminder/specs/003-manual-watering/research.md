# Research: Manual Watering

## 1. Reuse of the confirmation logic

- **Decision**: new `water_plant()` in `services.py`, next to `confirm_watering()`. It loads the
  plant (owner-checked), deletes the plant's reminder if one exists, calls `mark_watered` with
  today's local date, and returns the same `WateredResult`.
- **Rationale**: `confirm_watering()` returns `None` when no reminder exists, which is exactly the
  normal case here, so it cannot be reused as is. Changing it would alter the "Ya regué" contract
  (second tap must stay inactive).
- **Alternatives**: add a flag to `confirm_watering()` (mixes two contracts); duplicate the logic
  in the handler (untestable without Telegram).

## 2. Interaction pattern

- **Decision**: stateless buttons, same as `/eliminar`: `reg:<id>` → confirmation with
  `regok:<id>` / `regno`.
- **Rationale**: no per-chat state to lose on restart; old messages are safe because the action is
  evaluated against the plant and date at tap time.
- **Alternatives**: a ConversationHandler (needs state, nothing gained).

## 3. Pending reminder and the scheduler

- **Decision**: delete the reminder row in the same use case before `mark_watered`; no scheduler
  change.
- **Rationale**: the scheduler only creates reminders for plants with `next_due_on <= today`; after
  `mark_watered` that is false until the new due date. The old Telegram message stays in the chat;
  tapping "Ya regué" there hits the existing "no longer active" path because the reminder row is
  gone.
- **Risk**: the scheduler may be sending that reminder at the same moment (lease of 120 s). Worst
  case: one extra message arrives right after the confirmation. Acceptable; the row is already
  deleted so it is not repeated.

## 4. `/cancelar`

- **Decision**: no change. The flow keeps no state, so there is nothing to abort; `/cancelar`
  answers "nothing to cancel" as it does for `/eliminar`, and no data changes (FR-010 holds).
