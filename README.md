# 0xProtoD2

![GitHub release (latest by date)](https://img.shields.io/github/v/release/wudys/0xProtoD2?style=flat-square)
![License](https://img.shields.io/github/license/wudys/0xProtoD2?style=flat-square)
![Build Status](https://img.shields.io/github/actions/workflow/status/wudys/0xProtoD2/release-font.yml?style=flat-square)

0xProtoD2는 [0xProto](https://github.com/0xType/0xProto)의 코드 가독성과 [D2Coding](https://github.com/naver/d2codingfont)의 한글 경험을 함께 담은 프로그래밍 폰트입니다.

대체 폰트나 보조 폰트를 지정하기 어려운 환경에서도 코드와 주석, 문서를 자연스럽게 읽을 수 있습니다.

![0xProtoD2 preview](assets/preview.png)

## 특징

- **코드 가독성**: 비슷한 글자를 구분하기 쉬운 형태, 작은 크기에서도 읽기 좋은 여백, 의미와 형태를 과하게 바꾸지 않는 ligature 정책을 유지합니다.
- **자연스러운 한글 표시**: 코드와 주석, 문서가 같은 패밀리 안에서 어색하게 튀지 않도록 한글 폭, 외곽선 크기, 좌우 여백을 조정했습니다.
- **용도별 패밀리 제공**: Ligatures, No Ligatures, Nerd Font Mono, NL Nerd Font Mono를 제공합니다.
- **빌드 설정 제공**: 한글 폭, 외곽선 크기, 좌우 여백을 빌드 시 조정할 수 있습니다.

## 설치

[Releases](https://github.com/wudys/0xProtoD2/releases/latest)에서 원하는 패밀리를 내려받아 설치합니다.

| 패밀리 구성                 | 패밀리                        | 추천 환경                                     |
| --------------------------- | ----------------------------- | --------------------------------------------- |
| Ligatures                   | `0xProtoD2`                   | 코드 에디터, IDE                              |
| No Ligatures                | `0xProtoD2 NL`                | ligature를 완전히 끄고 싶은 환경              |
| Nerd Font Mono              | `0xProtoD2 Nerd Font Mono`    | 터미널에서 아이콘과 ligature를 함께 쓰는 환경 |
| No Ligatures Nerd Font Mono | `0xProtoD2 NL Nerd Font Mono` | 터미널, Vim/Neovim의 안정적인 기본 선택       |

각 패밀리는 Regular, Bold, Italic 스타일을 포함하며, `ZxProtoD2` 호환 패밀리로도 제공합니다.

Italic의 한글 글리프는 D2Coding Regular를 바탕으로 하되, Italic 빌드에서는 기울임 보정을 적용합니다.

## 빌드

### 요구사항

- Python 3.7+
- FontForge
- FontForge Python 바인딩
- Nerd Fonts Patcher 다운로드용 인터넷 연결(캐시가 없거나 버전이 바뀐 경우)
- `fonttools`, `pillow`(빌드 결과 검증/미리보기 생성 시)

#### macOS

```bash
brew install fontforge
```

#### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install fontforge python3-fontforge
```

#### 빌드 및 테스트

최종 빌드 폰트의 release version 메타데이터는 repo 최상위 `FONT_VERSION` 파일을 사용합니다.

```bash
# 전체 패밀리 빌드
python3 scripts/build.py build

# 특정 family만 빌드(0xProtoD2 또는 ZxProtoD2)
python3 scripts/build.py build --family ZxProtoD2

# 빌드 로직 테스트
python3 scripts/build.py test:logic

# 빌드 결과 테스트
python3 scripts/build.py test:outputs
```

`--family`는 빌드할 family만 제한합니다. 소스 버전 갱신, Nerd Font Mono 패치 확인, D2Coding 전처리는 공통으로 실행됩니다.

#### 미리보기 생성

```bash
# 미리보기 생성에는 Pillow와 fontTools가 추가로 필요합니다.
python3 -m pip install pillow fonttools
python3 scripts/build.py preview
```

`preview/balance-comparison.png`에는 현재 설정값과 D2Coding/0xProtoD2 렌더링 비교가 함께 표시됩니다.

`preview/metrics.json`에는 실제 advance width 측정값이 저장됩니다.

## 커스텀 설정

한글 폭과 외곽선 크기는 `scripts/font_settings.py` 또는 같은 이름의 환경 변수로 조정할 수 있습니다.
Nerd Font Mono 계열은 터미널 정렬에 맞춘 별도 기본값을 사용합니다.

| 설정                            |  기본값 | 설명                                          |
| ------------------------------- | ------: | --------------------------------------------- |
| `HANGUL_WIDTH_RATIO`            | `1.613` | 폰트의 기본 한글 advance width 비율           |
| `HANGUL_GLYPH_SCALE`            |  `1.09` | 폰트의 기본 한글 외곽선 크기                  |
| `HANGUL_SIDE_BEARING`           |   `100` | 폰트의 기본 한글 좌우 여백                    |
| `HANGUL_NERD_MONO_WIDTH_RATIO`  |   `2.0` | Nerd Font Mono 계열의 한글 advance width 비율 |
| `HANGUL_NERD_MONO_GLYPH_SCALE`  |  `0.94` | Nerd Font Mono 계열의 한글 외곽선 크기        |
| `HANGUL_NERD_MONO_SIDE_BEARING` |    `90` | Nerd Font Mono 계열의 한글 좌우 여백          |

## FAQ

### 폰트 이름이 왜 두 개인가요?

`0xProtoD2`와 `ZxProtoD2`는 같은 글리프를 가진 같은 폰트입니다. [<관련 내용>](https://github.com/0xType/0xProto/pull/112)

`0xProtoD2` 이름은 OpenType 표준상 문제가 없지만, 일부 애플리케이션/플랫폼 호환성을 위해 `ZxProtoD2`도 함께 제공합니다.

### WOFF2 파일도 제공하나요?

Ligatures 패밀리와 `NL` 패밀리는 WOFF2 파일도 제공합니다.
Nerd Font Mono 계열은 TTF만 제공합니다.

## 라이선스

이 프로젝트는 [LICENSE](LICENSE)을 따릅니다.

- [0xProto](https://github.com/0xType/0xProto/blob/main/LICENSE): SIL OFL 1.1
- [D2Coding](https://github.com/naver/d2codingfont/wiki/Open-Font-License): SIL OFL 1.1
- [Nerd Fonts Patcher](https://github.com/ryanoasis/nerd-fonts/blob/master/LICENSE): MIT License
- Forked from [FiraD2](https://github.com/partrita/FiraD2/blob/main/LICENSE): SIL OFL 1.1

각 라이선스 고지는 유지해야 합니다.
