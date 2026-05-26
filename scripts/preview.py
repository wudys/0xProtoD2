from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

from config import ASSETS_PATH, FONT_FAMILY_OUTPUT_PATHS
from font_settings import (
    HANGUL_GLYPH_SCALE,
    HANGUL_SIDE_BEARING,
    HANGUL_WIDTH_RATIO,
)


PREVIEW_PATH = "preview"
SAMPLE_TEXTS = [
    "00000000000000000000",
    "가나다라마바사아자차카타파하",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "abcdefghijklmnopqrstuvwxyz",
    "0123456789  ()[]{}<> /\\ | @ # $ % & * + - _",
    "ABCdef123 한글테스트 0xProtoD2",
    'const 한글Name = "테스트123";',
]


def _metric_for(font_path: str, codepoint: int) -> tuple[int, int]:
    font = TTFont(font_path)
    cmap = font.getBestCmap()
    glyph_name = cmap[codepoint]
    return font["hmtx"].metrics[glyph_name]


def collect_metrics(font_path: str) -> dict[str, object]:
    zero_advance, zero_lsb = _metric_for(font_path, 0x30)
    hangul_advance, hangul_lsb = _metric_for(font_path, 0xAC00)
    return {
        "font": font_path,
        "zero": {"advance": zero_advance, "left_side_bearing": zero_lsb},
        "hangul": {"advance": hangul_advance, "left_side_bearing": hangul_lsb},
        "hangul_to_zero_ratio": round(hangul_advance / zero_advance, 4),
        "settings": {
            "hangul_width_ratio": HANGUL_WIDTH_RATIO,
            "hangul_glyph_scale": HANGUL_GLYPH_SCALE,
            "hangul_side_bearing": HANGUL_SIDE_BEARING,
        },
    }


def render_preview_png(
    output_path: str,
    font_paths: list[tuple[str, str]],
    primary_metrics: dict[str, object],
) -> None:
    font_size = 34
    label_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 16)
    info_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 18)
    fonts = [(label, ImageFont.truetype(path, font_size)) for label, path in font_paths]

    width = 1500
    header_height = 92
    row_height = 330
    image = Image.new("RGB", (width, header_height + row_height * len(fonts)), "white")
    draw = ImageDraw.Draw(image)

    settings = primary_metrics["settings"]
    zero = primary_metrics["zero"]
    hangul = primary_metrics["hangul"]
    draw.rectangle((0, 0, width, header_height), fill=(248, 248, 248))
    draw.text(
        (20, 18),
        "Preview settings",
        font=info_font,
        fill=(20, 20, 20),
    )
    draw.text(
        (20, 50),
        (
            f"HANGUL_WIDTH_RATIO={settings['hangul_width_ratio']}  "
            f"HANGUL_GLYPH_SCALE={settings['hangul_glyph_scale']}  "
            f"HANGUL_SIDE_BEARING={settings['hangul_side_bearing']}  "
            f"zero={zero['advance']}  hangul={hangul['advance']}  "
            f"ratio={primary_metrics['hangul_to_zero_ratio']}"
        ),
        font=label_font,
        fill=(80, 80, 80),
    )

    for index, (label, font) in enumerate(fonts):
        y0 = header_height + index * row_height
        draw.text((20, y0 + 12), label, font=label_font, fill=(20, 20, 20))
        zero_width = draw.textlength("0", font=font)
        column = 0
        while 20 + column * zero_width < width - 20:
            x = 20 + column * zero_width
            color = (235, 235, 235) if column % 2 else (220, 230, 245)
            draw.line((x, y0 + 42, x, y0 + row_height - 12), fill=color)
            column += 1

        y = y0 + 48
        for text in SAMPLE_TEXTS:
            draw.text((20, y), text, font=font, fill=(0, 0, 0))
            y += 38
        draw.text(
            (1180, y0 + 12),
            f"zero advance px ~= {zero_width:.1f}",
            font=label_font,
            fill=(80, 80, 80),
        )

    image.save(output_path)


def generate_preview() -> bool:
    os.makedirs(PREVIEW_PATH, exist_ok=True)
    primary_font = os.path.join(
        FONT_FAMILY_OUTPUT_PATHS["0xProtoD2"], "0xProtoD2-Regular.ttf"
    )
    if not os.path.exists(primary_font):
        print(f"[ERROR] 미리보기용 폰트를 찾을 수 없습니다: {primary_font}")
        return False

    d2_font = os.path.join(
        ASSETS_PATH, "ko_font", "D2Coding-Regular-Ver1.3.2-20180524.ttf"
    )
    comparison_fonts = [("D2Coding Regular", d2_font), ("0xProtoD2 Regular", primary_font)]
    png_path = os.path.join(PREVIEW_PATH, "balance-comparison.png")
    metrics_path = os.path.join(PREVIEW_PATH, "metrics.json")

    metrics = collect_metrics(primary_font)
    render_preview_png(png_path, comparison_fonts, metrics)
    with open(metrics_path, "w", encoding="utf-8") as file:
        json.dump(metrics, file, ensure_ascii=False, indent=2)
        file.write("\n")

    print(f"[INFO] 미리보기 PNG 생성: {png_path}")
    print(f"[INFO] 미리보기 metrics 생성: {metrics_path}")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if generate_preview() else 1)
