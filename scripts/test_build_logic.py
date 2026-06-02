#!/usr/bin/env python3
"""
폰트 빌드 프로세스 테스트 스크립트

이 스크립트는 폰트 빌드 과정의 각 단계를 테스트하고 검증합니다.
"""

import os
import sys
import unittest
from unittest import mock

# 현재 스크립트 디렉터리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(__file__))

from config import (
    EN_FONT_PATH,
    EN_NERD_FONT_PATH,
    BUILT_FONTS_PATH,
)
import config


class TestFontBuildProcess(unittest.TestCase):
    """폰트 빌드 프로세스 테스트 클래스"""

    def test_hangul_bearing_adjustment_applies_to_hangul_glyph_width(self):
        """한글 글리프는 사용자 설정에서 계산한 고정폭 셀에 맞춥니다."""
        from hangulify import _process_and_adjust_glyph

        class FakeGlyph:
            references = ()

            def __init__(self):
                self.width = 1000
                self.left_side_bearing = 152
                self.right_side_bearing = 207
                self.transforms = []

            def transform(self, transform):
                self.transforms.append(transform)

        glyph = FakeGlyph()
        _process_and_adjust_glyph({0xAC00: glyph}, 0xAC00)

        self.assertEqual(glyph.width, 1000)
        self.assertEqual(len(glyph.transforms), 1)
        self.assertAlmostEqual(glyph.transforms[0][0], 0.981, places=4)

    def test_hangul_reference_glyphs_are_unlinked_before_adjustment(self):
        """참조 글리프는 생성 시 advance width가 되돌아가지 않도록 참조를 풉니다."""
        from hangulify import _process_and_adjust_glyph

        class FakeGlyph:
            references = (("cho", (1, 0, 0, 1, 0, 0)),)

            def __init__(self):
                self.width = 1000
                self.transforms = []
                self.unlinked = False

            def unlinkRef(self):
                self.unlinked = True
                self.references = ()

            def transform(self, transform):
                self.transforms.append(transform)

        glyph = FakeGlyph()
        _process_and_adjust_glyph({0xD7A3: glyph}, 0xD7A3, is_nerd_font=True)

        self.assertTrue(glyph.unlinked)
        self.assertEqual(glyph.width, 1240)
        self.assertEqual(len(glyph.transforms), 1)

    def test_italic_hangul_glyphs_are_slanted_after_merge(self):
        """Italic output의 한글은 fallback synthetic italic처럼 기울입니다."""
        from hangulify import slant_hangul_glyphs

        class FakeGlyph:
            references = ()

            def __init__(self):
                self.width = 1000
                self.transforms = []

            def transform(self, transform):
                self.transforms.append(transform)

        glyph = FakeGlyph()
        font = {0xAC00: glyph}

        slant_hangul_glyphs(font, -9)

        self.assertEqual(glyph.width, 1000)
        self.assertEqual(len(glyph.transforms), 1)
        self.assertEqual(glyph.transforms[0][0], 1)
        self.assertGreater(glyph.transforms[0][2], 0)

    def test_user_facing_hangul_settings_compute_fixed_2_cell_width(self):
        """기본 사용자 설정은 평상시 한글 advance와 여백을 계산합니다."""
        import font_settings

        self.assertEqual(font_settings.get_hangul_advance_width(), 1000)
        self.assertAlmostEqual(
            font_settings.get_hangul_outline_scale(1000),
            0.981,
            places=4,
        )

    def test_nerd_mono_hangul_settings_use_separate_balance(self):
        """Nerd Font Mono는 일반 한글 설정과 별도 advance/scale을 사용합니다."""
        import font_settings

        self.assertEqual(font_settings.get_hangul_advance_width(True), 1240)
        self.assertAlmostEqual(
            font_settings.get_hangul_outline_scale(1000, True),
            1.081,
            places=4,
        )

    def test_nerd_mono_variant_uses_separate_prepared_korean_font(self):
        """Nerd Font Mono variant만 별도 전처리 한글 폰트를 사용합니다."""
        import hangulify

        calls = []

        def record_variant(
            label,
            en_font_path,
            is_nerd_font,
            weight,
            ko_font_path,
            name_part=None,
            family_aliases=None,
        ):
            calls.append((is_nerd_font, ko_font_path))
            return True

        with mock.patch.object(hangulify, "_process_font_variant", record_variant):
            hangulify.build_weight_with_variants(
                "regular",
                "/tmp/D2Coding-regular.ttf",
                "/tmp/D2Coding-regular-nerd-mono.ttf",
            )

        self.assertEqual(
            calls,
            [
                (False, "/tmp/D2Coding-regular.ttf"),
                (False, "/tmp/D2Coding-regular.ttf"),
                (True, "/tmp/D2Coding-regular-nerd-mono.ttf"),
                (True, "/tmp/D2Coding-regular-nerd-mono.ttf"),
            ],
        )

    def test_run_prepare_korean_font_adds_nerd_mono_flag_only_for_variant(self):
        """Nerd Mono 한글 전처리 명령에만 --nerd-mono를 붙입니다."""
        import build

        calls = []

        def record_run(command, check):
            calls.append((command, check))
            return mock.Mock(returncode=0)

        with mock.patch.object(build.subprocess, "run", record_run):
            self.assertTrue(
                build.run_prepare_korean_font(
                    "fontforge",
                    "hangulify.py",
                    "regular",
                    "/tmp/D2Coding-regular.ttf",
                )
            )
            self.assertTrue(
                build.run_prepare_korean_font(
                    "fontforge",
                    "hangulify.py",
                    "regular",
                    "/tmp/D2Coding-regular-nerd-mono.ttf",
                    is_nerd_font=True,
                )
            )

        self.assertEqual(
            calls,
            [
                (
                    [
                        "fontforge",
                        "-script",
                        "hangulify.py",
                        "--prepare-ko",
                        "regular",
                        "/tmp/D2Coding-regular.ttf",
                    ],
                    False,
                ),
                (
                    [
                        "fontforge",
                        "-script",
                        "hangulify.py",
                        "--prepare-ko",
                        "regular",
                        "/tmp/D2Coding-regular-nerd-mono.ttf",
                        "--nerd-mono",
                    ],
                    False,
                ),
            ],
        )

    def test_run_python_test_script_uses_current_python_executable(self):
        """build.py 테스트 서브커맨드는 현재 Python으로 테스트 파일을 실행합니다."""
        import build

        calls = []

        def record_run(command, check):
            calls.append((command, check))
            return mock.Mock(returncode=0)

        with mock.patch.object(build.subprocess, "run", record_run):
            self.assertTrue(build.run_python_test_script("test_build_logic.py"))

        self.assertEqual(
            calls,
            [
                (
                    [
                        sys.executable,
                        os.path.join(os.path.dirname(build.__file__), "test_build_logic.py"),
                    ],
                    False,
                )
            ],
        )

    def test_release_archive_name_includes_family_and_version(self):
        """릴리즈 archive 이름은 family와 release version을 함께 담습니다."""
        self.assertEqual(
            config.get_release_archive_name("ZxProtoD2", "1.2.3"),
            "ZxProtoD2-fonts-1.2.3.zip",
        )

    def test_build_family_option_accepts_single_known_family(self):
        """build --family는 알려진 family alias 하나만 선택합니다."""
        import build

        self.assertEqual(
            build.parse_family_option(["--family", "ZxProtoD2"]),
            ("ZxProtoD2",),
        )

        with self.assertRaises(ValueError):
            build.parse_family_option(["--family", "UnknownD2"])

    def test_run_build_fonts_processes_italic_family(self):
        """빌드 오케스트레이터는 Italic 계열도 준비하고 worker에 전달합니다."""
        import build

        prepared_weights = []
        worker_weights = []
        worker_commands = []

        class FakeProcess:
            def __init__(self, command):
                worker_commands.append(command)
                worker_weights.append(command[4])

            def wait(self):
                return 0

        def record_prepare(fontforge_bin, script_path, weight, output_path, is_nerd_font=False):
            prepared_weights.append((weight, os.path.basename(output_path), is_nerd_font))
            return True

        with mock.patch.object(build.shutil, "which", return_value="fontforge"), \
            mock.patch.object(build, "run_prepare_korean_font", record_prepare), \
            mock.patch.object(build.tempfile, "TemporaryDirectory") as temp_dir, \
            mock.patch.object(build.subprocess, "Popen", FakeProcess):
            temp_dir.return_value.__enter__.return_value = "/tmp"

            self.assertTrue(build.run_build_fonts())

        self.assertEqual(
            prepared_weights,
            [
                ("regular", "D2Coding-regular.ttf", False),
                ("regular", "D2Coding-regular-nerd-mono.ttf", True),
                ("bold", "D2Coding-bold.ttf", False),
                ("bold", "D2Coding-bold-nerd-mono.ttf", True),
            ],
        )
        self.assertEqual(worker_weights, ["regular", "bold", "italic"])
        self.assertTrue(all("--family" not in command for command in worker_commands))

    def test_run_build_fonts_passes_selected_family_to_workers(self):
        """선택 family 빌드는 각 worker에 --family를 전달합니다."""
        import build

        worker_commands = []

        class FakeProcess:
            def __init__(self, command):
                worker_commands.append(command)

            def wait(self):
                return 0

        with mock.patch.object(build.shutil, "which", return_value="fontforge"), \
            mock.patch.object(build, "run_prepare_korean_font", return_value=True), \
            mock.patch.object(build.tempfile, "TemporaryDirectory") as temp_dir, \
            mock.patch.object(build.subprocess, "Popen", FakeProcess):
            temp_dir.return_value.__enter__.return_value = "/tmp"

            self.assertTrue(build.run_build_fonts(("ZxProtoD2",)))

        self.assertEqual(len(worker_commands), 3)
        self.assertTrue(
            all(
                command[-2:] == ["--family", "ZxProtoD2"]
                for command in worker_commands
            )
        )

    def test_hangulify_build_fonts_processes_italic_family(self):
        """FontForge worker 경로도 Italic 계열을 병합합니다."""
        import hangulify

        prepared_weights = []
        merged_weights = []

        def record_prepare(weight, output_path, is_nerd_font=False):
            prepared_weights.append((weight, os.path.basename(output_path), is_nerd_font))
            return True

        def record_build(
            weight,
            ko_font_path,
            nerd_mono_ko_font_path,
            family_aliases=None,
        ):
            merged_weights.append(weight)
            return True

        with mock.patch.object(hangulify, "fontforge", object()), \
            mock.patch.object(hangulify, "prepare_korean_font", record_prepare), \
            mock.patch.object(hangulify, "build_weight_with_variants", record_build), \
            mock.patch.object(hangulify.os, "makedirs"), \
            mock.patch.object(hangulify.tempfile, "TemporaryDirectory") as temp_dir:
            temp_dir.return_value.__enter__.return_value = "/tmp"

            self.assertTrue(hangulify.build_fonts())

        self.assertEqual(
            prepared_weights,
            [
                ("regular", "D2Coding-regular.ttf", False),
                ("regular", "D2Coding-regular-nerd-mono.ttf", True),
                ("bold", "D2Coding-bold.ttf", False),
                ("bold", "D2Coding-bold-nerd-mono.ttf", True),
            ],
        )
        self.assertEqual(merged_weights, ["regular", "bold", "italic"])

    def test_find_font_files_ignores_woff2_sources(self):
        """원본 검색은 TTF/OTF만 사용하고 WOFF2 웹폰트는 입력에서 제외합니다."""
        import tempfile
        from hangulify import find_font_files

        with tempfile.TemporaryDirectory() as font_dir:
            ttf_path = os.path.join(font_dir, "Example-Regular.ttf")
            woff2_path = os.path.join(font_dir, "Example-Regular.woff2")
            open(ttf_path, "w").close()
            open(woff2_path, "w").close()

            self.assertEqual(find_font_files(font_dir), [ttf_path])

    def test_find_font_files_filters_nerd_mono_ligature_sources_explicitly(self):
        """Nerd Font Mono source 검색은 L/NL 파일을 서로 섞지 않습니다."""
        import tempfile
        from hangulify import find_font_files

        filenames = [
            "0xProtoNerdFontMono-Regular.ttf",
            "0xProtoNerdFontMono-Bold.ttf",
            "0xProtoNLNerdFontMono-Regular.ttf",
            "0xProtoNLNerdFontMono-Bold.ttf",
        ]
        with tempfile.TemporaryDirectory() as font_dir:
            for filename in filenames:
                open(os.path.join(font_dir, filename), "w").close()

            self.assertEqual(
                [os.path.basename(path) for path in find_font_files(
                    font_dir,
                    "regular",
                    "0xProtoNerdFontMono",
                )],
                ["0xProtoNerdFontMono-Regular.ttf"],
            )
            self.assertEqual(
                [os.path.basename(path) for path in find_font_files(
                    font_dir,
                    "regular",
                    "0xProtoNLNerdFontMono",
                )],
                ["0xProtoNLNerdFontMono-Regular.ttf"],
            )

    def test_build_weight_with_variants_maps_each_variant_to_expected_source_filter(self):
        """각 variant는 의도한 영문 source 디렉터리와 Nerd source 필터를 사용합니다."""
        import hangulify

        calls = []

        def record_variant(
            label,
            en_font_path,
            is_nerd_font,
            weight,
            ko_font_path,
            name_part=None,
            family_aliases=None,
        ):
            calls.append((en_font_path, is_nerd_font, name_part))
            return True

        with mock.patch.object(hangulify, "_process_font_variant", record_variant):
            self.assertTrue(
                hangulify.build_weight_with_variants(
                    "regular",
                    "/tmp/D2Coding-regular.ttf",
                    "/tmp/D2Coding-regular-nerd-mono.ttf",
                )
            )

        self.assertEqual(
            calls,
            [
                (EN_FONT_PATH, False, None),
                (config.NO_LIGATURE_FONT_PATH, False, None),
                (
                    EN_NERD_FONT_PATH,
                    True,
                    "0xProtoNerdFontMono",
                ),
                (
                    EN_NERD_FONT_PATH,
                    True,
                    "0xProtoNLNerdFontMono",
                ),
            ],
        )

    def test_get_font_style_keeps_filename_precedence(self):
        """파일명 기반 스타일 판별 우선순위를 유지합니다."""
        from hangulify import get_font_style

        class FakeFont:
            weight = "Bold"
            italicangle = -12
            os2_weight = 700

        self.assertEqual(get_font_style(FakeFont(), "0xProto-Regular.ttf"), "Regular")
        self.assertEqual(get_font_style(FakeFont(), "0xProto-Bold.ttf"), "Bold")
        self.assertEqual(get_font_style(FakeFont(), "0xProto-Italic.ttf"), "Italic")
        self.assertEqual(get_font_style(FakeFont(), "0xProtoNL-Bold.ttf"), "Bold")

    def test_get_font_style_keeps_metadata_fallbacks(self):
        """파일명이 없으면 기존 메타데이터 순서로 스타일을 판별합니다."""
        from hangulify import get_font_style

        class FakeFont:
            def __init__(self, weight=None, italicangle=0, os2_weight=400):
                self.weight = weight
                self.italicangle = italicangle
                self.os2_weight = os2_weight

        self.assertEqual(get_font_style(FakeFont(weight="Bold")), "Bold")
        self.assertEqual(get_font_style(FakeFont(italicangle=-12)), "Italic")
        self.assertEqual(get_font_style(FakeFont(os2_weight=700)), "Bold")
        self.assertEqual(get_font_style(FakeFont()), "Regular")

    def test_no_ligature_source_suffix_is_kept_in_family_name(self):
        """No Ligatures 원본의 NL 표기는 family/file name에 유지합니다."""
        from hangulify import format_postscript_family_name, update_family_name

        self.assertEqual(
            update_family_name("0xProtoNL", "0xProto", "0xProtoD2"),
            "0xProtoD2 NL",
        )
        self.assertEqual(
            update_family_name("0xProtoNL Nerd Font Mono", "0xProto", "ZxProtoD2"),
            "ZxProtoD2 NL Mono Nerd Font",
        )
        self.assertEqual(
            update_family_name("0xProto Nerd Font Mono", "0xProto", "ZxProtoD2"),
            "ZxProtoD2 Mono Nerd Font",
        )
        self.assertEqual(
            format_postscript_family_name("0xProtoD2 NL Mono Nerd Font"),
            "0xProtoD2-NL-MonoNerdFont",
        )
        self.assertEqual(
            format_postscript_family_name("0xProtoD2 Mono Nerd Font"),
            "0xProtoD2-MonoNerdFont",
        )
        self.assertEqual(
            format_postscript_family_name("0xProtoD2 NL"),
            "0xProtoD2-NL",
        )

    def test_update_font_metadata_sets_family_specific_unique_id(self):
        """family alias별 output이 폰트 캐시에서 충돌하지 않도록 Unique ID를 갱신합니다."""
        from hangulify import update_font_metadata

        class FakeFont:
            familyname = "0xProto"

            def __init__(self):
                self.sfnt_names = []

            def appendSFNTName(self, language, name, value):
                self.sfnt_names.append((language, name, value))

        font = FakeFont()
        update_font_metadata(font, "Regular", "0xProto", "ZxProtoD2")

        self.assertEqual(font.fontname, "ZxProtoD2-Regular")
        self.assertIn(
            ("English (US)", "UniqueID", "ZxProtoD2-Regular"),
            font.sfnt_names,
        )

    def test_generated_font_output_paths_use_family_directories(self):
        """최종 output은 family alias 폴더에서 구분합니다."""
        from hangulify import get_output_dir

        self.assertEqual(
            get_output_dir("0xProtoD2"),
            os.path.join(BUILT_FONTS_PATH, "0xProtoD2"),
        )
        self.assertEqual(
            get_output_dir("ZxProtoD2 Mono Nerd Font"),
            os.path.join(BUILT_FONTS_PATH, "ZxProtoD2"),
        )
        self.assertEqual(
            get_output_dir("0xProtoD2 NL"),
            os.path.join(BUILT_FONTS_PATH, "0xProtoD2", "NL"),
        )
        self.assertEqual(
            get_output_dir("ZxProtoD2 NL Mono Nerd Font"),
            os.path.join(BUILT_FONTS_PATH, "ZxProtoD2", "NL"),
        )

    def test_nerd_font_does_not_generate_webfont(self):
        """Nerd Font Mono는 TTF만 생성합니다."""
        from hangulify import get_font_extensions

        self.assertEqual(get_font_extensions(is_nerd_font=False), ["ttf", "woff2"])
        self.assertEqual(get_font_extensions(is_nerd_font=True), ["ttf"])

    def test_generate_font_files_reports_failure(self):
        """폰트 파일 생성 실패는 호출자에게 실패로 전파합니다."""
        from hangulify import generate_font_files

        class FakeFont:
            fontname = "0xProtoD2-Regular"

            def generate(self, output_path):
                raise RuntimeError(f"failed: {output_path}")

        with mock.patch("hangulify.os.makedirs"):
            self.assertFalse(
                generate_font_files(
                    FakeFont(),
                    os.path.join("/tmp", "fonts"),
                    is_nerd_font=True,
                )
            )

    def test_generate_font_files_applies_built_font_version(self):
        """최종 font output에는 repo FONT_VERSION 값을 version 메타데이터로 적용합니다."""
        from hangulify import generate_font_files

        class FakeFont:
            fontname = "0xProtoD2-Regular"

            def __init__(self):
                self.version = "source-version"
                self.generated_versions = []
                self.sfnt_names = []

            def appendSFNTName(self, language, name, value):
                self.sfnt_names.append((language, name, value))

            def generate(self, output_path):
                self.generated_versions.append(self.version)

        font = FakeFont()
        with mock.patch("hangulify.os.makedirs"), \
            mock.patch("hangulify.read_built_font_version", return_value="v1.2.3"):
            self.assertTrue(
                generate_font_files(
                    font,
                    os.path.join("/tmp", "fonts"),
                    is_nerd_font=False,
                )
            )

        self.assertEqual(font.generated_versions, ["v1.2.3", "v1.2.3"])
        self.assertEqual(font.version, "v1.2.3")
        self.assertIn(("English (US)", "Version", "v1.2.3"), font.sfnt_names)

    def test_process_font_file_uses_given_output_directory(self):
        """단일 폰트 처리는 호출자가 넘긴 output 디렉터리를 그대로 사용합니다."""
        import hangulify

        class FakeFont:
            familyname = "0xProto"
            fontname = "0xProto-Regular"

        output_dirs = []

        def record_generate(font, output_dir, is_nerd_font):
            output_dirs.append(output_dir)
            return True

        def update_family(font, style, old_name, new_name, base_family_name=None):
            font.familyname = new_name

        with mock.patch.object(hangulify, "merge_korean_glyphs"), \
            mock.patch.object(hangulify, "get_font_style", return_value="Regular"), \
            mock.patch.object(hangulify, "update_font_metadata", update_family), \
            mock.patch.object(hangulify, "generate_font_files", record_generate):
            self.assertTrue(
                hangulify.process_font_file(
                    FakeFont(),
                    FakeFont(),
                    False,
                    "0xProto-Regular.ttf",
                    "/tmp/custom-output",
                )
            )

        self.assertEqual(
            output_dirs,
            [
                os.path.join("/tmp/custom-output", "0xProtoD2"),
                os.path.join("/tmp/custom-output", "ZxProtoD2"),
            ],
        )

    def test_process_font_file_can_limit_output_to_selected_family(self):
        """선택 family 빌드는 지정한 alias output만 생성합니다."""
        import hangulify

        class FakeFont:
            familyname = "0xProto"
            fontname = "0xProto-Regular"

        output_dirs = []

        def record_generate(font, output_dir, is_nerd_font):
            output_dirs.append(output_dir)
            return True

        def update_family(font, style, old_name, new_name, base_family_name=None):
            font.familyname = new_name

        with mock.patch.object(hangulify, "merge_korean_glyphs"), \
            mock.patch.object(hangulify, "get_font_style", return_value="Regular"), \
            mock.patch.object(hangulify, "update_font_metadata", update_family), \
            mock.patch.object(hangulify, "generate_font_files", record_generate):
            self.assertTrue(
                hangulify.process_font_file(
                    FakeFont(),
                    FakeFont(),
                    False,
                    "0xProto-Regular.ttf",
                    "/tmp/custom-output",
                    ("ZxProtoD2",),
                )
            )

        self.assertEqual(output_dirs, [os.path.join("/tmp/custom-output", "ZxProtoD2")])

    def test_process_font_variant_closes_fonts_and_reports_failure(self):
        """variant 처리 실패 시에도 열었던 폰트를 닫고 실패를 반환합니다."""
        import hangulify

        class FakeFont:
            def __init__(self, name):
                self.name = name
                self.closed = False

            def close(self):
                self.closed = True

        ko_font = FakeFont("ko")
        en_font = FakeFont("en")

        def fake_open(path):
            return ko_font if path == "/tmp/ko.ttf" else en_font

        fake_fontforge = mock.Mock(open=fake_open)

        with mock.patch.object(
            hangulify, "find_font_files", return_value=["/tmp/en.ttf"]
        ), mock.patch.object(
            hangulify, "fontforge", fake_fontforge
        ), mock.patch.object(
            hangulify,
            "process_font_file",
            side_effect=RuntimeError("generate failed"),
        ):
            self.assertFalse(
                hangulify._process_font_variant(
                    "Ligatures",
                    "/tmp/en",
                    False,
                    "regular",
                    "/tmp/ko.ttf",
                )
            )

        self.assertTrue(ko_font.closed)
        self.assertTrue(en_font.closed)

    def test_worker_args_parse_optional_family(self):
        """FontForge worker 인자는 선택 family를 해석합니다."""
        import hangulify

        self.assertEqual(
            hangulify.parse_worker_args(
                ["regular", "/tmp/ko.ttf", "/tmp/ko-nerd.ttf", "--family", "ZxProtoD2"]
            ),
            ("regular", "/tmp/ko.ttf", "/tmp/ko-nerd.ttf", ("ZxProtoD2",)),
        )
        self.assertEqual(
            hangulify.parse_worker_args(
                ["regular", "/tmp/ko.ttf", "--family", "0xProtoD2"]
            ),
            ("regular", "/tmp/ko.ttf", "/tmp/ko.ttf", ("0xProtoD2",)),
        )

    def test_build_weight_with_variants_reports_any_failure(self):
        """하나의 variant라도 실패하면 weight 빌드 전체를 실패로 봅니다."""
        import hangulify

        with mock.patch.object(
            hangulify,
            "_process_font_variant",
            side_effect=[True, False, True, True],
        ):
            self.assertFalse(
                hangulify.build_weight_with_variants(
                    "regular",
                    "/tmp/D2Coding-regular.ttf",
                    "/tmp/D2Coding-regular-nerd-mono.ttf",
                )
            )

    def test_nerd_font_patch_can_be_skipped_when_outputs_and_source_version_match(self):
        """Nerd Font Mono 패치 결과물과 기준 버전이 같으면 패치 단계를 건너뜁니다."""
        from build import get_expected_nerd_font_files, should_patch_nerd_fonts

        expected_files = get_expected_nerd_font_files(
            [
                os.path.join(config.EN_FONT_PATH, "0xProto-Regular.ttf"),
                os.path.join(config.EN_FONT_PATH, "0xProto-Bold.ttf"),
                os.path.join(config.EN_FONT_PATH, "0xProto-Italic.ttf"),
                os.path.join(config.NO_LIGATURE_FONT_PATH, "0xProto-Regular-NL.ttf"),
                os.path.join(config.NO_LIGATURE_FONT_PATH, "0xProto-Bold-NL.ttf"),
                os.path.join(config.NO_LIGATURE_FONT_PATH, "0xProto-Italic-NL.ttf"),
            ]
        )

        self.assertEqual(
            expected_files,
            [
                os.path.join(config.EN_NERD_FONT_PATH, "0xProtoNLNerdFontMono-Bold.ttf"),
                os.path.join(config.EN_NERD_FONT_PATH, "0xProtoNLNerdFontMono-Italic.ttf"),
                os.path.join(config.EN_NERD_FONT_PATH, "0xProtoNLNerdFontMono-Regular.ttf"),
                os.path.join(config.EN_NERD_FONT_PATH, "0xProtoNerdFontMono-Bold.ttf"),
                os.path.join(config.EN_NERD_FONT_PATH, "0xProtoNerdFontMono-Italic.ttf"),
                os.path.join(config.EN_NERD_FONT_PATH, "0xProtoNerdFontMono-Regular.ttf"),
            ],
        )
        with mock.patch("build.os.path.exists", return_value=True):
            self.assertFalse(should_patch_nerd_fonts(expected_files, "v3.4.0", "v3.4.0"))

    def test_nerd_font_patch_runs_when_source_version_differs(self):
        """기준 버전이 바뀌면 결과물이 있어도 다시 패치합니다."""
        from build import get_expected_nerd_font_files, should_patch_nerd_fonts

        expected_files = get_expected_nerd_font_files(
            [
                os.path.join(config.NO_LIGATURE_FONT_PATH, "0xProto-Regular-NL.ttf"),
                os.path.join(config.NO_LIGATURE_FONT_PATH, "0xProto-Bold-NL.ttf"),
                os.path.join(config.NO_LIGATURE_FONT_PATH, "0xProto-Italic-NL.ttf"),
            ]
        )

        self.assertTrue(should_patch_nerd_fonts(expected_files, "v3.3.0", "v3.4.0"))

    def test_nerd_font_patch_command_keeps_existing_arguments(self):
        """Nerd Font Mono 패치 명령 배열은 기존 옵션과 순서를 유지합니다."""
        from build import _build_nerd_font_patch_command

        self.assertEqual(
            _build_nerd_font_patch_command(
                "/usr/bin/fontforge",
                "/tmp/font-patcher",
                "/fonts/0xProtoNL-Regular.ttf",
            ),
            [
                "/usr/bin/fontforge",
                "-script",
                "/tmp/font-patcher",
                "/fonts/0xProtoNL-Regular.ttf",
                "--complete",
                "--mono",
                "--outputdir",
                config.EN_NERD_FONT_PATH,
                "--quiet",
            ],
        )

    def test_nerd_font_patch_fails_when_patcher_is_missing(self):
        """압축 해제 후 font-patcher 파일이 없으면 기존처럼 실패합니다."""
        from build import _patch_nerd_fonts_with_patcher

        with mock.patch("build.os.path.exists", return_value=False), mock.patch(
            "build.os.makedirs"
        ), mock.patch("build.subprocess.run") as run:
            self.assertFalse(
                _patch_nerd_fonts_with_patcher(
                    "/usr/bin/fontforge",
                    "/tmp/missing-patcher",
                    ["/fonts/0xProtoNL-Regular.ttf"],
                )
            )

        run.assert_not_called()

    def test_cached_font_patcher_is_reused(self):
        """로컬 캐시에 font-patcher가 있으면 다시 다운로드하지 않습니다."""
        import build

        with mock.patch("build.os.path.exists", return_value=True), \
            mock.patch("build._download_and_extract_font_patcher") as download:
            self.assertEqual(
                build._get_or_download_font_patcher(),
                os.path.join(config.FONT_PATCHER_CACHE_PATH, "font-patcher"),
            )

        download.assert_not_called()

    def test_font_patcher_is_cached_under_assets_when_missing(self):
        """font-patcher가 없으면 assets 하위 캐시에 다운로드합니다."""
        import build

        with mock.patch("build.os.path.exists", return_value=False), \
            mock.patch("build.os.makedirs") as makedirs, \
            mock.patch(
                "build._download_and_extract_font_patcher",
                return_value="/cached/font-patcher",
            ) as download:
            self.assertEqual(build._get_or_download_font_patcher(), "/cached/font-patcher")

        makedirs.assert_called_once_with(config.FONT_PATCHER_CACHE_PATH, exist_ok=True)
        download.assert_called_once_with(config.FONT_PATCHER_CACHE_PATH)

    def test_downloaded_font_patcher_is_extracted_to_flat_cache(self):
        """font-patcher와 지원 파일은 캐시 루트에 함께 압축 해제합니다."""
        import build

        class FakeArchive:
            def __init__(self, archive_path):
                self.archive_path = archive_path

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def extractall(self, cache_dir):
                extracted_dirs.append(cache_dir)

        extracted_dirs = []
        with mock.patch("build.urllib.request.urlretrieve") as download, \
            mock.patch("build.zipfile.ZipFile", FakeArchive), \
            mock.patch("build.os.remove") as remove:
            self.assertEqual(
                build._download_and_extract_font_patcher("/cache"),
                "/cache/font-patcher",
            )

        download.assert_called_once_with(config.FONT_PATCHER_URL, "/cache/FontPatcher.zip")
        self.assertEqual(extracted_dirs, ["/cache"])
        remove.assert_called_once_with("/cache/FontPatcher.zip")

    def test_nerd_font_version_is_written_only_after_all_fonts_succeed(self):
        """모든 패치 명령이 성공한 뒤에만 source version을 기록합니다."""
        import build

        source_fonts = [
            "/fonts/0xProto-Regular.ttf",
            "/fonts/0xProto-Bold.ttf",
            "/fonts/0xProtoNL-Regular.ttf",
            "/fonts/0xProtoNL-Bold.ttf",
        ]

        with mock.patch("build.shutil.which", return_value="/usr/bin/fontforge"), \
            mock.patch("build.find_nerd_font_source_fonts", return_value=source_fonts), \
            mock.patch("build.get_expected_nerd_font_files", return_value=["/out/r.ttf", "/out/b.ttf"]), \
            mock.patch("build.read_text_file", side_effect=["0xProto=2.501; NerdFontsPatcher=v3.4.0", "2.502"]), \
            mock.patch("build.get_font_patcher_version", return_value="v3.4.0"), \
            mock.patch("build.should_patch_nerd_fonts", return_value=True), \
            mock.patch("build._get_or_download_font_patcher", return_value="/tmp/font-patcher"), \
            mock.patch("build._patch_nerd_fonts_with_patcher", return_value=True) as patch_fonts, \
            mock.patch("build.write_text_file") as write_text_file:
            self.assertTrue(build.patch_nerd_fonts())

        patch_fonts.assert_called_once_with(
            "/usr/bin/fontforge",
            "/tmp/font-patcher",
            source_fonts,
        )
        write_text_file.assert_called_once_with(
            config.NERD_FONT_VERSION_PATH,
            "0xProto=2.502; NerdFontsPatcher=v3.4.0",
        )

    def test_nerd_font_version_is_not_written_when_any_font_fails(self):
        """패치 명령 중 하나라도 실패하면 source version을 기록하지 않습니다."""
        import build

        with mock.patch("build.shutil.which", return_value="/usr/bin/fontforge"), \
            mock.patch("build.find_nerd_font_source_fonts", return_value=["/fonts/0xProtoNL-Regular.ttf"]), \
            mock.patch("build.get_expected_nerd_font_files", return_value=["/out/r.ttf"]), \
            mock.patch("build.read_text_file", side_effect=["0xProto=2.501; NerdFontsPatcher=v3.4.0", "2.502"]), \
            mock.patch("build.get_font_patcher_version", return_value="v3.4.0"), \
            mock.patch("build.should_patch_nerd_fonts", return_value=True), \
            mock.patch("build._get_or_download_font_patcher", return_value="/tmp/font-patcher"), \
            mock.patch("build._patch_nerd_fonts_with_patcher", return_value=False), \
            mock.patch("build.write_text_file") as write_text_file:
            self.assertFalse(build.patch_nerd_fonts())

        write_text_file.assert_not_called()

if __name__ == '__main__':
    unittest.main(verbosity=2)
