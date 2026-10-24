# Data Model: Manual Watering

No new tables or columns. The migration in `storage/schema.sql` is unchanged.

## Changes in behaviour

| Entity | Change |
|--------|--------|
| Plant | `last_watered_on` is set to the user's local today on confirmed `/regar`. `next_due_on` stays derived (last watered + interval of the season on that day). |
| Reminder | Row for the plant is deleted on confirmed `/regar`, if it exists. |

### State transitions added

```text
(no reminder) --[/regar confirmed]--> (no reminder), Plant.last_watered_on = local today
PENDING       --[/regar confirmed]--> (row deleted),  Plant.last_watered_on = local today
any           --[/regar declined]---> unchanged
```

## Validation rules

| Rule | Requirement |
|------|-------------|
| Plant must belong to the chat | FR-011 |
| User needs a time zone | FR-009 |
| Date is always local today, never user-supplied | spec assumptions |
