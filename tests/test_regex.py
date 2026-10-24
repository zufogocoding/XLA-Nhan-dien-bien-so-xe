import pytest

from src.confusion_fixer import TO_DIGIT, fix_confusions
from src.pipeline_wp4 import postprocess
from src.regex_validator import format_plate, matching_formats
from src.province_validator import ProvinceRegistry


@pytest.mark.parametrize("raw,kind,expected", [("51F12345","car_5","51F-123.45"),("29A1234","car_4","29A-1234"),("59X112345","motorcycle","59X1-123.45")])
def test_three_requested_plate_formats(raw, kind, expected):
    assert kind in matching_formats(raw)
    assert format_plate(raw,kind) == expected


@pytest.mark.parametrize("letter,digit", list(TO_DIGIT.items()))
def test_all_eight_confusion_pairs_use_character_position(letter, digit):
    corrected, changes = fix_confusions(f"51F12{letter}45")
    assert corrected == f"51F12{digit}45" and changes
    corrected, _ = fix_confusions(f"51{digit}12345")
    assert corrected == f"51{letter}12345"


def test_type_ambiguity_and_current_registration_lookup():
    unknown = postprocess("51F12345", [0.9] * 8)
    assert unknown["is_valid"] and unknown["vehicle_type"] == "unknown"
    assert postprocess("51F12345", [], vehicle_type="car")["vehicle_type"] == "car"
    registry = ProvinceRegistry()
    assert registry.lookup("61")["province"] == "Hồ Chí Minh"
    assert registry.lookup("34")["province"] == "Hải Phòng"
    assert registry.lookup("80")["entity_type"] == "central_authority"
    assert postprocess("80A12345", [0.8] * 8)["province"] is None
    assert not postprocess("00A12345", [0.8] * 8)["is_valid"]
    assert not postprocess("<script>", [])["is_valid"]
