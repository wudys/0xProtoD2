from __future__ import annotations

import fontforge

from config import (
    EN_FONT_PATH,
    EN_FONT_VERSION_PATH,
    KO_FONT_PATH,
    KO_FONT_VERSION_PATH,
)
from hangulify import find_font_files


def _write_font_version(font_dir: str, version_path: str) -> None:
    font_files = find_font_files(font_dir, "regular")
    if not font_files:
        raise RuntimeError(f"Regular font not found in {font_dir}")

    font = fontforge.open(font_files[0])
    try:
        version = font.version.strip()
    finally:
        font.close()

    with open(version_path, "w", encoding="utf-8") as version_file:
        version_file.write(f"{version}\n")

    print(f"[INFO] 폰트 버전 갱신: {version_path} = {version}")


def main() -> None:
    _write_font_version(EN_FONT_PATH, EN_FONT_VERSION_PATH)
    _write_font_version(KO_FONT_PATH, KO_FONT_VERSION_PATH)


if __name__ == "__main__":
    main()
