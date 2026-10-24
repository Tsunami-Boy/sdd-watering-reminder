# Contract: `/regar`

Addition to `001/contracts/bot-commands.md`. Texts are in Spanish.

| Command | Purpose | Requirements |
|---------|---------|--------------|
| `/regar` | Register a watering done by the user (choose plant, then confirm) | FR-001–FR-012 |

`/regar` appears in the command menu and in the `/start` welcome list.

## Flow

1. `/regar`
   - No time zone → "Primero elige tu zona con /zona".
   - No plants → the existing no-plants message pointing to `/agregar`.
   - Otherwise: "¿Qué planta regaste?" with one button per plant (`reg:<plant_id>`).
2. Tap a plant (message is edited) → "¿Confirmas que regaste «<nombre>»?" with `Sí` (`regok:<plant_id>`)
   and `No` (`regno`).
   - Plant not found or not the chat's → "esa planta ya no existe", nothing changes.
3. `Sí` → plant's `last_watered_on` = local today; its pending reminder, if any, is deleted; message
   edited to `Regada ✅ «<nombre>». Próximo riego: <dd/mm/aaaa>`.
   - Plant not found or not the chat's → plant-gone message, nothing changes.
4. `No` → message edited to "No se registró ningún riego." Nothing changes.

Callback data: `reg:<id>`, `regok:<id>`, `regno` (all ≤ 64 bytes).

Old messages from a previous `/regar` stay usable: the action is evaluated at tap time.
