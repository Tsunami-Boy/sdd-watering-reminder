# Quickstart: validating `/regar`

## Automated

```bash
uv run pytest tests/integration/test_regar_flow.py
uv run pytest && uv run ruff check .
```

Expected: all tests pass; the `/regar` tests cover SC-002, SC-003 and SC-004.

## Manual (against the live bot, after deploy)

1. Register a plant with a 7-day summer interval (`/agregar`). Run `/plantas`; note the next date.
2. `/regar` → choose the plant → `No`. `/plantas` shows the same date (SC-003).
3. `/regar` → choose the plant → `Sí`. Reply shows today + the seasonal interval (SC-002);
   `/plantas` agrees.
4. With no plants (new chat) or no time zone, `/regar` shows the matching guidance.
5. With `CLOCK_OFFSET_HOURS` set so a reminder becomes pending, `/regar` → `Sí` for that plant:
   no repeats follow, and tapping "Ya regué" on the old message answers "ya no está activo"
   (SC-004). Remove `CLOCK_OFFSET_HOURS` afterwards.
6. `/start` and the command menu list `/regar`.
