from __future__ import annotations

import os
import sys
import tempfile
from typing import Any
import re

try:
    import fontforge
except ImportError:
    fontforge = None

from config import (
    BUILT_FONTS_PATH,
    EN_FONT_PATH,
    KO_FONT_PATH,
    EN_NERD_FONT_PATH,
    FONT_FAMILY_ALIASES,
    FONT_FAMILY_OUTPUT_PATHS,
    NO_LIGATURE_FONT_PATH,
    OLD_FONT_NAME,
)
from font_settings import (
    HANGUL_GLYPH_SCALE,
    HANGUL_SIDE_BEARING,
    HANGUL_WIDTH_RATIO,
    get_hangul_advance_width,
    get_hangul_outline_scale,
)

HANGUL_RANGES = [
    (0x1100, 0x11FF),
    (0x3130, 0x318F),
    (0xA960, 0xA97F),
    (0xAC00, 0xD7AF),
    (0xD7B0, 0xD7FF),
]


def _get_cleaned_name(name: str) -> str:
    """이름에서 공백을 제거합니다."""
    return name.replace(" ", "")


def update_family_name(original_family_name: str, old_str: str, new_str: str) -> str:
    """
    폰트 이름을 변경합니다.

    Args:
        original_family_name (str): 원래 폰트 이름.
        old_str (str): 변경하려는 이전 문자열. 공백과 대소문자는 무시됩니다.
        new_str (str): 변경할 새로운 문자열.

    Returns:
        str: 변경된 폰트 이름.
    """
    cleaned_original_name = _get_cleaned_name(original_family_name)
    cleaned_old_str = _get_cleaned_name(old_str)

    # old_str의 공백을 제거하고 대소문자를 무시하는 정규표현식으로 만듭니다.
    pattern = re.compile(re.escape(cleaned_old_str), re.IGNORECASE)

    # 정규표현식을 사용해 변경합니다.
    updated_name = pattern.sub(new_str, cleaned_original_name)
    return format_family_name(updated_name)


def format_family_name(family_name: str) -> str:
    """파일 친화적인 원본 family 이름을 UI에 표시할 family 이름으로 바꿉니다."""
    if "NLNerdFontMono" in family_name:
        return family_name.replace("NLNerdFontMono", " NL Nerd Font Mono")
    if family_name.endswith("NL"):
        return f"{family_name[:-2]} NL"
    return family_name


def format_postscript_family_name(family_name: str) -> str:
    """공백 없는 PostScript/file family 이름을 만듭니다."""
    return family_name.replace(" NL Nerd Font Mono", "-NL-NerdFontMono").replace(
        " NL", "-NL"
    )


def fit_hangul_glyph(glyph: Any) -> Any:
    """한글 글리프를 설정된 고정폭 셀 안에 맞춥니다."""
    source_width = int(glyph.width)
    target_width = get_hangul_advance_width()
    scale = get_hangul_outline_scale(source_width)
    x_offset = (target_width - (source_width * scale)) / 2

    glyph.transform((scale, 0, 0, scale, x_offset, 0))
    glyph.width = target_width
    return glyph


def _process_and_adjust_glyph(font: fontforge.font, glyph_id: int) -> None:
    """
    단일 글리프 또는 참조 글리프의 베어링을 조정합니다.
    """
    glyph = font[glyph_id]

    if not glyph.references:
        fit_hangul_glyph(glyph)
    else:
        fit_hangul_glyph(glyph)


def process_hangul_glyphs(font: fontforge.font) -> fontforge.font:
    """한글 글리프를 선택하고 베어링을 조정합니다."""
    for start, end in HANGUL_RANGES:
        for glyph_id in range(start, end + 1):
            if glyph_id in font:
                _process_and_adjust_glyph(font, glyph_id)

    print("[INFO] 한글 글리프 폭/외곽선 보정을 완료했습니다.")
    return font


def get_font_style(font: fontforge.font, original_filename: str = None) -> str:
    """
    폰트 객체나 파일명에서 폰트 스타일을 추출합니다.
    """
    if original_filename:
        style = _get_style_from_filename(original_filename)
        if style:
            return style

    return _get_style_from_font_metadata(font)


def _get_style_from_filename(original_filename: str) -> str | None:
    """파일명에서 스타일을 추출합니다."""
    base_name = os.path.splitext(original_filename)[0]
    base_name = base_name.replace("-NL", "")
    if "Bold" in base_name and "Italic" in base_name:
        return "BoldItalic"
    if "Bold" in base_name:
        return "Bold"
    if "Italic" in base_name:
        return "Italic"
    if "Regular" in base_name:
        return "Regular"
    style_parts = base_name.split("-")
    if len(style_parts) > 1:
        return style_parts[-1]
    return None


def _get_style_from_font_metadata(font: fontforge.font) -> str:
    """폰트 객체의 메타데이터에서 스타일을 추출합니다."""
    style_parts = []

    if hasattr(font, "weight") and font.weight:
        weight = font.weight.lower()
        if "bold" in weight:
            style_parts.append("Bold")
        elif "light" in weight:
            style_parts.append("Light")
        elif "medium" in weight:
            style_parts.append("Medium")

    if hasattr(font, "italicangle") and font.italicangle != 0:
        style_parts.append("Italic")

    try:
        if (
            hasattr(font, "os2_weight")
            and font.os2_weight >= 700
            and "Bold" not in style_parts
        ):
            style_parts.append("Bold")
    except Exception:
        pass

    if not style_parts:
        return "Regular"

    return "".join(style_parts)


def format_style_name(style: str) -> str:
    """스타일 이름을 포맷팅합니다(예: 'BoldItalic' -> 'Bold Italic')."""
    return re.sub(r"(?<!^)(?=[A-Z])", " ", style).strip()


def update_font_metadata(
    font: fontforge.font,
    style: str,
    old_name: str,
    new_name: str,
    base_family_name: str = None,
) -> None:
    """
    폰트의 메타데이터(패밀리 이름, 폰트 이름, 스타일 등)를 업데이트합니다.
    """
    new_family_name = update_family_name(base_family_name or font.familyname, old_name, new_name)

    formatted_style = format_style_name(style)
    postscript_family_name = format_postscript_family_name(new_family_name)

    font.familyname = new_family_name
    font.fontname = f"{postscript_family_name}-{style}"
    font.fullname = f"{new_family_name} {formatted_style}"

    font.appendSFNTName("English (US)", "Preferred Family", new_family_name)
    font.appendSFNTName("English (US)", "Family", new_family_name)
    font.appendSFNTName("English (US)", "Compatible Full", font.fullname)
    font.appendSFNTName("English (US)", "SubFamily", formatted_style)

    print(f"[INFO] 폰트 메타데이터를 '{new_family_name}'로 업데이트했습니다.")


def re_encode_for_nerd_font(font: fontforge.font) -> None:
    """Nerd Font의 특정 글리프 매핑 문제를 수정합니다(예: 하트, 오른쪽 삼각형 아이콘)."""
    mappings = {
        0xF08D0: 0x2665,  # heart
        0x25BA: 0x22B2,  # tringled right
    }

    for src_codepoint, dest_codepoint in mappings.items():
        try:
            if src_codepoint in font and dest_codepoint in font:
                font.selection.select(src_codepoint)
                font.copy()
                font.selection.select(dest_codepoint)
                font.paste()
                font.selection.select(src_codepoint)
                font.clear()
                print(
                    f"[INFO] 글리프 매핑을 수정했습니다: {hex(src_codepoint)} -> {hex(dest_codepoint)}"
                )
        except Exception as e:
            print(
                f"[WARNING] 글리프 매핑 수정 중 오류 발생 ({hex(src_codepoint)}): {e}"
            )


def get_font_extensions(is_nerd_font: bool) -> list[str]:
    if is_nerd_font:
        return ["ttf"]

    return ["ttf", "woff2"]


def generate_font_files(
    font: fontforge.font,
    style: str,
    output_dir: str,
    is_nerd_font: bool,
) -> None:
    """최종 TTF 및 WOFF2 폰트 파일을 생성하고 내보냅니다."""
    os.makedirs(output_dir, exist_ok=True)
    output_filename_base = font.fontname

    for ext in get_font_extensions(is_nerd_font):
        output_path = os.path.join(output_dir, f"{output_filename_base}.{ext}")

        try:
            font.generate(output_path)
            print(f"[INFO] {output_path} 내보내기 완료")
        except Exception as e:
            print(f"[ERROR] {font.fontname}에 대한 {ext.upper()} 생성 실패: {e}")


def get_output_dir(family_name: str) -> str:
    for family_alias, output_dir in FONT_FAMILY_OUTPUT_PATHS.items():
        if family_name.startswith(family_alias):
            return output_dir

    return BUILT_FONTS_PATH


def scale_font_em_units(font: fontforge.font, target_em: int) -> None:
    """
    폰트의 Em 단위를 조정하고 모든 글리프를 스케일링합니다.
    """
    if font.em == target_em:
        return

    scale_factor = target_em / font.em

    font.em = target_em
    font.selection.all()
    font.transform((scale_factor, 0, 0, scale_factor, 0, 0))

    print(
        f"[INFO] 폰트 Em 단위를 {int(target_em / scale_factor)}에서 {target_em}로 조정했습니다."
    )


def merge_korean_glyphs(
    target_font: fontforge.font, source_font: fontforge.font
) -> None:
    """
    한국어 글리프를 소스 폰트에서 타겟 폰트로 복사합니다.
    """
    try:
        copied_count = 0
        for start, end in HANGUL_RANGES:
            for codepoint in range(start, end + 1):
                if codepoint in source_font:
                    source_glyph = source_font[codepoint]
                    if source_glyph.isWorthOutputting():
                        source_font.selection.select(codepoint)
                        source_font.copy()
                        target_font.selection.select(codepoint)
                        target_font.paste()
                        copied_count += 1

        print(f"[INFO] {copied_count}개의 한글 글리프를 복사했습니다.")

    except Exception as e:
        print(f"[ERROR] 한글 글리프 병합 중 오류 발생: {e}")


def process_font_file(
    en_font: fontforge.font,
    ko_font: fontforge.font,
    is_nerd_font: bool,
    font_filename: str,
    output_dir: str,
) -> None:
    """
    단일 폰트 파일을 처리하여 한글 글리프를 병합하고 메타데이터를 업데이트합니다.
    """
    if is_nerd_font:
        re_encode_for_nerd_font(en_font)

    merge_korean_glyphs(en_font, ko_font)

    style = get_font_style(en_font, font_filename)
    base_family_name = en_font.familyname

    for family_alias in FONT_FAMILY_ALIASES:
        update_font_metadata(
            en_font,
            style,
            old_name=OLD_FONT_NAME,
            new_name=family_alias,
            base_family_name=base_family_name,
        )
        generate_font_files(
            en_font,
            style,
            get_output_dir(en_font.familyname),
            is_nerd_font,
        )


def find_font_files(directory: str, weight: str = None) -> list:
    """
    지정된 디렉터리에서 폰트 파일을 찾습니다.
    
    Args:
        directory: 폰트 파일을 찾을 디렉터리
        weight: 찾을 폰트 웨이트 ("Regular" 또는 "Bold")
        
    Returns:
        폰트 파일 경로의 리스트
    """
    if not os.path.exists(directory):
        return []
    
    font_files = []
    for filename in os.listdir(directory):
        if filename.lower().endswith((".ttf", ".otf", ".woff2")):
            if weight is None:
                font_files.append(os.path.join(directory, filename))
            elif weight.lower() in filename.lower():
                font_files.append(os.path.join(directory, filename))
    
    return sorted(font_files)


def _require_fontforge() -> None:
    if fontforge is None:
        raise RuntimeError(
            "FontForge Python module is required. Run this script with fontforge -script."
        )


def _process_font_variant(
    label: str,
    en_font_path: str,
    is_nerd_font: bool,
    weight: str,
    ko_font_path: str,
) -> None:
    en_files = find_font_files(en_font_path, weight)
    style = f"{label}-{weight.capitalize()}"

    if not en_files:
        print(f"[WARNING] {style}용 영문 폰트 파일을 찾을 수 없습니다. 건너뜁니다.")
        return

    en_font_file_path = en_files[0]

    try:
        print(f"[INFO] {style} 폰트 처리 중: {os.path.basename(ko_font_path)} + {os.path.basename(en_font_file_path)}")

        ko_font = fontforge.open(ko_font_path)
        en_font = fontforge.open(en_font_file_path)
        process_font_file(
            en_font,
            ko_font,
            is_nerd_font,
            os.path.basename(en_font_file_path),
            BUILT_FONTS_PATH,
        )

        en_font.close()
        ko_font.close()

    except Exception as e:
        print(f"[ERROR] {style} 폰트 처리 중 오류 발생: {e}")


def prepare_korean_font(weight: str, output_path: str) -> bool:
    ko_files = find_font_files(KO_FONT_PATH, weight)
    if not ko_files:
        print(f"[ERROR] {weight}용 한글 폰트 파일을 찾을 수 없습니다.")
        return False

    ko_font = fontforge.open(ko_files[0])
    process_hangul_glyphs(ko_font)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    ko_font.generate(output_path)
    ko_font.close()
    print(f"[INFO] 전처리 한글 폰트 생성: {output_path}")
    return True


def build_weight(weight: str, ko_font_path: str) -> None:
    variants = [
        ("Ligatures", EN_FONT_PATH, False),
        ("No-Ligatures", NO_LIGATURE_FONT_PATH, False),
        ("NerdFontMono", EN_NERD_FONT_PATH, True),
    ]

    for label, en_font_path, is_nerd_font in variants:
        _process_font_variant(label, en_font_path, is_nerd_font, weight, ko_font_path)


def build_fonts() -> None:
    """
    메인 폰트 빌드 프로세스입니다.
    새로운 디렉터리 구조에서 Regular와 Bold 폰트를 로드하고 병합합니다.
    """
    _require_fontforge()
    os.makedirs(BUILT_FONTS_PATH, exist_ok=True)

    with tempfile.TemporaryDirectory() as work_dir:
        for weight in ("regular", "bold"):
            ko_cache_path = os.path.join(work_dir, f"D2Coding-{weight}.ttf")
            if prepare_korean_font(weight, ko_cache_path):
                build_weight(weight, ko_cache_path)


def main() -> int:
    _require_fontforge()

    if len(sys.argv) == 4 and sys.argv[1] == "--prepare-ko":
        return 0 if prepare_korean_font(sys.argv[2], sys.argv[3]) else 1

    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        build_weight(sys.argv[2], sys.argv[3])
        return 0

    build_fonts()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
