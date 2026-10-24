# Verification Record: Manual Watering

| Date | Check | Expected | Actual | Pass |
|------|-------|----------|--------|------|
| 2026-10-23 | `/start` and command menu | `/regar` listed | Listed (owner confirmed) | Yes |
| 2026-10-23 | `/regar` → plant → No | "No se registró ningún riego"; date unchanged | As expected (owner confirmed) | Yes |
| 2026-10-23 | `/regar` → plant → Sí | Today + seasonal interval; `/plantas` agrees | As expected (owner confirmed) | Yes |

## Not yet checked in production

- Pending reminder cleared by `/regar` and old "Ya regué" inactive (quickstart step 5, needs `CLOCK_OFFSET_HOURS`; covered by automated tests T012–T014)
