"""Apply only position-constrained substitutions from the eight specified pairs."""

from .regex_validator import compact_text, matching_formats

TO_DIGIT = dict(zip("OISBZAGT", "01582467"))
TO_LETTER = {digit: letter for letter, digit in TO_DIGIT.items()}


def fix_confusions(raw_text: str, vehicle_type: str | None = None) -> tuple[str, list[dict]]:
    compact = compact_text(raw_text)
    if matching_formats(compact, vehicle_type):
        return compact, []
    if len(compact) not in (7, 8, 9):
        return compact, []
    corrected, changes = [], []
    for index, character in enumerate(compact):
        expected_letter = index == 2 or (len(compact)==9 and index==3 and compact[3].isalpha())
        replacement = TO_LETTER.get(character, character) if expected_letter else TO_DIGIT.get(character, character)
        corrected.append(replacement)
        if replacement != character:
            changes.append({"index": index, "from": character, "to": replacement})
    text = "".join(corrected)
    return (text, changes) if matching_formats(text, vehicle_type) else (compact, [])
