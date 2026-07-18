"""
MTS → MP4 변환 엔진 모듈
FFmpeg를 사용하여 MTS(AVCHD) 파일을 MP4로 변환합니다.
"""

import subprocess
import re
import os
import shutil
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class ConvertPreset:
    """변환 품질 프리셋"""
    name: str
    label: str
    crf: int          # Constant Rate Factor (낮을수록 고품질)
    preset: str       # FFmpeg encoding preset
    description: str


# 품질 프리셋 정의
PRESETS = {
    "high": ConvertPreset(
        name="high",
        label="고화질",
        crf=18,
        preset="slow",
        description="최고 품질 (파일 크기 큼)"
    ),
    "standard": ConvertPreset(
        name="standard",
        label="표준",
        crf=23,
        preset="medium",
        description="균형 잡힌 품질과 크기"
    ),
    "compact": ConvertPreset(
        name="compact",
        label="저용량",
        crf=28,
        preset="fast",
        description="작은 파일 크기 (품질 다소 낮음)"
    ),
}


def find_ffmpeg() -> Optional[str]:
    """
    FFmpeg 실행 파일 경로를 찾습니다.
    1) 실행 파일 옆의 ffmpeg 폴더
    2) 시스템 PATH
    """
    # 실행 파일(또는 스크립트) 옆에 ffmpeg.exe가 있는지 확인
    base_dir = os.path.dirname(os.path.abspath(__file__))
    local_ffmpeg = os.path.join(base_dir, "ffmpeg", "ffmpeg.exe")
    if os.path.isfile(local_ffmpeg):
        return local_ffmpeg

    local_ffmpeg2 = os.path.join(base_dir, "ffmpeg.exe")
    if os.path.isfile(local_ffmpeg2):
        return local_ffmpeg2

    # 시스템 PATH에서 찾기
    found = shutil.which("ffmpeg")
    if found:
        return found

    return None


def get_duration(filepath: str, ffmpeg_path: str) -> float:
    """FFprobe 대신 FFmpeg로 영상 길이(초)를 가져옵니다."""
    ffprobe_path = ffmpeg_path.replace("ffmpeg.exe", "ffprobe.exe").replace("ffmpeg", "ffprobe")
    if not os.path.isfile(ffprobe_path):
        ffprobe_path = shutil.which("ffprobe")

    if ffprobe_path:
        cmd = [
            ffprobe_path, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            filepath
        ]
    else:
        # ffprobe가 없으면 ffmpeg로 대체
        cmd = [
            ffmpeg_path, "-i", filepath,
            "-f", "null", "-"
        ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if ffprobe_path:
            return float(result.stdout.strip())
        else:
            # ffmpeg stderr에서 Duration 파싱
            match = re.search(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)", result.stderr)
            if match:
                h, m, s, cs = match.groups()
                return int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100
    except Exception:
        pass
    return 0.0


def convert_mts_to_mp4(
    input_path: str,
    output_path: str,
    preset_name: str = "standard",
    ffmpeg_path: Optional[str] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> bool:
    """
    MTS 파일을 MP4로 변환합니다.

    Args:
        input_path: 입력 MTS 파일 경로
        output_path: 출력 MP4 파일 경로
        preset_name: 품질 프리셋 이름 (high/standard/compact)
        ffmpeg_path: FFmpeg 실행 파일 경로 (None이면 자동 탐색)
        progress_callback: 진행률 콜백 (0.0 ~ 100.0)
        cancel_check: 취소 여부 확인 함수 (True 반환 시 중단)

    Returns:
        성공 여부
    """
    if ffmpeg_path is None:
        ffmpeg_path = find_ffmpeg()
        if ffmpeg_path is None:
            raise FileNotFoundError(
                "FFmpeg를 찾을 수 없습니다.\n"
                "FFmpeg를 설치하거나 프로그램 폴더에 넣어주세요.\n"
                "다운로드: https://ffmpeg.org/download.html"
            )

    preset = PRESETS.get(preset_name, PRESETS["standard"])

    # 영상 길이 가져오기
    duration = get_duration(input_path, ffmpeg_path)

    # FFmpeg 명령어 구성
    cmd = [
        ffmpeg_path,
        "-y",                          # 덮어쓰기
        "-i", input_path,              # 입력
        "-c:v", "libx264",             # H.264 비디오 코덱
        "-crf", str(preset.crf),       # 품질
        "-preset", preset.preset,      # 인코딩 속도
        "-c:a", "aac",                 # AAC 오디오 코덱
        "-b:a", "192k",               # 오디오 비트레이트
        "-movflags", "+faststart",     # 웹 스트리밍 최적화
        "-progress", "pipe:1",         # 진행률 stdout 출력
        "-nostats",
        output_path
    ]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,  # stderr를 버려서 파이프 데드락 방지
        universal_newlines=True,
        creationflags=subprocess.CREATE_NO_WINDOW
    )

    try:
        current_time = 0.0
        for line in process.stdout:
            line = line.strip()

            # 취소 확인
            if cancel_check and cancel_check():
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                # 불완전한 출력 파일 삭제
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                    except OSError:
                        pass
                return False

            # 진행률 파싱 (out_time_us 또는 out_time_ms)
            if line.startswith("out_time_us="):
                try:
                    time_us = int(line.split("=")[1])
                    current_time = time_us / 1_000_000  # microseconds → seconds
                    if duration > 0 and progress_callback:
                        pct = min((current_time / duration) * 100, 99.9)
                        progress_callback(pct)
                except (ValueError, IndexError):
                    pass
            elif line.startswith("out_time_ms="):
                try:
                    time_ms = int(line.split("=")[1])
                    current_time = time_ms / 1_000_000  # FFmpeg의 out_time_ms는 실제로 microseconds
                    if duration > 0 and progress_callback:
                        pct = min((current_time / duration) * 100, 99.9)
                        progress_callback(pct)
                except (ValueError, IndexError):
                    pass
            elif line.startswith("out_time="):
                # HH:MM:SS.mmmmm 형식 파싱 (폴백)
                try:
                    time_str = line.split("=")[1]
                    parts = time_str.split(":")
                    if len(parts) == 3:
                        h, m, s = float(parts[0]), float(parts[1]), float(parts[2])
                        current_time = h * 3600 + m * 60 + s
                        if duration > 0 and progress_callback:
                            pct = min((current_time / duration) * 100, 99.9)
                            progress_callback(pct)
                except (ValueError, IndexError):
                    pass
            elif line.startswith("progress=end"):
                if progress_callback:
                    progress_callback(100.0)

        process.wait(timeout=600)

        if process.returncode == 0:
            if progress_callback:
                progress_callback(100.0)
            return True
        else:
            raise RuntimeError(f"FFmpeg 오류 (코드 {process.returncode})")

    except subprocess.TimeoutExpired:
        process.kill()
        raise RuntimeError("변환 시간이 초과되었습니다.")


def get_output_path(input_path: str, output_dir: str) -> str:
    """입력 파일 경로를 기반으로 출력 MP4 경로를 생성합니다."""
    basename = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(output_dir, f"{basename}.mp4")

    # 같은 이름이 이미 있으면 번호 추가
    counter = 1
    while os.path.exists(output_path):
        output_path = os.path.join(output_dir, f"{basename} ({counter}).mp4")
        counter += 1

    return output_path
