import os

from config import ENGLISH_FONT_WIDTH


def _float_env(name: str, default: str) -> float:
    return float(os.environ.get(name, default))


def _int_env(name: str, default: str) -> int:
    return int(os.environ.get(name, default))


HANGUL_SETTINGS = (
    _float_env("HANGUL_WIDTH_RATIO", "1.613"),
    _float_env("HANGUL_GLYPH_SCALE", "1.09"),
    _int_env("HANGUL_SIDE_BEARING", "100"),
)
HANGUL_NERD_MONO_SETTINGS = (
    _float_env("HANGUL_NERD_MONO_WIDTH_RATIO", "2.0"),
    _float_env("HANGUL_NERD_MONO_GLYPH_SCALE", "0.945"),
    _int_env("HANGUL_NERD_MONO_SIDE_BEARING", "120"),
)


def get_hangul_settings(is_nerd_font: bool = False) -> tuple[float, float, int]:
    if is_nerd_font:
        return HANGUL_NERD_MONO_SETTINGS
    return HANGUL_SETTINGS


def get_hangul_advance_width(is_nerd_font: bool = False) -> int:
    width_ratio, _, _ = get_hangul_settings(is_nerd_font)
    return round(ENGLISH_FONT_WIDTH * width_ratio)


def get_hangul_outline_scale(source_width: int, is_nerd_font: bool = False) -> float:
    _, glyph_scale, side_bearing = get_hangul_settings(is_nerd_font)
    if source_width <= 0:
        return glyph_scale

    drawable_width = max(get_hangul_advance_width(is_nerd_font) - side_bearing, 1)
    return (drawable_width / source_width) * glyph_scale
