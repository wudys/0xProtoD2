#!/usr/bin/env python3
"""
빌드 산출 폰트 파일 검증 스크립트

이 스크립트는 scripts/build.py build 실행 후 생성된 TTF/WOFF2 파일을 열어
파일 간 메트릭과 설치 메타데이터가 일관적인지 검증합니다.
"""

import hashlib
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from config import BUILT_FONTS_PATH


class TestBuiltFonts(unittest.TestCase):
    """최종 산출 폰트 파일 검증 테스트."""

    HANGUL_RANGES = (
        (0x1100, 0x11FF),
        (0x3130, 0x318F),
        (0xA960, 0xA97F),
        (0xAC00, 0xD7AF),
        (0xD7B0, 0xD7FF),
    )

    def _require_fonttools(self):
        try:
            from fontTools.ttLib import TTFont
        except ImportError:
            self.skipTest("fontTools is required for built font validation")

        return TTFont

    def _unicode_cmap(self, font):
        cmap = {}
        for table in font["cmap"].tables:
            if table.isUnicode():
                cmap.update(table.cmap)

        return cmap

    def _built_font_paths(self, suffixes=(".ttf", ".woff2")):
        paths = []
        for family_name in ("0xProtoD2", "ZxProtoD2"):
            family_path = os.path.join(BUILT_FONTS_PATH, family_name)
            if not os.path.isdir(family_path):
                continue

            for filename in os.listdir(family_path):
                if filename.lower().endswith(suffixes):
                    paths.append(os.path.join(family_path, filename))

        return sorted(paths)

    def _hangul_metric_rows(self, font):
        cmap = self._unicode_cmap(font)
        metrics = font["hmtx"].metrics
        glyf = font["glyf"]
        rows = []

        for start, end in self.HANGUL_RANGES:
            for codepoint in range(start, end + 1):
                glyph_name = cmap.get(codepoint)
                if not glyph_name:
                    continue

                glyph = glyf[glyph_name]
                if glyph.isComposite():
                    glyph.recalcBounds(glyf)

                rows.append(
                    (
                        codepoint,
                        glyph_name,
                        metrics[glyph_name],
                        glyph.xMin,
                        glyph.yMin,
                        glyph.xMax,
                        glyph.yMax,
                    )
                )

        return rows

    def _hangul_metric_digest(self, font):
        rows = self._hangul_metric_rows(font)
        return hashlib.sha256(repr(rows).encode()).hexdigest()

    def _non_name_table_digest(self, font):
        digest = hashlib.sha256()
        for tag in sorted(font.keys()):
            if tag in {"GlyphOrder", "name", "head"}:
                continue

            digest.update(tag.encode("ascii"))
            digest.update(b"\0")
            digest.update(font.getTableData(tag))

        return digest.hexdigest()

    def test_built_fonts_have_expected_hangul_advance_widths(self):
        """모든 산출 폰트의 한글 advance width는 variant별 목표값과 일치합니다."""
        TTFont = self._require_fonttools()

        for font_path in self._built_font_paths():
            expected_width = (
                1240 if "NerdFontMono" in os.path.basename(font_path) else 1000
            )
            font = TTFont(font_path)
            bad_glyphs = [
                (hex(codepoint), glyph_name, advance_width)
                for codepoint, glyph_name, (advance_width, _), *_ in self._hangul_metric_rows(font)
                if advance_width != expected_width
            ]

            with self.subTest(font=os.path.basename(font_path)):
                self.assertEqual(
                    bad_glyphs,
                    [],
                    f"{font_path} contains Hangul glyphs outside width {expected_width}",
                )

    def test_built_ttf_unique_ids_are_not_shared_between_font_faces(self):
        """설치 대상 TTF face들은 Unique ID를 서로 공유하지 않습니다."""
        TTFont = self._require_fonttools()

        unique_ids = {}
        duplicates = []
        for font_path in self._built_font_paths(suffixes=(".ttf",)):
            font = TTFont(font_path)
            values = sorted(
                {
                    name.toUnicode()
                    for name in font["name"].names
                    if name.nameID == 3
                }
            )
            self.assertEqual(
                values,
                [os.path.splitext(os.path.basename(font_path))[0]],
            )

            for value in values:
                if value in unique_ids:
                    duplicates.append((value, unique_ids[value], font_path))
                unique_ids[value] = font_path

        self.assertEqual(duplicates, [])

    def test_built_0x_and_zx_aliases_have_identical_hangul_metrics(self):
        """0xProtoD2와 ZxProtoD2 alias 산출물은 family 이름 외 한글 메트릭이 같습니다."""
        TTFont = self._require_fonttools()
        zero_x_dir = os.path.join(BUILT_FONTS_PATH, "0xProtoD2")
        zx_dir = os.path.join(BUILT_FONTS_PATH, "ZxProtoD2")

        for zero_x_path in self._built_font_paths():
            if os.path.dirname(zero_x_path) != zero_x_dir:
                continue

            zx_filename = os.path.basename(zero_x_path).replace(
                "0xProtoD2",
                "ZxProtoD2",
                1,
            )
            zx_path = os.path.join(zx_dir, zx_filename)

            with self.subTest(font=os.path.basename(zero_x_path)):
                self.assertTrue(os.path.exists(zx_path), f"missing alias font: {zx_path}")
                self.assertEqual(
                    self._hangul_metric_digest(TTFont(zero_x_path)),
                    self._hangul_metric_digest(TTFont(zx_path)),
                )

    def test_built_0x_and_zx_aliases_only_differ_by_font_names(self):
        """0xProtoD2와 ZxProtoD2 alias 산출물은 이름 테이블 외 폰트 데이터가 같습니다."""
        TTFont = self._require_fonttools()
        zero_x_dir = os.path.join(BUILT_FONTS_PATH, "0xProtoD2")
        zx_dir = os.path.join(BUILT_FONTS_PATH, "ZxProtoD2")

        for zero_x_path in self._built_font_paths(suffixes=(".ttf",)):
            if os.path.dirname(zero_x_path) != zero_x_dir:
                continue

            zx_filename = os.path.basename(zero_x_path).replace(
                "0xProtoD2",
                "ZxProtoD2",
                1,
            )
            zx_path = os.path.join(zx_dir, zx_filename)

            with self.subTest(font=os.path.basename(zero_x_path)):
                self.assertTrue(os.path.exists(zx_path), f"missing alias font: {zx_path}")
                self.assertEqual(
                    self._non_name_table_digest(TTFont(zero_x_path)),
                    self._non_name_table_digest(TTFont(zx_path)),
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
