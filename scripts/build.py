import os
import re
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
    EN_NERD_FONT_PATH,
    FONT_FAMILY_ALIASES,
    FONT_PATCHER_CACHE_PATH,
    FONT_PATCHER_URL,
    get_family_aliases,
    get_prepared_korean_font_paths,
    get_prepared_korean_font_plan,
    NERD_FONT_VERSION_PATH,
    NO_LIGATURE_FONT_PATH,
)


def print_usage():
    """사용법 안내 메시지를 출력합니다."""
    print(f"python {sys.argv[0]} <subcommand>\n")
    print("subcommand:")
    print("    build [--family FAMILY] : assets 디렉터리의 폰트를 병합해 output 파일을 생성합니다.")
    print("    preview      : 빌드된 폰트의 HTML/PNG 미리보기를 생성합니다.")
    print("    test         : 폰트 빌드 환경을 테스트합니다.")
    print("    test:logic   : 빌드 로직과 스크립트 단위 테스트를 실행합니다.")
    print("    test:outputs : 빌드된 font output을 검증합니다.")
    print("    clean        : output 파일을 삭제합니다.")
    print(f"\nfamily values: {', '.join(FONT_FAMILY_ALIASES)}")


def parse_family_option(args):
    if not args:
        return get_family_aliases()
    if len(args) == 2 and args[0] == "--family":
        return get_family_aliases(args[1])

    raise ValueError("Usage: build [--family FAMILY]")


def check_font_directories():
    """필요한 폰트 디렉터리들이 존재하는지 확인합니다."""
    directories = {
        "영문 폰트": EN_FONT_PATH,
        "영문 No Ligatures 폰트": NO_LIGATURE_FONT_PATH,
        "한글 폰트": KO_FONT_PATH,
        "영문 Nerd Font Mono": EN_NERD_FONT_PATH
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


def find_patch_source_fonts(font_dir):
    """Nerd Font Mono 패치 대상이 되는 TTF 원본 폰트를 찾습니다."""
    if not os.path.exists(font_dir):
        return []

    font_files = []
    for filename in os.listdir(font_dir):
        lowered = filename.lower()
        if not lowered.endswith(".ttf"):
            continue
        if "regular" in lowered or "bold" in lowered or "italic" in lowered:
            font_files.append(os.path.join(font_dir, filename))

    return sorted(font_files)


def find_nerd_font_source_fonts():
    """Ligatures/NL Nerd Font Mono 패치 대상을 모두 찾습니다."""
    return sorted(
        find_patch_source_fonts(EN_FONT_PATH)
        + find_patch_source_fonts(NO_LIGATURE_FONT_PATH)
    )


def get_expected_nerd_font_files(source_fonts):
    """입력 폰트에 대응하는 Nerd Font Mono 결과물을 계산합니다."""
    expected_files = []
    for font_path in source_fonts:
        filename = os.path.basename(font_path)
        if "Bold" in filename:
            style = "Bold"
        elif "Italic" in filename:
            style = "Italic"
        elif "Regular" in filename:
            style = "Regular"
        else:
            continue

        family_suffix = "NLNerdFontMono" if "-NL" in filename else "NerdFontMono"
        expected_files.append(
            os.path.join(EN_NERD_FONT_PATH, f"0xProto{family_suffix}-{style}.ttf")
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
    """결과물이 없거나 기준 버전이 다르면 Nerd Font Mono를 다시 패치합니다."""
    if any(not os.path.exists(path) for path in expected_files):
        return True
    return current_version != source_version


def get_font_patcher_version(patcher_path=None):
    """font-patcher 스크립트에서 Nerd Fonts Patcher 버전을 읽습니다."""
    if patcher_path is None:
        patcher_path = os.path.join(FONT_PATCHER_CACHE_PATH, "font-patcher")

    content = read_text_file(patcher_path)
    if not content:
        return None

    match = re.search(r'^\s*version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    if not match:
        return None

    return f"v{match.group(1)}"


def get_nerd_font_dependency_version(source_version, patcher_version):
    """Nerd Font Mono 패치 캐시를 무효화할 기준 버전 문자열을 만듭니다."""
    return f"0xProto={source_version}; NerdFontsPatcher={patcher_version}"


def _download_and_extract_font_patcher(work_dir):
    """Nerd Fonts Patcher를 다운로드하고 압축을 해제한 뒤 실행 파일 경로를 반환합니다."""
    archive_path = os.path.join(work_dir, "FontPatcher.zip")
    print(f"[INFO] Nerd Fonts Patcher 다운로드 중: {FONT_PATCHER_URL}")
    urllib.request.urlretrieve(FONT_PATCHER_URL, archive_path)

    print("[INFO] Nerd Fonts Patcher 압축 해제 중")
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(work_dir)

    os.remove(archive_path)
    return os.path.join(work_dir, "font-patcher")


def _get_or_download_font_patcher():
    """로컬 캐시의 Nerd Fonts Patcher를 반환하고, 없으면 한 번만 다운로드합니다."""
    patcher_path = os.path.join(FONT_PATCHER_CACHE_PATH, "font-patcher")
    if os.path.exists(patcher_path):
        return patcher_path

    os.makedirs(FONT_PATCHER_CACHE_PATH, exist_ok=True)
    return _download_and_extract_font_patcher(FONT_PATCHER_CACHE_PATH)


def _build_nerd_font_patch_command(fontforge_bin, patcher_path, font_path):
    """Nerd Fonts Patcher 실행 명령을 만듭니다."""
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
    """다운로드된 Nerd Fonts Patcher로 입력 폰트들을 패치합니다."""
    if not os.path.exists(patcher_path):
        print(f"[ERROR] Nerd Fonts Patcher 실행 파일을 찾을 수 없습니다: {patcher_path}")
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
    """0xProto Ligatures/NL 폰트를 Nerd Font Mono로 패치합니다."""
    fontforge_bin = shutil.which("fontforge")
    if not fontforge_bin:
        print("[ERROR] fontforge 실행 파일을 찾을 수 없습니다.")
        return False

    source_fonts = find_nerd_font_source_fonts()
    if not source_fonts:
        print("[ERROR] Nerd Font Mono로 패치할 TTF 파일을 찾을 수 없습니다.")
        return False

    expected_files = get_expected_nerd_font_files(source_fonts)
    current_version = read_text_file(NERD_FONT_VERSION_PATH)
    source_version = read_text_file(EN_FONT_VERSION_PATH)
    if not source_version:
        print(f"[ERROR] 0xProto 버전 파일을 찾을 수 없습니다: {EN_FONT_VERSION_PATH}")
        return False

    try:
        patcher_path = _get_or_download_font_patcher()
        patcher_version = get_font_patcher_version(patcher_path)
        if not patcher_version:
            print(f"[ERROR] Nerd Fonts Patcher 버전을 읽을 수 없습니다: {patcher_path}")
            return False

        dependency_version = get_nerd_font_dependency_version(
            source_version,
            patcher_version,
        )
        if not should_patch_nerd_fonts(
            expected_files,
            current_version,
            dependency_version,
        ):
            print("[INFO] Nerd Font Mono 패치 결과물이 이미 있어 건너뜁니다.")
            return True

        if not _patch_nerd_fonts_with_patcher(
            fontforge_bin,
            patcher_path,
            source_fonts,
        ):
            return False

        write_text_file(NERD_FONT_VERSION_PATH, dependency_version)
    except Exception as e:
        print(f"[ERROR] Nerd Font Mono 패치 중 오류 발생: {e}")
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


def run_build_fonts(family_aliases=None):
    """한글 폰트를 weight별로 전처리한 뒤 Regular/Bold 병렬 빌드를 실행합니다."""
    family_aliases = get_family_aliases(family_aliases)
    fontforge_bin = shutil.which("fontforge")
    if not fontforge_bin:
        print("[ERROR] fontforge 실행 파일을 찾을 수 없습니다.")
        return False

    script_path = os.path.join(os.path.dirname(__file__), "hangulify.py")
    with tempfile.TemporaryDirectory() as work_dir:
        for weight in ("regular", "bold"):
            output_path, nerd_mono_output_path = get_prepared_korean_font_paths(
                work_dir,
                weight,
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

        processes = []
        for weight, (ko_font_path, nerd_mono_ko_font_path) in get_prepared_korean_font_plan(
            work_dir
        ).items():
            command = [
                fontforge_bin,
                "-script",
                script_path,
                "--worker",
                weight,
                ko_font_path,
                nerd_mono_ko_font_path,
            ]
            if len(family_aliases) == 1:
                command.extend(["--family", family_aliases[0]])
            processes.append(subprocess.Popen(command))

        return_codes = [process.wait() for process in processes]
        return all(return_code == 0 for return_code in return_codes)


def refresh_source_font_versions():
    """소스 폰트의 version 메타데이터를 버전 파일에 반영합니다."""
    fontforge_bin = shutil.which("fontforge")
    if not fontforge_bin:
        print("[ERROR] fontforge 실행 파일을 찾을 수 없습니다.")
        return False

    script_path = os.path.join(
        os.path.dirname(__file__),
        "refresh_source_font_versions.py",
    )
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


def run_python_test_script(script_name: str) -> bool:
    """현재 Python 실행 파일로 지정된 테스트 스크립트를 실행합니다."""
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    result = subprocess.run([sys.executable, script_path], check=False)
    return result.returncode == 0


def clean():
    """output 파일을 삭제합니다."""
    print("[INFO] output 파일 삭제 중")
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
        try:
            family_aliases = parse_family_option(sys.argv[2:])
        except ValueError as e:
            print(f"[ERROR] {e}")
            print_usage()
            exit(1)

        print("[INFO] 폰트 버전 파일 갱신 중")
        if not refresh_source_font_versions():
            exit(1)
        print("[INFO] Nerd Font Mono 패치 시작")
        if not patch_nerd_fonts():
            exit(1)
        print("[INFO] 폰트 디렉터리 확인 중")
        if check_font_directories():
            print("[INFO] 폰트 빌드 시작")
            if not run_build_fonts(family_aliases):
                exit(1)
        else:
            print("[ERROR] 폰트 빌드에 필요한 파일이 준비되지 않았습니다.")
            exit(1)
    elif subcommand == "test":
        success = test_font_build()
        if not success:
            exit(1)
    elif subcommand == "test:logic":
        if not run_python_test_script("test_build_logic.py"):
            exit(1)
    elif subcommand == "test:outputs":
        if not run_python_test_script("test_built_font_outputs.py"):
            exit(1)
    elif subcommand == "preview":
        from preview_assets import generate_preview

        if not generate_preview():
            exit(1)
    elif subcommand == "clean":
        clean()
    else:
        print_usage()
        exit(1)


if __name__ == "__main__":
    main()
