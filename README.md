<div align="center">

# 🎬 MTS → MP4 Converter

**AVCHD 캠코더 영상을 MP4로 간편하게 변환하세요**

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-Powered-007808?style=for-the-badge&logo=ffmpeg&logoColor=white)](https://ffmpeg.org)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)]()

<br>

<img src="https://img.shields.io/badge/H.264-Encoding-FF6B6B?style=flat-square" alt="H.264"/>
<img src="https://img.shields.io/badge/AAC-Audio-4ECDC4?style=flat-square" alt="AAC"/>
<img src="https://img.shields.io/badge/GUI-ttkbootstrap-FFE66D?style=flat-square" alt="GUI"/>

<br><br>

*Sony, Canon, Panasonic 등 AVCHD 캠코더의 `.mts` / `.m2ts` 파일을 고품질 `.mp4`로 변환하는 데스크톱 앱*

</div>

---

## ✨ Features

<table>
<tr>
<td>

### 🎯 핵심 기능
- **일괄 변환** — 여러 MTS 파일을 한 번에 MP4로 변환
- **3단계 품질 프리셋** — 고화질 / 표준 / 저용량 선택
- **실시간 진행률** — 현재 파일 + 전체 진행률 동시 표시
- **⏱️ 남은시간 표시** — 변환 ETA를 실시간으로 계산

</td>
<td>

### 📹 카메라 자동 감지
- **USB 연결 자동 인식** — 캠코더를 꽂으면 자동 감지
- **새 영상만 불러오기** — 이미 변환한 파일은 자동 스킵
- **처리 로그** — JSON 기반 중복 방지 시스템
- **연결/해제 감지** — 실시간 드라이브 모니터링

</td>
</tr>
</table>

### 🔄 How Auto-Scan Works

```
캠코더 USB 연결 → J: 드라이브 감지 → STREAM 폴더 스캔 → 새 파일만 필터링 → 목록에 자동 추가
         │                                                        │
         │              processed_files.json ◄────────────────────┘
         │                (변환 완료 로그)                    기존 파일 자동 스킵
         │
         └── 연결 해제 시 자동 대기 → 재연결 대기
```

---

## 📦 Installation

### Prerequisites

| Requirement | Version | Note |
|:--|:--|:--|
| [Python](https://python.org) | 3.8+ | 설치 시 `Add to PATH` 체크 |
| [FFmpeg](https://ffmpeg.org/download.html) | 최신 권장 | 시스템 PATH에 추가 또는 앱 폴더에 배치 |

### Quick Start

```bash
# 1. 저장소 클론
git clone https://github.com/udd43/mtstomp4.git
cd mtstomp4

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 실행
python main.py
```

### EXE 빌드 (선택)

```bash
# build.bat 실행 또는 직접:
pyinstaller --noconfirm --onefile --windowed ^
  --name "MTS_to_MP4_Converter" ^
  --add-data "converter.py;." ^
  --hidden-import ttkbootstrap ^
  main.py

# 결과: dist/MTS_to_MP4_Converter.exe
```

---

## 🚀 Usage

### 기본 사용법

1. **파일 추가** — `📂 파일 추가` 또는 `📁 폴더 추가` 클릭
2. **출력 폴더 설정** — 변환된 MP4 저장 위치 선택
3. **품질 선택** — 고화질 / 표준 / 저용량 중 선택
4. **변환 시작** — `▶ 변환 시작` 클릭

### 자동 감지 모드 (캠코더 연결)

1. **`📹 자동 감지`** 버튼 클릭
2. 캠코더를 USB로 연결 (J: 드라이브)
3. 새로운 MTS 파일이 **자동으로** 목록에 추가됨
4. 변환 완료된 파일은 **다시 불러오지 않음**

> [!TIP]
> 자동 감지는 `J:\PRIVATE\AVCHD\BDMV\STREAM` 경로를 3초마다 확인합니다.
> 대부분의 Sony / Canon AVCHD 캠코더는 이 경로를 사용합니다.

---

## ⚙️ Quality Presets

| Preset | CRF | Speed | 설명 | 권장 용도 |
|:--|:--:|:--:|:--|:--|
| 🔴 **고화질** | 18 | slow | 최고 품질, 파일 크기 큼 | 보관용, 편집용 |
| 🟢 **표준** | 23 | medium | 균형 잡힌 품질과 크기 | 일반 사용 *(기본값)* |
| 🔵 **저용량** | 28 | fast | 작은 파일 크기 | 공유, 업로드용 |

---

## 🏗️ Project Structure

```
mtstomp4/
├── main.py              # GUI 애플리케이션 (ttkbootstrap)
├── converter.py         # FFmpeg 변환 엔진
├── scan_log.py          # 자동 감지 & 처리 로그 관리
├── requirements.txt     # Python 의존성
├── build.bat            # Windows EXE 빌드 스크립트
└── .gitignore
```

### 모듈 설명

| File | Description |
|:--|:--|
| [`main.py`](main.py) | ttkbootstrap 기반 GUI. 파일 관리, 진행률, ETA, 자동 스캔 UI |
| [`converter.py`](converter.py) | FFmpeg 프로세스 관리. 진행률 파싱, 품질 프리셋 정의 |
| [`scan_log.py`](scan_log.py) | 처리된 파일 JSON 로그. 파일명+크기+수정일 기반 중복 판별 |

---

## 🔧 Configuration

### 카메라 경로 변경

`main.py` 상단의 상수를 수정하세요:

```python
# 카메라 기본 경로
CAMERA_STREAM_PATH = r"J:\PRIVATE\AVCHD\BDMV\STREAM"
SCAN_INTERVAL_MS = 3000  # 스캔 주기 (밀리초)
```

### FFmpeg 배치

FFmpeg를 다음 위치 중 하나에 배치하면 자동으로 인식합니다:

```
1. ./ffmpeg/ffmpeg.exe    (앱 폴더의 ffmpeg 하위 폴더)
2. ./ffmpeg.exe           (앱 폴더에 직접)
3. 시스템 PATH            (환경변수에 등록)
```

---

## 📋 처리 로그 (processed_files.json)

변환이 완료된 파일은 자동으로 로그에 기록됩니다:

```json
{
  "processed": [
    {
      "key": "00001.MTS|1234567890|1721234567.0",
      "filename": "00001.MTS",
      "path": "J:\\PRIVATE\\AVCHD\\BDMV\\STREAM\\00001.MTS",
      "processed_at": "2026-07-18T12:00:00"
    }
  ]
}
```

> [!NOTE]
> 파일 식별은 **파일명 + 크기 + 수정일** 조합으로 이루어집니다.
> 같은 이름이더라도 새로 촬영한 영상은 별도로 인식됩니다.

---

## 🛠️ Tech Stack

<div align="center">

| Technology | Purpose |
|:--:|:--:|
| ![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) | Core Language |
| ![FFmpeg](https://img.shields.io/badge/FFmpeg-007808?style=flat-square&logo=ffmpeg&logoColor=white) | Video Encoding |
| ![Tkinter](https://img.shields.io/badge/ttkbootstrap-FFE66D?style=flat-square) | GUI Framework |

</div>

- **H.264 (libx264)** — 최고의 호환성을 가진 비디오 코덱
- **AAC 192kbps** — 고품질 오디오
- **faststart** — 웹 스트리밍 최적화 (moov atom 앞으로 이동)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">

**Made with ❤️ for videographers**

*AVCHD 캠코더 사용자를 위한 간편한 변환 도구*

</div>
