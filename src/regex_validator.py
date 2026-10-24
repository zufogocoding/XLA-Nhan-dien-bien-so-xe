"""Syntactic validation for the three civilian plate formats in the brief."""

import re

PATTERNS = {
    "car_5": re.compile(r"[0-9]{2}[A-Z][0-9]{5}"),
    "car_4": re.compile(r"[0-9]{2}[A-Z][0-9]{4}"),
    "motorcycle": re.compile(r"[0-9]{2}[A-Z](?:[0-9]|[A-Z])?[0-9]{5}"),
}


def compact_text(text: str) -> str:
    text = text.upper().strip()
    if not text or not re.fullmatch(r"[A-Z0-9.\-\s]+", text, flags=re.ASCII):
        return ""
    return re.sub(r"[.\-\s]", "", text)


def matching_formats(text: str, vehicle_type: str | None = None) -> list[str]:
    if vehicle_type not in (None, "unknown", "car", "motorcycle"):
        raise ValueError("vehicle_type must be car, motorcycle or unknown")
    compact = compact_text(text)
    return [name for name, pattern in PATTERNS.items() if pattern.fullmatch(compact) and (vehicle_type in (None, "unknown") or (name.startswith("car") if vehicle_type == "car" else name == "motorcycle"))]


def format_plate(text: str, format_name: str) -> str:
    compact = compact_text(text)
    if format_name not in PATTERNS or not PATTERNS[format_name].fullmatch(compact):
        raise ValueError("text does not match the requested plate format")
    digits = 4 if format_name == "car_4" else 5
    prefix, serial = compact[:-digits], compact[-digits:]
    return prefix + "-" + (serial if digits == 4 else serial[:3] + "." + serial[3:])
