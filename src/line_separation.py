"""One/two-line plate separation using horizontal foreground projection."""

import numpy as np

from .binarization import validate_binary


def _runs(active: np.ndarray) -> list[tuple[int, int]]:
    changes = np.diff(np.pad(active.astype(np.int8), (1, 1)))
    return list(zip(np.flatnonzero(changes == 1).tolist(), np.flatnonzero(changes == -1).tolist()))


def separate_lines(
    binary: np.ndarray,
    *,
    valley_ratio: float = 0.08,
    min_gap_fraction: float = 0.03,
) -> list[tuple[int, int]]:
    """Return top-to-bottom, half-open row ranges in plate coordinates.

    A split requires a central whitespace valley with substantial foreground
    on both sides. Empty masks yield no lines, not an invented line label.
    """
    validate_binary(binary)
    if not 0 <= valley_ratio < 1 or not 0 < min_gap_fraction < 0.5:
        raise ValueError("invalid projection thresholds")
    projection = np.count_nonzero(binary, axis=1)
    active_rows = np.flatnonzero(projection)
    if not len(active_rows):
        return []
    top, bottom = int(active_rows[0]), int(active_rows[-1]) + 1
    text_height = bottom - top
    low = projection <= projection.max() * valley_ratio
    candidates = []
    for start, end in _runs(low):
        gap_center = (start + end) / 2
        if end - start < max(2, round(text_height * min_gap_fraction)):
            continue
        if not top + 0.2 * text_height <= gap_center <= top + 0.8 * text_height:
            continue
        above = np.flatnonzero(projection[top:start]) + top
        below = np.flatnonzero(projection[end:bottom]) + end
        if not len(above) or not len(below):
            continue
        if min(len(above), len(below)) < max(2, 0.15 * text_height):
            continue
        total = projection.sum()
        if min(projection[top:start].sum(), projection[end:bottom].sum()) < 0.15 * total:
            continue
        candidates.append((end - start, start, end, above, below))
    if not candidates:
        return [(top, bottom)]
    _, _, _, above, below = max(candidates, key=lambda item: item[0])
    return [(int(above[0]), int(above[-1]) + 1), (int(below[0]), int(below[-1]) + 1)]


def group_component_lines(boxes: list[tuple[int,int,int,int]], image_height: int) -> list[list[tuple[int,int,int,int]]]:
    """Recover two tilted rows whose vertical extents have no whitespace gap.

    Use glyph-sized component centers to infer row membership, retaining whole
    boxes rather than cutting a glyph at a horizontal split through its body.
    Empty/ambiguous evidence yields no fallback, leaving projection in charge.
    """
    references=[box for box in boxes if box[3] >= image_height * 0.18 and 0.15 <= box[2]/box[3] <= 1.2]
    if len(references) < 4:
        return []
    typical=float(np.median([box[3] for box in references]))
    references=[box for box in references if 0.5*typical <= box[3] <= 1.5*typical]
    references.sort(key=lambda box:box[1]+box[3]/2)
    if len(references) < 4:
        return []
    centers=np.array([box[1]+box[3]/2 for box in references])
    cut=int(np.argmax(np.diff(centers)))+1
    if min(cut,len(references)-cut) < 2 or centers[cut]-centers[cut-1] < 0.6*typical:
        return []
    middle=(centers[cut-1]+centers[cut])/2
    # A tall side frame or a border connected to a glyph must not determine a
    # row's height: it otherwise makes the real second row fail the height filter.
    glyphs = [box for box in boxes if 0.5*typical <= box[3] <= 1.5*typical
              and 0.1 <= box[2]/box[3] <= 1.2]
    return [[box for box in glyphs if (box[1]+box[3]/2 < middle)==upper] for upper in (True,False)]
