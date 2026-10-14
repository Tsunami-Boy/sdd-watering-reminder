"""All user-facing texts (Spanish)."""

from datetime import date

from waterbot.domain.models import Plant

CONFIRM_BUTTON = "✅ Ya regué"

COMMANDS = [
    ("start", "Ver los comandos disponibles"),
    ("zona", "Elegir tu zona horaria"),
    ("agregar", "Registrar una planta"),
    ("plantas", "Ver tus plantas"),
    ("eliminar", "Eliminar una planta"),
    ("cancelar", "Cancelar lo que estás haciendo"),
]

SEASON_ES = {"summer": "verano", "winter": "invierno"}


def welcome() -> str:
    lines = ["¡Hola! Soy tu recordatorio de riego 🌱", "", "Comandos disponibles:"]
    lines += [f"/{name} — {description}" for name, description in COMMANDS]
    lines += ["", "Empieza eligiendo tu zona horaria con /zona."]
    return "\n".join(lines)


HELP = "No entendí eso. Usa /start para ver los comandos disponibles."
NEED_TIMEZONE = "Primero elige tu zona con /zona."
CANCELLED = "Listo, cancelado."
NOTHING_TO_CANCEL = "No hay nada que cancelar."
ZONA_CHOOSE_REGION = "Elige tu región (o escribe tu zona, por ejemplo America/Santiago):"
ZONA_INVALID = (
    "Esa no es una zona horaria válida. Elige una de la lista o escribe una como "
    "America/Santiago, Europe/Madrid o Asia/Tokyo."
)
ZONA_CHOOSE_ZONE = "Elige tu zona horaria:"
NO_PLANTS = "Aún no tienes plantas. Registra una con /agregar."
ASK_NAME = "¿Cómo se llama la planta? (máximo 40 caracteres)"
ASK_TYPE = "¿Qué tipo de planta es? (por ejemplo: Dólar, Suculenta)"
ASK_SUMMER = "¿Cada cuántos días hay que regarla en verano? (número entero)"
ASK_WINTER = "¿Cada cuántos días hay que regarla en invierno? (número entero)"
NAME_TAKEN = "Ya tienes una planta con ese nombre. Elige otro nombre."
DELETE_CHOOSE = "¿Qué planta quieres eliminar?"
DELETE_CANCELLED = "No se eliminó nada."
PLANT_GONE = "Esa planta ya no existe."
REMINDER_INACTIVE = "Este recordatorio ya no está activo."


def zona_saved(zone: str, local_time: str, season: str) -> str:
    return (
        f"Zona horaria: {zone}\nHora local: {local_time}\nTemporada: {SEASON_ES[season]}\n\n"
        "Ahora puedes registrar plantas con /agregar."
    )


def fmt_date(day: date) -> str:
    return day.strftime("%d/%m/%Y")


def plant_saved(plant: Plant, first_reminder: date) -> str:
    return (
        f"Planta registrada ✅\nNombre: {plant.name}\nTipo: {plant.plant_type}\n"
        f"Riego en verano: cada {plant.summer_days} días\n"
        f"Riego en invierno: cada {plant.winter_days} días\n"
        f"Primer recordatorio: {fmt_date(first_reminder)} a las 08:00"
    )


def plant_line(plant: Plant, next_due: date) -> str:
    return (
        f"🌿 {plant.name} ({plant.plant_type})\n"
        f"   Verano: {plant.summer_days} días · Invierno: {plant.winter_days} días\n"
        f"   Próximo riego: {fmt_date(next_due)}"
    )


def delete_ask(name: str) -> str:
    return f"¿Eliminar «{name}»?"


def deleted(name: str) -> str:
    return f"«{name}» eliminada. No recibirás más recordatorios de esa planta."


def reminder_text(name: str, plant_type: str, repeat: bool) -> str:
    prefix = "Recordatorio: " if repeat else ""
    return f"{prefix}💧 Hoy toca regar «{name}» ({plant_type})"


def watered(next_due: date) -> str:
    return f"Regada ✅. Próximo riego: {fmt_date(next_due)}"
