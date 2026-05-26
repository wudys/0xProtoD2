import os

from config import ENGLISH_FONT_WIDTH


HANGUL_WIDTH_RATIO: float = float(os.environ.get("HANGUL_WIDTH_RATIO", "1.613"))
HANGUL_GLYPH_SCALE: float = float(os.environ.get("HANGUL_GLYPH_SCALE", "1.09"))
HANGUL_SIDE_BEARING: int = int(os.environ.get("HANGUL_SIDE_BEARING", "100"))
HANGUL_NERD_MONO_WIDTH_RATIO: float = float(
    os.environ.get("HANGUL_NERD_MONO_WIDTH_RATIO", "2.0")
)
HANGUL_NERD_MONO_GLYPH_SCALE: float = float(
    os.environ.get("HANGUL_NERD_MONO_GLYPH_SCALE", "0.94")
)
HANGUL_NERD_MONO_SIDE_BEARING: int = int(
    os.environ.get("HANGUL_NERD_MONO_SIDE_BEARING", "90")
)


def get_hangul_advance_width(is_nerd_font: bool = False) -> int:
    width_ratio = (
        HANGUL_NERD_MONO_WIDTH_RATIO if is_nerd_font else HANGUL_WIDTH_RATIO
    )
    return round(ENGLISH_FONT_WIDTH * width_ratio)


def get_hangul_outline_scale(source_width: int, is_nerd_font: bool = False) -> float:
    glyph_scale = (
        HANGUL_NERD_MONO_GLYPH_SCALE if is_nerd_font else HANGUL_GLYPH_SCALE
    )
    side_bearing = (
        HANGUL_NERD_MONO_SIDE_BEARING if is_nerd_font else HANGUL_SIDE_BEARING
    )
    if source_width <= 0:
        return glyph_scale

    drawable_width = max(get_hangul_advance_width(is_nerd_font) - side_bearing, 1)
    return (drawable_width / source_width) * glyph_scale
