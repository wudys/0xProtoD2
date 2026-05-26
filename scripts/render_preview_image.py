from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

from config import ASSETS_PATH, FONT_FAMILY_OUTPUT_PATHS


PREVIEW_IMAGE_PATH = os.path.join(ASSETS_PATH, "preview.png")
PREVIEW_FONT_SIZE = 28
HEADER_FONT_SIZE = 34
NOTE_FONT_SIZE = 24
FOOTER_FONT_SIZE = 24


def render_preview_image(output_path: str = PREVIEW_IMAGE_PATH) -> bool:
    font_path = os.path.join(
        FONT_FAMILY_OUTPUT_PATHS["0xProtoD2"], "0xProtoD2-Regular.ttf"
    )
    if not os.path.exists(font_path):
        print(f"[ERROR] 미리보기용 폰트를 찾을 수 없습니다: {font_path}")
        return False

    font = ImageFont.truetype(font_path, PREVIEW_FONT_SIZE)
    header_font = ImageFont.truetype(font_path, HEADER_FONT_SIZE)
    note_font = ImageFont.truetype(font_path, NOTE_FONT_SIZE)
    footer_font = ImageFont.truetype(font_path, FOOTER_FONT_SIZE)
    image = Image.new("RGB", (1280, 640), "#f7f2e8")
    draw = ImageDraw.Draw(image)

    ink = "#223044"
    muted = "#5f6875"
    bar = "#202a35"
    rule = "#d9c99f"

    draw.rectangle((0, 0, 1280, 88), fill=bar)
    draw.text((54, 31), "0xProtoD2", font=header_font, fill="white")

    lines = [
        (54, 136, 'const greeting = "안녕하세요, 0xProtoD2";', ink),
        (54, 188, "A-z  ABCDEFGHIJKLMNOPQRSTUVWXYZ  abcdefghijklmnopqrstuvwxyz", ink),
        (54, 240, "Numbers  0123456789  Symbols  ()[]{}<> /\\ | @ # $ % & * + - _", ink),
        (54, 316, "한글과 English, 숫자 0123456789, 기호 ()[]{}<>", ink),
        (54, 368, "코드와 문장을 한 폰트에서 함께 봅니다", ink),
    ]
    for x, y, text, fill in lines:
        draw.text((x, y), text, font=font, fill=fill)
    draw.text(
        (54, 456),
        "Non-deforming ligature policy · Nerd Font Mono variant included",
        font=note_font,
        fill=muted,
    )

    draw.rectangle((54, 502, 1226, 507), fill=rule)
    draw.text(
        (54, 547),
        "Built from 0xProto + D2Coding",
        font=footer_font,
        fill=muted,
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    image.save(output_path)
    print(f"[INFO] README 미리보기 PNG 생성: {output_path}")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if render_preview_image() else 1)
