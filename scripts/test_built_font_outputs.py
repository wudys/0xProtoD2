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

from config import BUILT_FONT_VERSION_PATH, BUILT_FONTS_PATH


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

            for dirpath, _, filenames in os.walk(family_path):
                for filename in filenames:
                    if filename.lower().endswith(suffixes):
                        paths.append(os.path.join(dirpath, filename))

        return sorted(paths)

    def _built_font_relpath(self, font_path):
        return os.path.relpath(font_path, BUILT_FONTS_PATH)

    def _alias_path(self, zero_x_path):
        relpath = self._built_font_relpath(zero_x_path)
        return os.path.join(
            BUILT_FONTS_PATH,
            relpath.replace("0xProtoD2", "ZxProtoD2"),
        )

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

    def _hangul_advance_digest(self, font):
        rows = [
            (codepoint, metrics[0])
            for codepoint, glyph_name, metrics, *_ in self._hangul_metric_rows(font)
        ]
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

    def _gsub_feature_tags(self, font):
        if "GSUB" not in font:
            return set()

        feature_list = font["GSUB"].table.FeatureList
        if not feature_list:
            return set()

        return {record.FeatureTag for record in feature_list.FeatureRecord}

    def _sfnt_name_values(self, font, name_id):
        return sorted(
            {
                name.toUnicode()
                for name in font["name"].names
                if name.nameID == name_id
            }
        )

    def _expected_ttf_relpaths(self):
        relpaths = set()
        for family_name in ("0xProtoD2", "ZxProtoD2"):
            for style in ("Bold", "Italic", "Regular"):
                relpaths.add(f"{family_name}/{family_name}-{style}.ttf")
                relpaths.add(f"{family_name}/NL/{family_name}-NL-{style}.ttf")
                relpaths.add(f"{family_name}/{family_name}-NerdFontMono-{style}.ttf")
                relpaths.add(
                    f"{family_name}/NL/{family_name}-NL-NerdFontMono-{style}.ttf"
                )

        return relpaths

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

    def test_built_ttf_files_include_ligature_and_nl_nerd_mono_variants(self):
        """Nerd Font Mono는 ligature/NL 조합을 모두 제공합니다."""
        actual_files = {
            self._built_font_relpath(path)
            for path in self._built_font_paths(suffixes=(".ttf",))
        }

        self.assertEqual(actual_files, self._expected_ttf_relpaths())

    def test_ligature_variants_keep_calt_feature(self):
        """한글 병합은 Ligatures variant의 contextual alternates를 제거하지 않습니다."""
        TTFont = self._require_fonttools()

        for font_path in self._built_font_paths(suffixes=(".ttf",)):
            relpath = self._built_font_relpath(font_path)
            with self.subTest(font=relpath):
                has_calt = "calt" in self._gsub_feature_tags(TTFont(font_path))
                self.assertEqual(has_calt, "/NL/" not in relpath)

    def test_built_ttf_unique_ids_are_not_shared_between_font_faces(self):
        """설치 대상 TTF face들은 Unique ID를 서로 공유하지 않습니다."""
        TTFont = self._require_fonttools()

        unique_ids = {}
        duplicates = []
        for font_path in self._built_font_paths(suffixes=(".ttf",)):
            font = TTFont(font_path)
            values = self._sfnt_name_values(font, 3)
            self.assertEqual(
                values,
                [os.path.splitext(os.path.basename(font_path))[0]],
            )

            for value in values:
                if value in unique_ids:
                    duplicates.append((value, unique_ids[value], font_path))
                unique_ids[value] = font_path

        self.assertEqual(duplicates, [])

    def test_built_fonts_use_release_version_metadata(self):
        """모든 산출 폰트의 version name은 repo FONT_VERSION과 일치합니다."""
        TTFont = self._require_fonttools()

        with open(BUILT_FONT_VERSION_PATH, encoding="utf-8") as version_file:
            expected_version = version_file.read().strip()

        self.assertTrue(expected_version, f"empty version file: {BUILT_FONT_VERSION_PATH}")

        for font_path in self._built_font_paths():
            font = TTFont(font_path)
            with self.subTest(font=os.path.basename(font_path)):
                self.assertEqual(
                    self._sfnt_name_values(font, 5),
                    [expected_version],
                )

    def test_built_0x_and_zx_aliases_have_identical_hangul_metrics(self):
        """0xProtoD2와 ZxProtoD2 alias 산출물은 family 이름 외 한글 메트릭이 같습니다."""
        TTFont = self._require_fonttools()

        for zero_x_path in self._built_font_paths():
            if not self._built_font_relpath(zero_x_path).startswith("0xProtoD2/"):
                continue

            zx_path = self._alias_path(zero_x_path)

            with self.subTest(font=os.path.basename(zero_x_path)):
                self.assertTrue(os.path.exists(zx_path), f"missing alias font: {zx_path}")
                self.assertEqual(
                    self._hangul_metric_digest(TTFont(zero_x_path)),
                    self._hangul_metric_digest(TTFont(zx_path)),
                )

    def test_built_0x_and_zx_aliases_only_differ_by_font_names(self):
        """0xProtoD2와 ZxProtoD2 alias 산출물은 이름 테이블 외 폰트 데이터가 같습니다."""
        TTFont = self._require_fonttools()

        for zero_x_path in self._built_font_paths(suffixes=(".ttf",)):
            if not self._built_font_relpath(zero_x_path).startswith("0xProtoD2/"):
                continue

            zx_path = self._alias_path(zero_x_path)

            with self.subTest(font=os.path.basename(zero_x_path)):
                self.assertTrue(os.path.exists(zx_path), f"missing alias font: {zx_path}")
                self.assertEqual(
                    self._non_name_table_digest(TTFont(zero_x_path)),
                    self._non_name_table_digest(TTFont(zx_path)),
                )

    def test_built_italic_hangul_keeps_width_but_slants_outlines(self):
        """Italic 산출물의 한글은 Regular와 폭은 같고 outline은 기울어져 다릅니다."""
        TTFont = self._require_fonttools()

        pairs = [
            ("0xProtoD2-Regular.ttf", "0xProtoD2-Italic.ttf"),
            ("0xProtoD2-NL-Regular.ttf", "0xProtoD2-NL-Italic.ttf"),
            (
                "0xProtoD2-NerdFontMono-Regular.ttf",
                "0xProtoD2-NerdFontMono-Italic.ttf",
            ),
            (
                "0xProtoD2-NL-NerdFontMono-Regular.ttf",
                "0xProtoD2-NL-NerdFontMono-Italic.ttf",
            ),
            ("ZxProtoD2-Regular.ttf", "ZxProtoD2-Italic.ttf"),
            ("ZxProtoD2-NL-Regular.ttf", "ZxProtoD2-NL-Italic.ttf"),
            (
                "ZxProtoD2-NerdFontMono-Regular.ttf",
                "ZxProtoD2-NerdFontMono-Italic.ttf",
            ),
            (
                "ZxProtoD2-NL-NerdFontMono-Regular.ttf",
                "ZxProtoD2-NL-NerdFontMono-Italic.ttf",
            ),
        ]

        for regular_name, italic_name in pairs:
            family_name = regular_name.split("-", 1)[0]
            family_dir = os.path.join(BUILT_FONTS_PATH, family_name)
            if "-NL-" in regular_name:
                family_dir = os.path.join(family_dir, "NL")
            regular_path = os.path.join(family_dir, regular_name)
            italic_path = os.path.join(family_dir, italic_name)

            with self.subTest(font=italic_name):
                regular_font = TTFont(regular_path)
                italic_font = TTFont(italic_path)
                self.assertEqual(
                    self._hangul_advance_digest(regular_font),
                    self._hangul_advance_digest(italic_font),
                )
                self.assertNotEqual(
                    self._hangul_metric_digest(regular_font),
                    self._hangul_metric_digest(italic_font),
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
