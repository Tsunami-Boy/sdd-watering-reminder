# Data Model: Plant Watering Reminders

All timestamps are stored as UTC `timestamptz`. Local dates and the 08:00 send time are computed
from the user's IANA time zone at read time, never stored as local strings.

## User

| Field | Type | Rules |
|-------|------|-------|
| `chat_id` | bigint, primary key | Telegram chat identifier; one user per private chat |
| `timezone` | text, nullable | Valid IANA zone name; null until `/zona` is completed |
| `created_at` | timestamptz | Set on first `/start` |

Derived (not stored): `hemisphere` (north/south) from the zone; `season` (summer/winter) from
hemisphere and the current local month.

## Plant

| Field | Type | Rules |
|-------|------|-------|
| `id` | bigint, primary key | Generated |
| `chat_id` | bigint, FK → User | On delete cascade |
| `name` | text | Required, 1–40 characters after trimming, unique per user (case-insensitive) |
| `plant_type` | text | Required, 1–60 characters |
| `summer_days` | integer | Whole number, 1–365 |
| `winter_days` | integer | Whole number, 1–365 |
| `last_watered_on` | date | Local date in the user's zone; set to the registration day (FR-013) and to the confirmation day (FR-012) |
| `created_at` | timestamptz | |

Uniqueness: `(chat_id, lower(name))`.

Derived: `next_due_on` = `last_watered_on` + interval of the season in effect on `last_watered_on`.
Rationale: the interval is chosen on the day of watering, as stated in FR-012.

## Reminder

One row per plant that is currently due and not confirmed. At most one per plant (FR-011, SC-003).

| Field | Type | Rules |
|-------|------|-------|
| `plant_id` | bigint, primary key, FK → Plant | On delete cascade (deleting a plant stops reminders) |
| `due_on` | date | Local date on which watering became due |
| `next_send_at` | timestamptz | When the next message is allowed to be sent |
| `last_sent_at` | timestamptz, nullable | Set after each successful send |
| `send_count` | integer | Number of messages sent for this watering |
| `message_id` | bigint, nullable | Last Telegram message id, used to update the message after confirming |

### State transitions

```text
(no reminder) --[local date >= next_due_on and 08:00 reached]--> PENDING (row created, next_send_at = now)
PENDING --[send ok]--> PENDING (next_send_at = next slot: 12:00, 16:00, 20:00, else 08:00 next day)
PENDING --[send fails]--> PENDING (unchanged; retried next tick; failure logged)
PENDING --[user confirms]--> (row deleted; Plant.last_watered_on = local today)
PENDING --[plant deleted]--> (row deleted by cascade)
PENDING --[user changes time zone]--> PENDING (next_send_at recomputed for the new zone, no duplicate)
```

## Queries the scheduler needs

1. Plants with no reminder whose `next_due_on <= local today` and whose local time is at/after 08:00
   → create `Reminder`.
2. Reminders with `next_send_at <= now` → claimed atomically (`FOR UPDATE SKIP LOCKED`; their
   `next_send_at` is pushed 120 s ahead as a lease) → send → `record_sent` sets the real next slot.
   If the send fails the lease expires and the next tick retries.

## Validation rules mapped to the spec

| Rule | Requirement |
|------|-------------|
| Time zone must exist before a plant is created | FR-005 |
| Intervals are positive whole numbers; name non-empty and unique | FR-006 |
| Reminder rows survive restarts | FR-014 |
| Data keyed by `chat_id` | FR-015 |
