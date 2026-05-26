import os
import sys
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile

from config import (
    BUILT_FONTS_PATH,
    EN_FONT_PATH,
    EN_FONT_VERSION_PATH,
    KO_FONT_PATH,
    KO_FONT_VERSION_PATH,
    EN_NERD_FONT_PATH,
    FONT_PATCHER_URL,
    NERD_FONT_VERSION_PATH,
    NO_LIGATURE_FONT_PATH,
)


def print_usage():
    """사용법 안내 메시지를 출력합니다."""
    print(f"python {sys.argv[0]} <subcommand>\n")
    print("subcommand:")
    print("    build  : assets 디렉터리의 폰트를 병합하고 출력합니다.")
    print("    preview: 빌드된 폰트의 HTML/PNG 미리보기를 생성합니다.")
    print("    test   : 폰트 빌드 프로세스를 테스트합니다.")
    print("    clean  : 출력 파일을 삭제합니다.")


def check_font_directories():
    """필요한 폰트 디렉터리들이 존재하는지 확인합니다."""
    directories = {
        "영문 폰트": EN_FONT_PATH,
        "영문 No Ligatures 폰트": NO_LIGATURE_FONT_PATH,
        "한글 폰트": KO_FONT_PATH,
        "너드 폰트": EN_NERD_FONT_PATH
    }

    missing_dirs = []
    for name, path in directories.items():
        if not os.path.exists(path):
            missing_dirs.append((name, path))
        else:
            ttf_files = [f for f in os.listdir(path) if f.lower().endswith('.ttf')]
            if not ttf_files:
                print(f"[WARNING] {name} 디렉터리({path})에 TTF 파일이 없습니다.")
            else:
                print(f"[INFO] {name} 디렉터리 확인: {len(ttf_files)}개 폰트 파일 발견")

    if missing_dirs:
        print("[ERROR] 다음 디렉터리들이 누락되었습니다:")
        for name, path in missing_dirs:
            print(f"  - {name}: {path}")
        return False

    return True


def find_no_ligature_fonts():
    """Nerd Font 패치 대상이 되는 No Ligatures Regular/Bold 폰트를 찾습니다."""
    if not os.path.exists(NO_LIGATURE_FONT_PATH):
        return []

    font_files = []
    for filename in os.listdir(NO_LIGATURE_FONT_PATH):
        lowered = filename.lower()
        if not lowered.endswith(".ttf"):
            continue
        if "regular" in lowered or "bold" in lowered:
            font_files.append(os.path.join(NO_LIGATURE_FONT_PATH, filename))

    return sorted(font_files)


def get_expected_nerd_font_files(source_fonts):
    """No Ligatures 입력 폰트에 대응하는 Nerd Font Mono 결과물을 계산합니다."""
    expected_files = []
    for font_path in source_fonts:
        filename = os.path.basename(font_path)
        if "Bold" in filename:
            style = "Bold"
        elif "Regular" in filename:
            style = "Regular"
        else:
            continue

        expected_files.append(
            os.path.join(EN_NERD_FONT_PATH, f"0xProtoNLNerdFontMono-{style}.ttf")
        )

    return sorted(expected_files)


def read_text_file(path):
    """텍스트 파일을 읽고 없으면 None을 반환합니다."""
    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as file:
        return file.read().strip()


def write_text_file(path, value):
    """텍스트 파일을 생성하고 값을 저장합니다."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        file.write(f"{value}\n")


def should_patch_nerd_fonts(expected_files, current_version, source_version):
    """결과물이 없거나 0xProto 원본 버전이 다르면 Nerd Font를 다시 패치합니다."""
    if any(not os.path.exists(path) for path in expected_files):
        return True
    return current_version != source_version


def _download_and_extract_font_patcher(work_dir):
    """Nerd Font Patcher를 다운로드하고 압축을 해제한 뒤 실행 파일 경로를 반환합니다."""
    archive_path = os.path.join(work_dir, "FontPatcher.zip")
    patcher_dir = os.path.join(work_dir, "NerdFontPatcher")
    print(f"[INFO] Nerd Font Patcher 다운로드 중: {FONT_PATCHER_URL}")
    urllib.request.urlretrieve(FONT_PATCHER_URL, archive_path)

    print("[INFO] Nerd Font Patcher 압축 해제 중")
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(patcher_dir)

    return os.path.join(patcher_dir, "font-patcher")


def _build_nerd_font_patch_command(fontforge_bin, patcher_path, font_path):
    """Nerd Font Patcher 실행 명령을 만듭니다."""
    return [
        fontforge_bin,
        "-script",
        patcher_path,
        font_path,
        "--complete",
        "--mono",
        "--outputdir",
        EN_NERD_FONT_PATH,
        "--quiet",
    ]


def _patch_nerd_fonts_with_patcher(fontforge_bin, patcher_path, source_fonts):
    """다운로드된 Nerd Font Patcher로 입력 폰트들을 패치합니다."""
    if not os.path.exists(patcher_path):
        print(f"[ERROR] Nerd Font Patcher 실행 파일을 찾을 수 없습니다: {patcher_path}")
        return False

    os.makedirs(EN_NERD_FONT_PATH, exist_ok=True)
    for font_path in source_fonts:
        command = _build_nerd_font_patch_command(
            fontforge_bin,
            patcher_path,
            font_path,
        )
        result = subprocess.run(command, check=False)
        if result.returncode != 0:
            return False

    return True


def patch_nerd_fonts():
    """0xProto No Ligatures 폰트를 Nerd Font Mono로 패치합니다."""
    fontforge_bin = shutil.which("fontforge")
    if not fontforge_bin:
        print("[ERROR] fontforge 실행 파일을 찾을 수 없습니다.")
        return False

    source_fonts = find_no_ligature_fonts()
    if not source_fonts:
        print(f"[ERROR] {NO_LIGATURE_FONT_PATH}에서 패치할 TTF 파일을 찾을 수 없습니다.")
        return False

    expected_files = get_expected_nerd_font_files(source_fonts)
    current_version = read_text_file(NERD_FONT_VERSION_PATH)
    source_version = read_text_file(EN_FONT_VERSION_PATH)
    if not source_version:
        print(f"[ERROR] 0xProto 버전 파일을 찾을 수 없습니다: {EN_FONT_VERSION_PATH}")
        return False

    if not should_patch_nerd_fonts(expected_files, current_version, source_version):
        print("[INFO] Nerd Font Mono 패치 결과물이 이미 있어 건너뜁니다.")
        return True

    try:
        with tempfile.TemporaryDirectory() as work_dir:
            patcher_path = _download_and_extract_font_patcher(work_dir)
            if not _patch_nerd_fonts_with_patcher(
                fontforge_bin,
                patcher_path,
                source_fonts,
            ):
                return False

            write_text_file(NERD_FONT_VERSION_PATH, source_version)
    except Exception as e:
        print(f"[ERROR] Nerd Font 패치 중 오류 발생: {e}")
        return False

    return True


def run_prepare_korean_font(
    fontforge_bin, script_path, weight, output_path, is_nerd_font=False
):
    command = [
        fontforge_bin,
        "-script",
        script_path,
        "--prepare-ko",
        weight,
        output_path,
    ]
    if is_nerd_font:
        command.append("--nerd-mono")

    result = subprocess.run(command, check=False)
    return result.returncode == 0


def run_build_fonts():
    """한글 폰트를 weight별로 전처리한 뒤 Regular/Bold 병렬 빌드를 실행합니다."""
    fontforge_bin = shutil.which("fontforge")
    if not fontforge_bin:
        print("[ERROR] fontforge 실행 파일을 찾을 수 없습니다.")
        return False

    script_path = os.path.join(os.path.dirname(__file__), "hangulify.py")
    with tempfile.TemporaryDirectory() as work_dir:
        prepared_fonts = {}
        for weight in ("regular", "bold"):
            output_path = os.path.join(work_dir, f"D2Coding-{weight}.ttf")
            nerd_mono_output_path = os.path.join(
                work_dir, f"D2Coding-{weight}-nerd-mono.ttf"
            )
            if not run_prepare_korean_font(
                fontforge_bin, script_path, weight, output_path
            ):
                return False
            if not run_prepare_korean_font(
                fontforge_bin,
                script_path,
                weight,
                nerd_mono_output_path,
                is_nerd_font=True,
            ):
                return False
            prepared_fonts[weight] = (output_path, nerd_mono_output_path)

        processes = [
            subprocess.Popen(
                [
                    fontforge_bin,
                    "-script",
                    script_path,
                    "--worker",
                    weight,
                    ko_font_path,
                    nerd_mono_ko_font_path,
                ]
            )
            for weight, (ko_font_path, nerd_mono_ko_font_path) in prepared_fonts.items()
        ]
        return_codes = [process.wait() for process in processes]
        return all(return_code == 0 for return_code in return_codes)


def update_font_versions():
    """소스 폰트의 version 메타데이터를 버전 파일에 반영합니다."""
    fontforge_bin = shutil.which("fontforge")
    if not fontforge_bin:
        print("[ERROR] fontforge 실행 파일을 찾을 수 없습니다.")
        return False

    script_path = os.path.join(os.path.dirname(__file__), "write_font_versions.py")
    result = subprocess.run([fontforge_bin, "-script", script_path], check=False)
    return result.returncode == 0


def test_font_build():
    """폰트 빌드 프로세스를 테스트합니다."""
    print("[INFO] 폰트 빌드 테스트 시작")

    if not check_font_directories():
        print("[ERROR] 필요한 폰트 디렉터리가 누락되었습니다.")
        return False

    try:
        # FontForge 모듈 임포트 테스트
        import fontforge
        print("[INFO] FontForge 모듈 로드 성공")

        # 각 디렉터리에서 첫 번째 폰트 파일 로드 테스트
        test_dirs = [EN_FONT_PATH, KO_FONT_PATH, EN_NERD_FONT_PATH]
        for test_dir in test_dirs:
            ttf_files = [f for f in os.listdir(test_dir) if f.lower().endswith('.ttf')]
            if ttf_files:
                test_file = os.path.join(test_dir, ttf_files[0])
                try:
                    font = fontforge.open(test_file)
                    print(f"[INFO] 폰트 로드 테스트 성공: {ttf_files[0]} (Family: {font.familyname})")
                    font.close()
                except Exception as e:
                    print(f"[ERROR] 폰트 로드 테스트 실패 ({ttf_files[0]}): {e}")
                    return False

        print("[INFO] 모든 테스트가 성공했습니다. 폰트 빌드를 진행할 수 있습니다.")
        return True

    except ImportError as e:
        print(f"[ERROR] FontForge 모듈을 찾을 수 없습니다: {e}")
        print("[INFO] FontForge 설치: pip install fontforge-python 또는 시스템 패키지 관리자 사용")
        return False
    except Exception as e:
        print(f"[ERROR] 테스트 중 오류 발생: {e}")
        return False


def clean():
    """출력 파일을 삭제합니다."""
    print("[INFO] 출력 파일 삭제 중")
    if os.path.exists(BUILT_FONTS_PATH):
        shutil.rmtree(BUILT_FONTS_PATH)
        print(f"[INFO] {BUILT_FONTS_PATH} 디렉터리를 삭제했습니다.")
    else:
        print(f'[INFO] "{BUILT_FONTS_PATH}" 디렉터리를 찾을 수 없어 건너뜁니다.')




def main():
    if len(sys.argv) == 1:
        print_usage()
        exit(1)

    subcommand = sys.argv[1]

    if subcommand == "build":
        print("[INFO] 폰트 버전 파일 갱신 중")
        if not update_font_versions():
            exit(1)
        print("[INFO] Nerd Font Mono 패치 시작")
        if not patch_nerd_fonts():
            exit(1)
        print("[INFO] 폰트 디렉터리 확인 중")
        if check_font_directories():
            print("[INFO] 폰트 빌드 시작")
            if not run_build_fonts():
                exit(1)
        else:
            print("[ERROR] 폰트 빌드에 필요한 파일이 준비되지 않았습니다.")
            exit(1)
    elif subcommand == "test":
        success = test_font_build()
        if not success:
            exit(1)
    elif subcommand == "preview":
        from build_preview import generate_preview

        if not generate_preview():
            exit(1)
    elif subcommand == "clean":
        clean()
    else:
        print_usage()
        exit(1)


if __name__ == "__main__":
    main()
