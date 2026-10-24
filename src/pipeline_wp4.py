"""Post-process raw OCR, retaining corrections and unresolved vehicle ambiguity."""

import numpy as np

from .confusion_fixer import fix_confusions
from .province_validator import ProvinceRegistry
from .regex_validator import compact_text, format_plate, matching_formats


def postprocess(raw_text: str, confidences: list[float], *, vehicle_type: str | None = None, registry: ProvinceRegistry | None = None) -> dict:
    registry = registry or ProvinceRegistry()
    compact = compact_text(raw_text)
    if confidences and (len(confidences) != len(compact) or not all(np.isfinite(c) and 0 <= c <= 1 for c in confidences)):
        raise ValueError("confidences must match the alphanumeric OCR string and lie in [0,1]")
    text, changes = fix_confusions(raw_text, vehicle_type)
    formats = matching_formats(text, vehicle_type)
    registration = registry.lookup(text[:2]) if formats else None
    possible_types = sorted({"car" if name.startswith("car") else "motorcycle" for name in formats})
    resolved_type = possible_types[0] if len(possible_types) == 1 else "unknown"
    return {
        "raw_text": raw_text, "corrected_text": text,
        "plate_text": format_plate(text, formats[0]) if formats else None,
        "is_valid": bool(formats and registration),
        "province": registration["province"] if registration and registration["entity_type"] == "province" else None,
        "registration_authority": registration["province"] if registration else None,
        "vehicle_type": resolved_type, "possible_vehicle_types": possible_types,
        "confidence": float(np.mean(confidences)) if confidences else None,
        "corrections": changes, "matching_formats": formats,
        "validation_scope": "supported_format_and_registration_code",
    }
