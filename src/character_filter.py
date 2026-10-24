"""Geometric filtering of WP2 character candidates."""


def filter_characters(
    boxes: list[tuple[int, int, int, int]],
    line_shape: tuple[int, int],
    *,
    min_area_fraction: float = 0.003,
    max_area_fraction: float = 0.35,
    min_height_fraction: float = 0.45,
    min_aspect: float = 0.2,
    max_aspect: float = 1.0,
) -> list[tuple[int, int, int, int]]:
    height, width = line_shape
    if min(height, width) <= 0:
        raise ValueError("line shape must be positive")
    if not (0 <= min_area_fraction < max_area_fraction <= 1 and 0 < min_height_fraction <= 1 and 0 < min_aspect < max_aspect):
        raise ValueError("invalid character filter thresholds")
    area = height * width
    return [
        (x, y, w, h) for x, y, w, h in boxes
        if w > 0 and h > 0 and 0 <= x < x + w <= width and 0 <= y < y + h <= height
        and min_area_fraction <= w * h / area <= max_area_fraction
        and h >= min_height_fraction * height and min_aspect <= w / h <= max_aspect
    ]
