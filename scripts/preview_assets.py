from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

from config import ASSETS_PATH, FONT_FAMILY_OUTPUT_PATHS
from font_settings import get_hangul_settings


PREVIEW_PATH = "preview"
README_PREVIEW_IMAGE_PATH = os.path.join(ASSETS_PATH, "preview.png")
README_PREVIEW_FONT_SIZE = 28
README_HEADER_FONT_SIZE = 34
README_NOTE_FONT_SIZE = 24
README_FOOTER_FONT_SIZE = 24
README_TITLE_ICON_SIZE = 36
README_GITHUB_ICON_SIZE = 36
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
    width_ratio, glyph_scale, side_bearing = get_hangul_settings()
    return {
        "font": font_path,
        "zero": {"advance": zero_advance, "left_side_bearing": zero_lsb},
        "hangul": {"advance": hangul_advance, "left_side_bearing": hangul_lsb},
        "hangul_to_zero_ratio": round(hangul_advance / zero_advance, 4),
        "settings": {
            "hangul_width_ratio": width_ratio,
            "hangul_glyph_scale": glyph_scale,
            "hangul_side_bearing": side_bearing,
        },
    }


def render_preview_png(
    output_path: str,
    font_paths: list[tuple[str, str]],
    primary_metrics: dict[str, object],
) -> None:
    font_size = 34
    ui_font_path = str(primary_metrics["font"])
    label_font = ImageFont.truetype(ui_font_path, 16)
    info_font = ImageFont.truetype(ui_font_path, 18)
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


def render_readme_preview(output_path: str = README_PREVIEW_IMAGE_PATH) -> bool:
    font_path = os.path.join(
        FONT_FAMILY_OUTPUT_PATHS["0xProtoD2"], "0xProtoD2-Regular.ttf"
    )
    nerd_font_path = os.path.join(
        FONT_FAMILY_OUTPUT_PATHS["0xProtoD2"],
        "NL",
        "0xProtoD2-NL-NerdFontMono-Regular.ttf",
    )
    if not os.path.exists(font_path):
        print(f"[ERROR] 미리보기용 폰트를 찾을 수 없습니다: {font_path}")
        return False
    if not os.path.exists(nerd_font_path):
        print(f"[ERROR] 미리보기용 Nerd Font를 찾을 수 없습니다: {nerd_font_path}")
        return False

    font = ImageFont.truetype(font_path, README_PREVIEW_FONT_SIZE)
    header_font = ImageFont.truetype(font_path, README_HEADER_FONT_SIZE)
    note_font = ImageFont.truetype(font_path, README_NOTE_FONT_SIZE)
    footer_font = ImageFont.truetype(font_path, README_FOOTER_FONT_SIZE)
    title_icon_font = ImageFont.truetype(nerd_font_path, README_TITLE_ICON_SIZE)
    github_icon_font = ImageFont.truetype(nerd_font_path, README_GITHUB_ICON_SIZE)
    image = Image.new("RGB", (1280, 610), "#f7f2e8")
    draw = ImageDraw.Draw(image)

    ink = "#223044"
    muted = "#5f6875"
    bar = "#202a35"
    rule = "#d9c99f"

    draw.rectangle((0, 0, 1280, 88), fill=bar)
    draw.text((54, 28), "0xProtoD2", font=header_font, fill="white")
    draw.text((258, 24), "\uf121", font=title_icon_font, fill="white")
    draw.text((926, 24), "\uf09b", font=github_icon_font, fill="white")
    draw.text((966, 32), "wudys/0xProtoD2", font=footer_font, fill="white")

    lines = [
        (54, 136, 'const greeting = "안녕하세요, 0xProtoD2";', ink),
        (54, 188, "ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz", ink),
        (54, 240, "0123456789 ()[]{}<> /\\ | @ # $ % & * + - _", ink),
        (54, 316, "코드, 주석과 문서를 자연스럽게 살펴보세요.", ink),
        (54, 368, "Common ligature samples: -> <- => <= >= == === != !== && || ??", ink),
        (54, 410, "Code ligature samples: // /// :: ::= </> <$> |> <| >> <<", ink),
    ]
    for x, y, text, fill in lines:
        draw.text((x, y), text, font=font, fill=fill)
    draw.rectangle((54, 486, 1226, 491), fill=rule)
    draw.text(
        (54, 516),
        "included Regular / Bold / Italic / NL / Nerd Font Mono variants",
        font=note_font,
        fill=muted,
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    image.save(output_path)
    print(f"[INFO] README 미리보기 PNG 생성: {output_path}")
    return True


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
    return render_readme_preview()


if __name__ == "__main__":
    raise SystemExit(0 if generate_preview() else 1)
