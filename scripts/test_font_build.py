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
    KO_FONT_PATH,
    EN_NERD_FONT_PATH,
    BUILT_FONTS_PATH,
    ASSETS_PATH
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

    def test_user_facing_hangul_settings_compute_fixed_2_cell_width(self):
        """기본 사용자 설정은 평상시 한글 advance와 여백을 계산합니다."""
        import font_settings

        self.assertEqual(font_settings.HANGUL_WIDTH_RATIO, 1.613)
        self.assertEqual(font_settings.HANGUL_GLYPH_SCALE, 1.09)
        self.assertEqual(font_settings.HANGUL_SIDE_BEARING, 100)
        self.assertEqual(font_settings.get_hangul_advance_width(), 1000)
        self.assertAlmostEqual(
            font_settings.get_hangul_outline_scale(1000),
            0.981,
            places=4,
        )

    def test_nerd_mono_hangul_settings_use_separate_balance(self):
        """Nerd Font Mono는 일반 한글 설정과 별도 advance/scale을 사용합니다."""
        import font_settings

        self.assertEqual(font_settings.HANGUL_NERD_MONO_WIDTH_RATIO, 2.0)
        self.assertEqual(font_settings.HANGUL_NERD_MONO_GLYPH_SCALE, 0.94)
        self.assertEqual(font_settings.HANGUL_NERD_MONO_SIDE_BEARING, 90)
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

        def record_variant(label, en_font_path, is_nerd_font, weight, ko_font_path):
            calls.append((label, is_nerd_font, ko_font_path))

        with mock.patch.object(hangulify, "_process_font_variant", record_variant):
            hangulify.build_weight_with_variants(
                "regular",
                "/tmp/D2Coding-regular.ttf",
                "/tmp/D2Coding-regular-nerd-mono.ttf",
            )

        self.assertEqual(
            calls,
            [
                ("Ligatures", False, "/tmp/D2Coding-regular.ttf"),
                ("No-Ligatures", False, "/tmp/D2Coding-regular.ttf"),
                ("NerdFontMono", True, "/tmp/D2Coding-regular-nerd-mono.ttf"),
            ],
        )

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

    def test_preview_paths_are_under_assets_preview(self):
        """사용자 미리보기 산출물은 루트 preview 디렉터리에 모읍니다."""
        import preview

        self.assertEqual(preview.PREVIEW_PATH, "preview")

    def test_readme_preview_image_path_and_font_size(self):
        """README 대표 이미지는 별도 스크립트에서 같은 크기 폰트로 렌더링합니다."""
        import render_preview_image

        self.assertEqual(
            render_preview_image.PREVIEW_IMAGE_PATH,
            os.path.join(ASSETS_PATH, "preview.png"),
        )
        self.assertEqual(render_preview_image.PREVIEW_FONT_SIZE, 28)
        self.assertEqual(render_preview_image.HEADER_FONT_SIZE, 34)
        self.assertEqual(render_preview_image.FOOTER_FONT_SIZE, 24)

    def test_directory_structure(self):
        """필요한 디렉터리 구조가 존재하는지 테스트"""
        print("\n=== 디렉터리 구조 테스트 ===")

        # 필수 디렉터리들
        required_dirs = {
            "Assets": ASSETS_PATH,
            "English Font": EN_FONT_PATH,
            "Korean Font": KO_FONT_PATH,
            "Nerd Font": EN_NERD_FONT_PATH
        }

        for name, path in required_dirs.items():
            with self.subTest(directory=name):
                self.assertTrue(os.path.exists(path),
                    f"{name} 디렉터리가 존재하지 않습니다: {path}")
                print(f"✓ {name} 디렉터리 확인: {path}")

    def test_0xproto_output_configuration(self):
        """0xProtoD2/ZxProtoD2 산출물 구성이 올바른지 테스트"""
        self.assertEqual(config.OLD_FONT_NAME, "0xProto")
        self.assertEqual(config.ENGLISH_FONT_WIDTH, 620)
        self.assertEqual(config.ENGLISH_FONT_NF_WIDTH, 620)
        self.assertEqual(config.FONT_FAMILY_ALIASES, ["0xProtoD2", "ZxProtoD2"])
        self.assertEqual(
            config.FONT_FAMILY_OUTPUT_PATHS,
            {
                "0xProtoD2": os.path.join(BUILT_FONTS_PATH, "0xProtoD2"),
                "ZxProtoD2": os.path.join(BUILT_FONTS_PATH, "ZxProtoD2"),
            },
        )
        self.assertEqual(
            config.NO_LIGATURE_FONT_PATH,
            os.path.join(EN_FONT_PATH, "No-Ligatures"),
        )
        self.assertEqual(
            config.FONT_PATCHER_URL,
            "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/FontPatcher.zip",
        )
        self.assertEqual(
            config.NERD_FONT_VERSION_PATH,
            os.path.join(EN_NERD_FONT_PATH, "version"),
        )
        self.assertTrue(os.path.exists(config.NERD_FONT_VERSION_PATH))
        self.assertFalse(hasattr(config, "FONT_PATCHER_VERSION_URL"))
        self.assertFalse(hasattr(config, "NERD_FONT_PATCHER_SCRIPT_PATH"))
        self.assertEqual(config.RELEASE_FILES_PATH, "release_files")
        self.assertEqual(
            config.RELEASE_NOTES_PATH,
            os.path.join(config.RELEASE_FILES_PATH, "RELEASE_NOTES.md"),
        )
        self.assertEqual(
            config.EN_FONT_VERSION_PATH,
            os.path.join(EN_FONT_PATH, "version"),
        )
        self.assertEqual(
            config.KO_FONT_VERSION_PATH,
            os.path.join(KO_FONT_PATH, "version"),
        )
        self.assertTrue(os.path.exists(config.EN_FONT_VERSION_PATH))
        self.assertTrue(os.path.exists(config.KO_FONT_VERSION_PATH))
        self.assertEqual(
            config.RELEASE_ARCHIVE_NAMES,
            {
                "0xProtoD2": "0xProtoD2-fonts.zip",
                "ZxProtoD2": "ZxProtoD2-fonts.zip",
            },
        )
        self.assertFalse(hasattr(config, "RELEASE_SCRIPT_PATH"))
        self.assertFalse(
            os.path.exists(os.path.join(os.path.dirname(__file__), "build_release.sh"))
        )
        self.assertFalse(
            os.path.exists(os.path.join(os.path.dirname(__file__), "patch_nerd_fonts.sh"))
        )

    def test_font_files_existence(self):
        """각 디렉터리에 폰트 파일이 존재하는지 테스트"""
        print("\n=== 폰트 파일 존재 테스트 ===")

        font_dirs = {
            "English Font": EN_FONT_PATH,
            "Korean Font": KO_FONT_PATH,
        }

        for name, path in font_dirs.items():
            with self.subTest(directory=name):
                if os.path.exists(path):
                    ttf_files = [f for f in os.listdir(path) if f.lower().endswith('.ttf')]
                    self.assertGreater(len(ttf_files), 0,
                        f"{name} 디렉터리에 TTF 파일이 없습니다: {path}")
                    print(f"✓ {name}: {len(ttf_files)}개 TTF 파일 발견")
                    for ttf_file in ttf_files:
                        print(f"  - {ttf_file}")

    def test_font_weights(self):
        """Regular와 Bold 폰트가 각 디렉터리에 있는지 테스트"""
        print("\n=== 폰트 웨이트 테스트 ===")

        font_dirs = {
            "English Font": EN_FONT_PATH,
            "Korean Font": KO_FONT_PATH,
        }

        expected_weights = ['regular', 'bold']

        for name, path in font_dirs.items():
            with self.subTest(directory=name):
                if os.path.exists(path):
                    ttf_files = [f.lower() for f in os.listdir(path) if f.lower().endswith('.ttf')]

                    for weight in expected_weights:
                        weight_files = [f for f in ttf_files if weight in f]
                        if weight_files:
                            print(f"✓ {name} - {weight.capitalize()}: {len(weight_files)}개 파일")
                        else:
                            print(f"⚠ {name} - {weight.capitalize()}: 파일이 없습니다")

    def test_fontforge_import(self):
        """FontForge 모듈 임포트 테스트"""
        print("\n=== FontForge 모듈 테스트 ===")

        try:
            import fontforge
            print("✓ FontForge 모듈 임포트 성공")

            # 간단한 폰트 생성 테스트
            test_font = fontforge.font()
            test_font.fontname = "TestFont"
            print("✓ FontForge 폰트 객체 생성 성공")
            test_font.close()

        except ImportError as e:
            self.skipTest(f"FontForge Python 모듈이 없어 건너뜁니다: {e}")
        except Exception as e:
            self.fail(f"FontForge 테스트 중 오류 발생: {e}")

    def test_font_loading(self):
        """실제 폰트 파일 로딩 테스트"""
        print("\n=== 폰트 파일 로딩 테스트 ===")

        try:
            import fontforge

            font_dirs = [EN_FONT_PATH, KO_FONT_PATH, EN_NERD_FONT_PATH]
            dir_names = ["English Font", "Korean Font", "Nerd Font"]

            for i, (name, path) in enumerate(zip(dir_names, font_dirs)):
                with self.subTest(directory=name):
                    if os.path.exists(path):
                        ttf_files = [f for f in os.listdir(path) if f.lower().endswith('.ttf')]
                        if ttf_files:
                            test_file = os.path.join(path, ttf_files[0])
                            try:
                                font = fontforge.open(test_file)
                                print(f"✓ {name} 폰트 로드 성공: {ttf_files[0]}")
                                print(f"  패밀리명: {font.familyname}")
                                print(f"  폰트명: {font.fontname}")
                                print(f"  글리프 수: {len(font)}")
                                font.close()
                            except Exception as e:
                                self.fail(f"{name} 폰트 로드 실패 ({ttf_files[0]}): {e}")
                        else:
                            print(f"⚠ {name}: 테스트할 TTF 파일이 없습니다")

        except ImportError:
            self.skipTest("FontForge 모듈이 없어 폰트 로딩 테스트를 건너뜁니다")

    def test_hangulify_imports(self):
        """hangulify 모듈의 함수들이 제대로 임포트되는지 테스트"""
        print("\n=== Hangulify 모듈 테스트 ===")

        try:
            from hangulify import (
                find_font_files,
                merge_korean_glyphs,
                process_font_file
            )
            print("✓ hangulify 모듈 함수들 임포트 성공")

            # find_font_files 함수 테스트
            if os.path.exists(EN_FONT_PATH):
                regular_files = find_font_files(EN_FONT_PATH, "regular")
                bold_files = find_font_files(EN_FONT_PATH, "bold")
                print(f"✓ find_font_files 테스트 성공 (Regular: {len(regular_files)}, Bold: {len(bold_files)})")

        except ImportError as e:
            self.fail(f"hangulify 모듈 임포트 실패: {e}")
        except Exception as e:
            print(f"⚠ hangulify 함수 테스트 중 오류: {e}")

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
            "ZxProtoD2 NL Nerd Font Mono",
        )
        self.assertEqual(
            format_postscript_family_name("0xProtoD2 NL Nerd Font Mono"),
            "0xProtoD2-NL-NerdFontMono",
        )
        self.assertEqual(
            format_postscript_family_name("0xProtoD2 NL"),
            "0xProtoD2-NL",
        )

    def test_generated_font_output_paths_use_family_directories(self):
        """최종 산출물은 family alias 폴더에서 구분합니다."""
        from hangulify import get_output_dir

        self.assertEqual(
            get_output_dir("0xProtoD2"),
            os.path.join(BUILT_FONTS_PATH, "0xProtoD2"),
        )
        self.assertEqual(
            get_output_dir("ZxProtoD2 NL Nerd Font Mono"),
            os.path.join(BUILT_FONTS_PATH, "ZxProtoD2"),
        )

    def test_nerd_font_does_not_generate_webfont(self):
        """Nerd Font Mono는 TTF만 생성합니다."""
        from hangulify import get_font_extensions

        self.assertEqual(get_font_extensions(is_nerd_font=False), ["ttf", "woff2"])
        self.assertEqual(get_font_extensions(is_nerd_font=True), ["ttf"])

    def test_nerd_font_patch_can_be_skipped_when_outputs_and_source_version_match(self):
        """Nerd Font 패치 결과물과 0xProto 버전이 같으면 패치 단계를 건너뜁니다."""
        from build import get_expected_nerd_font_files, should_patch_nerd_fonts

        expected_files = get_expected_nerd_font_files(
            [
                os.path.join(config.NO_LIGATURE_FONT_PATH, "0xProto-Regular-NL.ttf"),
                os.path.join(config.NO_LIGATURE_FONT_PATH, "0xProto-Bold-NL.ttf"),
            ]
        )

        self.assertEqual(
            expected_files,
            [
                os.path.join(config.EN_NERD_FONT_PATH, "0xProtoNLNerdFontMono-Bold.ttf"),
                os.path.join(config.EN_NERD_FONT_PATH, "0xProtoNLNerdFontMono-Regular.ttf"),
            ],
        )
        self.assertFalse(should_patch_nerd_fonts(expected_files, "v3.4.0", "v3.4.0"))

    def test_nerd_font_patch_runs_when_source_version_differs(self):
        """0xProto 버전이 바뀌면 결과물이 있어도 다시 패치합니다."""
        from build import get_expected_nerd_font_files, should_patch_nerd_fonts

        expected_files = get_expected_nerd_font_files(
            [
                os.path.join(config.NO_LIGATURE_FONT_PATH, "0xProto-Regular-NL.ttf"),
                os.path.join(config.NO_LIGATURE_FONT_PATH, "0xProto-Bold-NL.ttf"),
            ]
        )

        self.assertTrue(should_patch_nerd_fonts(expected_files, "v3.3.0", "v3.4.0"))

    def test_nerd_font_patch_command_keeps_existing_arguments(self):
        """Nerd Font 패치 명령 배열은 기존 옵션과 순서를 유지합니다."""
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

    def test_nerd_font_version_is_written_only_after_all_fonts_succeed(self):
        """모든 패치 명령이 성공한 뒤에만 source version을 기록합니다."""
        import build

        source_fonts = [
            "/fonts/0xProtoNL-Regular.ttf",
            "/fonts/0xProtoNL-Bold.ttf",
        ]

        with mock.patch("build.shutil.which", return_value="/usr/bin/fontforge"), \
            mock.patch("build.find_no_ligature_fonts", return_value=source_fonts), \
            mock.patch("build.get_expected_nerd_font_files", return_value=["/out/r.ttf", "/out/b.ttf"]), \
            mock.patch("build.read_text_file", side_effect=["v3.3.0", "v3.4.0"]), \
            mock.patch("build.should_patch_nerd_fonts", return_value=True), \
            mock.patch("build._download_and_extract_font_patcher", return_value="/tmp/font-patcher"), \
            mock.patch("build._patch_nerd_fonts_with_patcher", return_value=True) as patch_fonts, \
            mock.patch("build.write_text_file") as write_text_file:
            self.assertTrue(build.patch_nerd_fonts())

        patch_fonts.assert_called_once_with(
            "/usr/bin/fontforge",
            "/tmp/font-patcher",
            source_fonts,
        )
        write_text_file.assert_called_once_with(config.NERD_FONT_VERSION_PATH, "v3.4.0")

    def test_nerd_font_version_is_not_written_when_any_font_fails(self):
        """패치 명령 중 하나라도 실패하면 source version을 기록하지 않습니다."""
        import build

        with mock.patch("build.shutil.which", return_value="/usr/bin/fontforge"), \
            mock.patch("build.find_no_ligature_fonts", return_value=["/fonts/0xProtoNL-Regular.ttf"]), \
            mock.patch("build.get_expected_nerd_font_files", return_value=["/out/r.ttf"]), \
            mock.patch("build.read_text_file", side_effect=["v3.3.0", "v3.4.0"]), \
            mock.patch("build.should_patch_nerd_fonts", return_value=True), \
            mock.patch("build._download_and_extract_font_patcher", return_value="/tmp/font-patcher"), \
            mock.patch("build._patch_nerd_fonts_with_patcher", return_value=False), \
            mock.patch("build.write_text_file") as write_text_file:
            self.assertFalse(build.patch_nerd_fonts())

        write_text_file.assert_not_called()

    def test_output_directory_creation(self):
        """출력 디렉터리 생성 테스트"""
        print("\n=== 출력 디렉터리 테스트 ===")

        # 임시로 built_fonts 디렉터리 생성 테스트
        test_output_dir = os.path.join(ASSETS_PATH, "test_built_fonts")

        try:
            os.makedirs(test_output_dir, exist_ok=True)
            self.assertTrue(os.path.exists(test_output_dir))
            print(f"✓ 출력 디렉터리 생성 성공: {test_output_dir}")

            # 정리
            if os.path.exists(test_output_dir):
                os.rmdir(test_output_dir)
                print("✓ 테스트 디렉터리 정리 완료")

        except Exception as e:
            self.fail(f"출력 디렉터리 생성 테스트 실패: {e}")


def run_detailed_analysis():
    """상세한 폰트 분석 정보 출력"""
    print("\n" + "="*60)
    print("상세 폰트 분석")
    print("="*60)

    font_dirs = {
        "English Font": EN_FONT_PATH,
        "Korean Font": KO_FONT_PATH,
        "Nerd Font": EN_NERD_FONT_PATH
    }

    for name, path in font_dirs.items():
        print(f"\n--- {name} ---")
        if os.path.exists(path):
            files = [f for f in os.listdir(path) if f.lower().endswith('.ttf')]
            for file in files:
                print(f"  📄 {file}")
                file_path = os.path.join(path, file)
                file_size = os.path.getsize(file_path)
                print(f"     크기: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")
        else:
            print(f"  ❌ 디렉터리가 존재하지 않습니다: {path}")


if __name__ == '__main__':
    print("0xProtoD2 폰트 빌드 테스트 시작")
    print("="*60)

    # 상세 분석 실행
    run_detailed_analysis()

    # 유닛 테스트 실행
    print("\n" + "="*60)
    print("유닛 테스트 실행")
    print("="*60)

    # verbosity=2로 설정하여 자세한 테스트 결과 출력
    unittest.main(verbosity=2, exit=False)

    print("\n" + "="*60)
    print("테스트 완료!")
    print("="*60)
