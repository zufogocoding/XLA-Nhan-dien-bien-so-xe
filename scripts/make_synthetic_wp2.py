"""Generate synthetic Vietnamese plates with exact character boxes.

The public dataset only annotates plate boxes, not characters. This generator
provides reproducible ground truth for WP2 segmentation tests and evaluation.
It renders realistic one-line and two-line layouts, then applies mild
rotation/perspective, blur, lighting and noise.
"""

import argparse
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.augmentation import (  # noqa: E402
    add_noise,
    brightness_contrast,
    gaussian_blur,
)


FONT_CANDIDATES = (
    "/usr/share/fonts/google-noto/NotoSans-CondensedBold.ttf",
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/open-sans/OpenSans-Bold.ttf",
    "/usr/share/fonts/google-carlito-fonts/Carlito-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
)


ONE_LINE_TEXTS = (
    "51F-123.45",
    "30A-970.61",
    "29C-660.73",
    "89A-088.24",
    "30E-755.31",
    "51G-234.56",
    "30K-555.55",
    "29A-372.29",
)
TWO_LINE_TEXTS = (
    ("29C", "660.73"),
    ("30G", "582.05"),
    ("30M", "4253"),
    ("51F1", "234.56"),
    ("80B", "123.45"),
    ("29A1", "888.88"),
    ("30E", "545.15"),
    ("89A", "123.27"),
)
PLATE_COLORS = (
    ((238, 238, 232), (25, 25, 25)),  # white plate, black text
    ((246, 208, 55), (25, 25, 25)),  # yellow plate, black text
    ((22, 48, 122), (242, 242, 242)),  # blue plate, white text
)
ALPHABET = "ABCDEFGHKLMNPRSTUVXYZ"
DIGITS = "0123456789"


@dataclass
class SyntheticPlate:
    image: np.ndarray
    line_type: str
    chars: list[dict]


def find_font_path() -> Path:
    for candidate in FONT_CANDIDATES:
        path = Path(candidate)
        if path.exists():
            return path
    for pattern in ("*Sans*Bold*.ttf", "*Arial*Bold*.ttf"):
        for path in sorted(Path("/usr/share/fonts").rglob(pattern)):
            if "CJK" not in path.name and "Mono" not in path.name:
                return path
    raise FileNotFoundError(
        "no CJK-free bold TTF found; install DejaVu Sans or Arial"
    )


def _random_text(rng: random.Random) -> tuple[list[str], str]:
    if rng.random() < 0.5:
        return [rng.choice(ONE_LINE_TEXTS)], "1_line"
    return list(rng.choice(TWO_LINE_TEXTS)), "2_line"


def _render_line(
    draw: ImageDraw.ImageDraw,
    tokens: list[str],
    font: ImageFont.FreeTypeFont,
    center: tuple[float, float],
    fill: tuple[int, int, int],
    gap_scale: float = 1.0,
) -> list[dict]:
    """Draw tokens centered at ``center`` and return character ink boxes."""
    spacing = max(1.0, font.size * 0.12 * gap_scale)
    advances = []
    total = 0.0
    for index, token in enumerate(tokens):
        advance = font.getlength(token)
        advances.append(advance)
        total += advance
        if index + 1 < len(tokens):
            total += spacing if token.isalnum() else spacing * 0.45

    x = center[0] - total / 2
    baseline = center[1]
    boxes = []
    for token, advance in zip(tokens, advances):
        left, top, right, bottom = font.getbbox(token)
        # Place the ink bounding box exactly where the glyph is drawn.
        draw_x = x - left
        draw_y = baseline - (top + bottom) / 2
        draw.text((draw_x, draw_y), token, font=font, fill=fill)
        if token.isalnum():
            boxes.append(
                {
                    "text": token,
                    "bbox": (
                        int(round(x)),
                        int(round(draw_y + top)),
                        int(round(right - left)),
                        int(round(bottom - top)),
                    ),
                }
            )
        x += advance
        if token.isalnum():
            x += spacing
        else:
            x += spacing * 0.45
    return boxes


def render_plate(
    line_type: str | None = None,
    rng: random.Random | np.random.Generator | None = None,
) -> SyntheticPlate:
    """Render one synthetic plate and return its pixel-exact character boxes."""
    if rng is None:
        rng = random.Random(0)
    if not isinstance(rng, random.Random):
        rng = random.Random(int(rng.integers(0, 2**32 - 1)))
    if line_type is None:
        lines, line_type = _random_text(rng)
    elif line_type == "1_line":
        lines = [rng.choice(ONE_LINE_TEXTS)]
    else:
        lines = list(rng.choice(TWO_LINE_TEXTS))

    background, foreground = rng.choice(PLATE_COLORS)
    if line_type == "1_line":
        width = rng.randint(460, 540)
        height = rng.randint(105, 135)
    else:
        width = rng.randint(300, 380)
        height = rng.randint(180, 230)

    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)
    border = rng.randint(3, 6)
    draw.rectangle(
        (1, 1, width - 2, height - 2), outline=foreground, width=border
    )

    inside_h = height - 2 * border
    inside_w = width - 2 * border
    font_size = int(inside_h / max(1, len(lines)) * 0.78)
    font = ImageFont.truetype(str(find_font_path()), font_size)

    # Shrink the font until the widest line fits, so no glyph is clipped.
    for text in lines:
        spacing = max(1.0, font_size * 0.12)
        line_width = sum(font.getlength(char) for char in text)
        line_width += spacing * max(0, len(text) - 1)
        if line_width > 0.86 * inside_w:
            font_size = max(12, int(font_size * 0.86 * inside_w / line_width))
            font = ImageFont.truetype(str(find_font_path()), font_size)

    char_boxes = []
    for index, text in enumerate(lines):
        tokens = [token for token in text]
        center_y = border + inside_h * (index + 0.5) / len(lines)
        line_boxes = _render_line(
            draw, tokens, font, (width / 2, center_y), foreground
        )
        for box in line_boxes:
            box["line"] = index
        char_boxes.extend(line_boxes)

    # Small lighting gradient, like a photo rather than a flat graphic.
    array = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR).astype(np.float32)
    gradient = np.linspace(-1.0, 1.0, width, dtype=np.float32)[None, :, None]
    array += gradient * rng.uniform(3, 10)
    image_bgr = np.clip(array, 0, 255).astype(np.uint8)

    return SyntheticPlate(image_bgr, line_type, char_boxes)


def _transform_boxes(
    boxes: list[dict], matrix: np.ndarray, width: int, height: int
) -> list[dict]:
    transformed = []
    for box in boxes:
        x, y, w, h = box["bbox"]
        corners = np.array(
            [[x, y], [x + w, y], [x + w, y + h], [x, y + h]], dtype=np.float32
        ).reshape(1, 4, 2)
        warped = cv2.perspectiveTransform(corners, matrix).reshape(4, 2)
        x1, y1 = warped.min(axis=0)
        x2, y2 = warped.max(axis=0)
        x1, y1 = max(0, int(round(x1))), max(0, int(round(y1)))
        x2, y2 = min(width, int(round(x2))), min(height, int(round(y2)))
        if x2 - x1 < 2 or y2 - y1 < 2:
            continue
        if not (0 <= (x1 + x2) / 2 < width and 0 <= (y1 + y2) / 2 < height):
            continue
        transformed.append({**box, "bbox": (x1, y1, x2 - x1, y2 - y1)})
    return transformed


def _geometric_augment(
    plate: SyntheticPlate, rng: random.Random, strength: str
) -> SyntheticPlate:
    image = plate.image
    height, width = image.shape[:2]
    if strength == "easy":
        angle_range, perspective_range = 2.5, (0.0, 0.02)
    elif strength == "hard":
        angle_range, perspective_range = 10.0, (0.05, 0.12)
    else:
        angle_range, perspective_range = 5.0, (0.01, 0.05)

    scale = 1.0
    if strength == "hard":
        scale = rng.uniform(0.88, 1.0)
    matrix = cv2.getRotationMatrix2D(
        (width / 2, height / 2), rng.uniform(-angle_range, angle_range), scale
    )
    matrix3 = np.vstack([matrix, [0, 0, 1]]).astype(np.float32)

    if perspective_range[1] > 0:
        amount = rng.uniform(*perspective_range)
        source = np.array(
            [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
            dtype=np.float32,
        )
        destination = source + np.array(
            [
                [rng.uniform(-amount, amount) * width, rng.uniform(-amount, amount) * height]
                for _ in range(4)
            ],
            dtype=np.float32,
        )
        perspective = cv2.getPerspectiveTransform(source, destination)
        matrix3 = perspective @ matrix3

    warped = cv2.warpPerspective(
        image,
        matrix3,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )
    boxes = _transform_boxes(plate.chars, matrix3, width, height)
    return SyntheticPlate(warped, plate.line_type, boxes)


def make_synthetic_plate(
    seed: int,
    line_type: str | None = None,
    strength: str = "typical",
) -> SyntheticPlate:
    """Deterministic synthetic plate for tests and evaluation."""
    rng = random.Random(seed)
    plate = render_plate(line_type=line_type, rng=rng)
    plate = _geometric_augment(plate, rng, strength)

    blur = {"easy": (0.0, 1.0), "typical": (0.0, 1.5), "hard": (0.6, 2.2)}[strength]
    plate.image = gaussian_blur(plate.image, rng.uniform(*blur))
    spread = {"easy": 0.15, "typical": 0.25, "hard": 0.35}[strength]
    plate.image = brightness_contrast(
        plate.image,
        rng.uniform(-spread, spread) * 45,
        rng.uniform(1 - spread, 1 + spread),
    )
    if strength == "hard":
        plate.image = add_noise(plate.image, rng.uniform(2, 6), np.random.default_rng(seed))
    return plate


def make_dataset(
    count: int = 150,
    seed: int = 42,
    strength: str = "typical",
    half_and_half: bool = True,
) -> list[SyntheticPlate]:
    plates = []
    for index in range(count):
        line_type = None
        if half_and_half:
            line_type = "1_line" if index % 2 == 0 else "2_line"
        plates.append(
            make_synthetic_plate(seed + index, line_type=line_type, strength=strength)
        )
    return plates


def _draw_annotation(image: np.ndarray, chars: list[dict], line_type: str) -> np.ndarray:
    canvas = image.copy()
    for box in chars:
        x, y, w, h = box["bbox"]
        color = (0, 220, 0) if box["line"] == 0 else (255, 170, 0)
        cv2.rectangle(canvas, (x, y), (x + w, y + h), color, 2)
    cv2.putText(
        canvas,
        line_type,
        (4, 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 0, 255),
        1,
        cv2.LINE_AA,
    )
    return canvas


def save_dataset(
    plates: list[SyntheticPlate], output_dir: Path, seed: int = 42
) -> None:
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    annotations = {"seed": seed, "images": []}
    for index, plate in enumerate(plates):
        name = f"synthetic_{index:04d}.jpg"
        cv2.imwrite(str(images_dir / name), plate.image)
        annotations["images"].append(
            {
                "file_name": name,
                "line_type": plate.line_type,
                "chars": [
                    {"text": box["text"], "bbox": list(box["bbox"]), "line": box["line"]}
                    for box in plate.chars
                ],
            }
        )
    (output_dir / "annotations.json").write_text(
        json.dumps(annotations, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def save_showcase(plates: list[SyntheticPlate], output_path: Path) -> None:
    tiles = []
    for plate in plates:
        tile = _draw_annotation(plate.image, plate.chars, plate.line_type)
        scale = 420 / tile.shape[1]
        tile = cv2.resize(
            tile, (420, max(1, round(tile.shape[0] * scale))), interpolation=cv2.INTER_AREA
        )
        tiles.append(tile)
    height = max(tile.shape[0] for tile in tiles)
    tiles = [
        cv2.copyMakeBorder(
            tile, 0, height - tile.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(35, 35, 35)
        )
        for tile in tiles
    ]
    rows = [np.hstack(tiles[index : index + 2]) for index in range(0, len(tiles), 2)]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), np.vstack(rows))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--strength", choices=("easy", "typical", "hard"), default="typical")
    parser.add_argument("--output", type=Path, default=Path("data/synthetic_wp2"))
    parser.add_argument("--showcase", type=Path, default=Path("demo/wp2_synthetic.png"))
    args = parser.parse_args()

    dataset = make_dataset(args.count, args.seed, args.strength, half_and_half=True)
    save_dataset(dataset, args.output, args.seed)
    save_showcase(dataset[:8], args.showcase)
    print(f"saved {len(dataset)} plates to {args.output}")
    print(f"saved showcase to {args.showcase}")
