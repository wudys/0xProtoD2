import os

from config import ENGLISH_FONT_WIDTH


HANGUL_WIDTH_RATIO: float = float(os.environ.get("HANGUL_WIDTH_RATIO", "2.0"))
HANGUL_GLYPH_SCALE: float = float(os.environ.get("HANGUL_GLYPH_SCALE", "0.96"))
HANGUL_SIDE_BEARING: int = int(os.environ.get("HANGUL_SIDE_BEARING", "100"))


def get_hangul_advance_width() -> int:
    return round(ENGLISH_FONT_WIDTH * HANGUL_WIDTH_RATIO)


def get_hangul_outline_scale(source_width: int) -> float:
    if source_width <= 0:
        return HANGUL_GLYPH_SCALE

    drawable_width = max(get_hangul_advance_width() - HANGUL_SIDE_BEARING, 1)
    return (drawable_width / source_width) * HANGUL_GLYPH_SCALE
