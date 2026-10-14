"""Validation of the data the user types when registering a plant."""

NAME_MAX = 40
TYPE_MAX = 60
INTERVAL_MIN = 1
INTERVAL_MAX = 365


class ValidationError(ValueError):
    """The message is user-facing (Spanish)."""


def validate_name(text: str) -> str:
    name = text.strip()
    if not name or len(name) > NAME_MAX:
        raise ValidationError(f"El nombre debe tener entre 1 y {NAME_MAX} caracteres.")
    return name


def validate_type(text: str) -> str:
    plant_type = text.strip()
    if not plant_type or len(plant_type) > TYPE_MAX:
        raise ValidationError(f"El tipo debe tener entre 1 y {TYPE_MAX} caracteres.")
    return plant_type


def parse_interval(text: str) -> int:
    raw = text.strip()
    if not raw.isascii() or not raw.isdigit():
        raise ValidationError("Escribe un número entero de días (por ejemplo 7).")
    days = int(raw)
    if not INTERVAL_MIN <= days <= INTERVAL_MAX:
        raise ValidationError(f"Los días deben estar entre {INTERVAL_MIN} y {INTERVAL_MAX}.")
    return days
