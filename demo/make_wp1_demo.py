"""Create a presentation-ready WP1 before/after image from a real dataset sample."""

import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from src.pipeline_wp1 import detect_plate
from src.preprocessing import grayscale


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMAGE = ROOT / "Vietnam License Plate.v2i.coco" / "train" / "greenpack_1648_png.rf.17ee479729a7760d82f5c6ece363cd43.jpg"
DEFAULT_OUTPUT = ROOT / "demo" / "wp1_before_after.png"
FONT_PATH = Path("C:/Windows/Fonts/arial.ttf")
BOLD_FONT_PATH = Path("C:/Windows/Fonts/arialbd.ttf")


def font(size: int, bold: bool = False):
    path = BOLD_FONT_PATH if bold else FONT_PATH
    return ImageFont.truetype(str(path), size)


def image_to_pil(image: np.ndarray) -> Image.Image:
    if image.ndim == 2:
        return Image.fromarray(image).convert("RGB")
    return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))


def card(canvas: Image.Image, position: tuple[int, int], index: int, title: str, note: str, image: np.ndarray):
    x, y = position
    width, height = 544, 464
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((x, y, x + width, y + height), radius=24, fill="#ffffff", outline="#d9e3e8", width=2)
    draw.ellipse((x + 24, y + 22, x + 70, y + 68), fill="#087e83")
    draw.text((x + 47, y + 45), str(index), anchor="mm", font=font(23, True), fill="white")
    draw.text((x + 84, y + 22), title, font=font(28, True), fill="#19343e")
    draw.text((x + 26, y + 76), note, font=font(18), fill="#58717b")
    photo = image_to_pil(image)
    scale = min(500 / photo.width, 329 / photo.height)
    photo = photo.resize((max(1, round(photo.width * scale)), max(1, round(photo.height * scale))), Image.Resampling.LANCZOS)
    px = x + (width - photo.width) // 2
    py = y + 117 + (329 - photo.height) // 2
    canvas.paste(photo, (px, py))
    draw.rounded_rectangle((x + 20, y + 111, x + width - 20, y + height - 18), radius=14, outline="#e6edf0", width=2)


def make_demo(input_path: Path, output_path: Path):
    result = detect_plate(input_path)
    if result is None:
        raise ValueError("No plate detected in this image")
    source = cv2.imdecode(np.fromfile(input_path, dtype=np.uint8), cv2.IMREAD_COLOR)
    annotated = source.copy()
    x1, y1, x2, y2 = result["bbox"]
    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 205, 255), 5)
    crop = result["plate_crop"]
    corrected = result["plate_normalized"]
    gray = grayscale(corrected)
    contrast = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    denoised = cv2.bilateralFilter(contrast, 5, 35, 35)

    canvas = Image.new("RGB", (1776, 1190), "#eff5f5")
    draw = ImageDraw.Draw(canvas)
    draw.text((52, 30), "WP1 | Từ ảnh xe máy đến biển số sạch", font=font(40, True), fill="#15353b")
    draw.text((54, 86), "Ảnh thật trong dataset · Phát hiện bằng OpenCV, không dùng box nhãn khi dự đoán", font=font(21), fill="#54707a")
    panels = [
        ("Ảnh gốc", "Khung vàng là vị trí thuật toán tìm được", annotated),
        ("Cắt vùng biển", "Lấy pixel bên trong bounding box", crop),
        ("Chỉnh phối cảnh", "Làm phẳng vùng biển bị nghiêng", corrected),
        ("Chuyển ảnh xám", "Giữ độ sáng, bỏ thông tin màu", gray),
        ("Tăng tương phản", "CLAHE làm nét chữ rõ hơn", contrast),
        ("Lọc nhiễu", "Bilateral làm mượt và giữ biên chữ", denoised),
    ]
    for index, (title, note, panel_image) in enumerate(panels, 1):
        card(canvas, (52 + ((index - 1) % 3) * 570, 140 + ((index - 1) // 3) * 485), index, title, note, panel_image)
    draw.text((54, 1108), f"Nguồn ảnh: Vietnam License Plate, Roboflow Universe (CC BY 4.0)  |  Box dự đoán: [{x1}, {y1}, {x2}, {y2}]", font=font(17), fill="#58717b")
    draw.text((54, 1139), f"Tệp gốc: {input_path.name}", font=font(16), fill="#58717b")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(make_demo(args.image, args.output))
