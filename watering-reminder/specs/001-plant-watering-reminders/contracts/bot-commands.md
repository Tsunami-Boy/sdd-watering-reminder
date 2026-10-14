# Contract: Bot Commands

Texts are in Spanish. Only private chats are served; messages from groups are ignored.
Commands are registered with Telegram (`setMyCommands`) so they appear in the command menu.

## Commands

| Command | Purpose | Requirements |
|---------|---------|--------------|
| `/start` | Welcome message listing every command with a one-line description; creates the user | FR-001 |
| `/zona` | Choose or change the time zone | FR-002, FR-003 |
| `/agregar` | Register a plant (guided) | FR-004–FR-006 |
| `/plantas` | List the user's plants | FR-007 |
| `/eliminar` | Delete a plant (choose, then confirm) | FR-008 |
| `/cancelar` | Abort the current guided flow | FR-016 |

Any other text or unknown command gets a short help message pointing to `/start`.

## `/zona` flow

1. Bot shows an inline keyboard of regions.
2. User taps a region → bot shows zones of that region, paged (e.g. 10 per page, with ◀ ▶).
3. User taps a zone → bot saves it and replies with the zone, local time and current season,
   e.g. `Zona horaria: America/Santiago · Hora local: 14:05 · Temporada: verano`.
4. Alternative: the user sends a zone name as text. Valid → same as step 3. Invalid → error message
   and the keyboard again; stored value unchanged.

Callback data: `tz:r:<region>`, `tz:p:<region>:<page>`, `tz:s:<zone>` (each ≤ 64 bytes; zones
longer than that are selected by index within the region).

## `/agregar` flow (ConversationHandler)

Requires a time zone; otherwise replies "Primero elige tu zona con /zona" and ends.

| Step | Bot asks | Valid input | On invalid |
|------|----------|-------------|-----------|
| 1 | Nombre de la planta | 1–40 chars, not already used (case-insensitive) | Explain, ask again |
| 2 | Tipo de planta | 1–60 chars | Ask again |
| 3 | Días entre riegos en verano | whole number 1–365 | Ask again |
| 4 | Días entre riegos en invierno | whole number 1–365 | Ask again |

On success the bot replies with a summary (name, type, both intervals) and the date of the first
reminder. `/cancelar` at any step ends the flow without saving.

## `/plantas` output

One line per plant: name, type, summer days, winter days, next watering date (local). With no
plants: a message explaining how to use `/agregar`.

## `/eliminar` flow

1. Inline keyboard with one button per plant.
2. User taps a plant → bot asks "¿Eliminar <nombre>?" with Sí / No buttons.
3. Sí → plant and any pending reminder are removed; No → nothing changes.

## Reminder message

Text: `💧 Hoy toca regar «<nombre>» (<tipo>)` with one inline button `✅ Ya regué`.
Repeats (same text, prefixed `Recordatorio:`) are sent as new messages.

Callback data: `water:<plant_id>`.

- On tap, the bot answers the callback, edits the message to `Regada ✅. Próximo riego: <fecha>`,
  deletes the reminder, and sets `last_watered_on` to the local date.
- If the reminder no longer exists (already confirmed or plant deleted), the bot answers
  "Este recordatorio ya no está activo" and does nothing else.
- Callbacks from a chat other than the plant owner's are rejected.
