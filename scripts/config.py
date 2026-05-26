import os

# =======================================
#  빌드 및 경로 구성
# =======================================
# 에셋 디렉터리 경로
ASSETS_PATH: str = "assets"
# 최종 폰트 파일이 저장될 디렉터리입니다.
BUILT_FONTS_PATH: str = os.path.join(ASSETS_PATH, "built_fonts")
# 최종 산출물의 release version 파일
BUILT_FONT_VERSION_PATH: str = "FONT_VERSION"
# 릴리즈 압축 파일이 저장될 디렉터리입니다.
RELEASE_FILES_PATH: str = "release_files"
RELEASE_NOTES_PATH: str = os.path.join(RELEASE_FILES_PATH, "RELEASE_NOTES.md")
# 폰트 이름 설정
OLD_FONT_NAME: str = "0xProto"
FONT_FAMILY_ALIASES: list[str] = ["0xProtoD2", "ZxProtoD2"]
FONT_FAMILY_OUTPUT_PATHS: dict[str, str] = {
    family_name: os.path.join(BUILT_FONTS_PATH, family_name)
    for family_name in FONT_FAMILY_ALIASES
}


def get_release_archive_name(family_name: str, version: str) -> str:
    return f"{family_name}-fonts-{version}.zip"

# =======================================
#  폰트 디렉터리 경로 구성
# =======================================
# 영문 폰트 디렉터리 경로
EN_FONT_PATH: str = os.path.join(ASSETS_PATH, "en_font")
# 영문 폰트 버전 파일
EN_FONT_VERSION_PATH: str = os.path.join(EN_FONT_PATH, "version")
# 영문 No Ligatures 폰트 디렉터리 경로
NO_LIGATURE_FONT_PATH: str = os.path.join(EN_FONT_PATH, "No-Ligatures")
# 한글 폰트 디렉터리 경로
KO_FONT_PATH: str = os.path.join(ASSETS_PATH, "ko_font")
# 한글 폰트 버전 파일
KO_FONT_VERSION_PATH: str = os.path.join(KO_FONT_PATH, "version")
# 영문 너드 폰트 디렉터리 경로
EN_NERD_FONT_PATH: str = os.path.join(ASSETS_PATH, "en_nerd_font")
# Nerd Font Patcher 버전 파일
NERD_FONT_VERSION_PATH: str = os.path.join(EN_NERD_FONT_PATH, "version")
# Nerd Font Patcher 배포 아카이브
FONT_PATCHER_URL: str = "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/FontPatcher.zip"
FONT_PATCHER_CACHE_PATH: str = os.path.join(ASSETS_PATH, "font_patcher")

# =======================================
#  폰트 설정
# =======================================
KOREAN_FONT_WIDTH: int = 1000
ENGLISH_FONT_WIDTH: int = 620


def get_prepared_korean_font_paths(work_dir: str, weight: str) -> tuple[str, str]:
    return (
        os.path.join(work_dir, f"D2Coding-{weight}.ttf"),
        os.path.join(work_dir, f"D2Coding-{weight}-nerd-mono.ttf"),
    )


def get_prepared_korean_font_plan(
    work_dir: str,
    prepared_weights: set[str] | None = None,
) -> dict[str, tuple[str, str]]:
    if prepared_weights is None:
        prepared_weights = {"regular", "bold"}

    regular_paths = get_prepared_korean_font_paths(work_dir, "regular")
    plan = {}
    if "regular" in prepared_weights:
        plan["regular"] = regular_paths
    if "bold" in prepared_weights:
        plan["bold"] = get_prepared_korean_font_paths(work_dir, "bold")
    if "regular" in prepared_weights:
        plan["italic"] = regular_paths

    return plan
