"""Create a presentation-ready WP2 segmentation demo from a real plate."""

import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from scripts.make_synthetic_wp2 import find_font_path
from src.pipeline_wp1 import detect_plate
from src.pipeline_wp2 import segment_plate


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMAGE = (
    ROOT
    / "Vietnam License Plate.v2i.coco"
    / "test"
    / "Tgmt_0649_png.rf.7200ee4d65a8bd7e90f75bc85463f540.jpg"
)
DEFAULT_OUTPUT = ROOT / "demo" / "wp2_pipeline.png"


def font(size: int, bold: bool = False):
    try:
        path = find_font_path()
        return ImageFont.truetype(str(path), size)
    except (FileNotFoundError, OSError):
        return ImageFont.load_default(size)


def image_to_pil(image: np.ndarray) -> Image.Image:
    if image.ndim == 2:
        return Image.fromarray(image).convert("RGB")
    return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))


def card(
    canvas: Image.Image,
    position: tuple[int, int],
    index: int,
    title: str,
    note: str,
    image: np.ndarray,
):
    x, y = position
    width, height = 544, 464
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        (x, y, x + width, y + height), radius=24, fill="#ffffff", outline="#d9e3e8", width=2
    )
    draw.ellipse((x + 24, y + 22, x + 70, y + 68), fill="#087e83")
    draw.text((x + 47, y + 45), str(index), anchor="mm", font=font(23, True), fill="white")
    draw.text((x + 84, y + 22), title, font=font(27, True), fill="#19343e")
    draw.text((x + 26, y + 76), note, font=font(18), fill="#58717b")
    photo = image_to_pil(image)
    scale = min(500 / photo.width, 329 / photo.height)
    photo = photo.resize(
        (max(1, round(photo.width * scale)), max(1, round(photo.height * scale))),
        Image.Resampling.LANCZOS,
    )
    px = x + (width - photo.width) // 2
    py = y + 117 + (329 - photo.height) // 2
    canvas.paste(photo, (px, py))
    draw.rounded_rectangle(
        (x + 20, y + 111, x + width - 20, y + height - 18),
        radius=14,
        outline="#e6edf0",
        width=2,
    )


def character_grid(characters: list[np.ndarray], columns: int = 4) -> np.ndarray:
    size = characters[0].shape[0] if characters else 32
    scale = 3
    tile = size * scale
    gap = 12
    rows_count = max(1, (len(characters) + columns - 1) // columns)
    canvas = np.full(
        (rows_count * tile + (rows_count + 1) * gap, columns * tile + (columns + 1) * gap),
        245,
        dtype=np.uint8,
    )
    for index, character in enumerate(characters):
        row, column = divmod(index, columns)
        x = gap + column * (tile + gap)
        y = gap + row * (tile + gap)
        enlarged = cv2.resize(
            character, (tile, tile), interpolation=cv2.INTER_NEAREST
        )
        canvas[y : y + tile, x : x + tile] = enlarged
        cv2.putText(
            canvas,
            str(index + 1),
            (x + 4, y + 14),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            140,
            1,
            cv2.LINE_AA,
        )
    return canvas


def annotate_plate(plate: np.ndarray, result: dict) -> np.ndarray:
    annotated = plate.copy()
    if annotated.ndim == 2:
        annotated = cv2.cvtColor(annotated, cv2.COLOR_GRAY2BGR)
    for line in result["line_boxes"]:
        _, y, _, h = line
        cv2.line(annotated, (2, y), (annotated.shape[1] - 3, y), (0, 180, 0), 1)
        cv2.line(
            annotated,
            (2, y + h),
            (annotated.shape[1] - 3, y + h),
            (0, 180, 0),
            1,
        )
    for x, y, w, h in result["positions"]:
        cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 0, 255), 1)
    return annotated


def make_demo(input_path: Path, output_path: Path):
    detection = detect_plate(input_path)
    if detection is None:
        raise ValueError("No plate detected in this image")
    plate = detection["plate_normalized"]
    result = segment_plate(plate)
    annotated = annotate_plate(plate, result)
    binary = result["binary"]
    grid = character_grid(result["characters"])

    canvas = Image.new("RGB", (1776, 760), "#eff5f5")
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (52, 30), "WP2 | Tách dòng, tách ký tự và chuẩn hóa", font=font(40, True), fill="#15353b"
    )
    draw.text(
        (54, 86),
        "Đầu vào là ảnh biển đã chuẩn hóa bởi WP1 · Ảnh thật trong dataset",
        font=font(21),
        fill="#54707a",
    )
    panels = [
        (
            "Biển số đầu vào",
            "Đỏ: ký tự · Xanh: ranh giới dòng",
            annotated,
        ),
        (
            "Nhị phân sạch",
            f"Phương pháp: {result['binarization']}",
            binary,
        ),
        (
            "Ký tự 32×32",
            f"{result['num_chars']} ký tự · {result['line_type']}",
            grid,
        ),
    ]
    for index, (title, note, panel_image) in enumerate(panels, 1):
        card(canvas, (52 + (index - 1) * 570, 140), index, title, note, panel_image)
    draw.text(
        (54, 660),
        f"Thứ tự: trái → phải, trên → dưới  |  Kích thước chuẩn hóa: "
        f"{result['normalized_size']}×{result['normalized_size']}  |  "
        f"Số dòng: {len(result['line_boxes'])}",
        font=font(18),
        fill="#58717b",
    )
    draw.text(
        (54, 696),
        f"Tệp gốc: {input_path.name}  |  Box WP1: {detection['bbox']}",
        font=font(16),
        fill="#58717b",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(make_demo(args.image, args.output))
