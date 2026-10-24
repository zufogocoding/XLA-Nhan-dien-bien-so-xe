"""Build raw OCR text in WP2 reading order, preserving per-character scores."""


def build_sequence(details: list[dict]) -> dict:
    if any(len(item["char"]) != 1 or not (item["char"].isdigit() or "A" <= item["char"] <= "Z" or item["char"] in "-.") for item in details):
        raise ValueError("predictions must contain individual alphanumeric characters")
    glyphs = [dict(item) for item in details if item["char"] not in "-."]
    return {
        "raw_text": "".join(item["char"] for item in glyphs),
        "confidences": [item["confidence"] for item in glyphs],
        "char_details": glyphs,
    }
