"""Visualize HOG on one real character crop for the WP3 explanation."""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from src.pipeline_wp1 import detect_plate


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Vietnam License Plate.v2i.coco" / "train" / "greenpack_1648_png.rf.17ee479729a7760d82f5c6ece363cd43.jpg"
OUTPUT = ROOT / "demo" / "hog_character.png"
FONT = Path("C:/Windows/Fonts/arial.ttf")
BOLD = Path("C:/Windows/Fonts/arialbd.ttf")


def font(size, bold=False):
    return ImageFont.truetype(str(BOLD if bold else FONT), size)


def contain(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
    factor = min(max_width / image.width, max_height / image.height)
    return image.resize((round(image.width * factor), round(image.height * factor)), Image.Resampling.LANCZOS)


def card_base(canvas, x, title, note):
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((x, 155, x + 538, 758), radius=24, fill="white", outline="#d9e3e8", width=2)
    draw.text((x + 25, 178), title, font=font(30, True), fill="#19343e")
    draw.text((x + 25, 224), note, font=font(19), fill="#58717b")
    draw.rounded_rectangle((x + 25, 270, x + 513, 724), radius=14, fill="#f7fafb", outline="#e3ebee", width=2)


def make_hog_demo():
    result = detect_plate(SOURCE)
    if result is None:
        raise ValueError("Demo plate could not be detected")
    plate = result["plate_normalized"]
    # Manual character crop only for this explanatory figure; WP2 segmentation is separate.
    character = cv2.cvtColor(plate[8:70, 38:57], cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(character, (64, 128), interpolation=cv2.INTER_CUBIC)
    gx = cv2.Sobel(resized, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(resized, cv2.CV_32F, 0, 1, ksize=3)
    magnitude, angle = cv2.cartToPolar(gx, gy, angleInDegrees=True)
    angle %= 180

    canvas = Image.new("RGB", (1768, 1045), "#eff5f5")
    draw = ImageDraw.Draw(canvas)
    draw.text((52, 35), "HOG | Từ hình ký tự đến vector đặc trưng", font=font(40, True), fill="#15353b")
    draw.text((54, 93), "Ví dụ ký tự 9 trên biển xe máy · HOG mô tả hướng thay đổi độ sáng quanh nét chữ", font=font(21), fill="#54707a")

    positions = (52, 615, 1178)
    for x, title, note in zip(positions, ("1. Ký tự gốc", "2. Độ mạnh của biên", "3. Hướng biên theo ô"),
                              ("Cắt tay ký tự 9 để minh họa", "Sobel đo độ đổi sáng từng pixel", "Mỗi ô 8×8 pixel có 9 hướng")):
        card_base(canvas, x, title, note)

    # Panel 1: original sample, normalized to the HOG input size, with an 8x8 grid.
    char_pil = contain(Image.fromarray(resized).convert("RGB"), 220, 440)
    canvas.paste(char_pil, (52 + (538 - char_pil.width) // 2, 277 + (440 - char_pil.height) // 2))
    p1x = 52 + (538 - char_pil.width) // 2
    p1y = 277 + (440 - char_pil.height) // 2
    for col in range(1, 8):
        xx = p1x + round(col * char_pil.width / 8)
        draw.line((xx, p1y, xx, p1y + char_pil.height), fill="#16aca7", width=1)
    for row in range(1, 16):
        yy = p1y + round(row * char_pil.height / 16)
        draw.line((p1x, yy, p1x + char_pil.width, yy), fill="#16aca7", width=1)

    # Panel 2: true Sobel gradient magnitude, scaled only for display.
    display_mag = np.uint8(np.clip(magnitude / max(1, np.percentile(magnitude, 99)) * 255, 0, 255))
    heat = cv2.applyColorMap(display_mag, cv2.COLORMAP_INFERNO)
    heat_pil = contain(Image.fromarray(cv2.cvtColor(heat, cv2.COLOR_BGR2RGB)), 220, 440)
    canvas.paste(heat_pil, (615 + (538 - heat_pil.width) // 2, 277 + (440 - heat_pil.height) // 2))

    # Panel 3: a glyph for each cell histogram. Bright strokes indicate strong directions.
    board = Image.new("RGB", (256, 512), "#102b35")
    glyph = ImageDraw.Draw(board)
    histograms = np.zeros((16, 8, 9), dtype=np.float32)
    for row in range(16):
        for col in range(8):
            cell_m = magnitude[row * 8:(row + 1) * 8, col * 8:(col + 1) * 8]
            cell_a = angle[row * 8:(row + 1) * 8, col * 8:(col + 1) * 8]
            histograms[row, col], _ = np.histogram(cell_a, bins=9, range=(0, 180), weights=cell_m)
    blocks = []
    for row in range(15):
        for col in range(7):
            block = histograms[row:row + 2, col:col + 2].ravel()
            blocks.append(block / np.sqrt(np.dot(block, block) + 1e-6))
    vector = np.concatenate(blocks)
    high = max(1, np.percentile(histograms, 98))
    for row in range(16):
        for col in range(8):
            cx, cy = 16 + 32 * col, 16 + 32 * row
            glyph.rectangle((col * 32, row * 32, col * 32 + 31, row * 32 + 31), outline="#28505b")
            for bin_index, value in enumerate(histograms[row, col]):
                strength = min(1.0, float(value / high))
                if strength < 0.09:
                    continue
                theta = np.deg2rad(10 + bin_index * 20)
                length = 13 * strength
                dx, dy = length * np.cos(theta), length * np.sin(theta)
                shade = int(70 + 185 * strength)
                glyph.line((cx - dx, cy - dy, cx + dx, cy + dy), fill=(shade, min(255, shade + 28), 76), width=2)
    board = board.resize((288, 432), Image.Resampling.LANCZOS)
    canvas.paste(board, (1178 + (538 - 288) // 2, 281))

    # Explain the numeric vector with an actual subset of this HOG descriptor.
    draw.rounded_rectangle((52, 787, 1716, 1000), radius=22, fill="#15343e")
    draw.text((77, 808), "4. Ghép thành vector cho bộ phân loại SVM", font=font(29, True), fill="white")
    draw.text((79, 853), f"7 × 15 block × 4 ô × 9 hướng = {len(vector):,} giá trị", font=font(23), fill="#bde8df")
    shown = vector[:160]
    bar_left, bar_top, bar_width, bar_height = 79, 900, 1590, 64
    max_value = max(float(shown.max()), 1e-6)
    for index, value in enumerate(shown):
        bar_x = bar_left + index * (bar_width / len(shown))
        bar_h = max(1, float(value) / max_value * bar_height)
        draw.rectangle((bar_x, bar_top + bar_height - bar_h, bar_x + 6, bar_top + bar_height), fill="#77d5ba")
    draw.text((1350, 973), "160 giá trị đầu", font=font(17), fill="#bde8df")
    draw.text((54, 1017), "Nguồn ảnh: Vietnam License Plate, Roboflow Universe (CC BY 4.0) · Crop ký tự chỉ phục vụ minh họa", font=font(17), fill="#58717b")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    print(make_hog_demo())
