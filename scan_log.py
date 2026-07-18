"""
MTS 파일 처리 로그 관리 모듈
이미 변환한 파일을 다시 불러오지 않도록 JSON 로그로 관리합니다.
"""

import json
import os
from datetime import datetime
from typing import Set


# 로그 파일 경로 (실행파일 옆에 생성)
LOG_FILENAME = "processed_files.json"


def _get_log_path() -> str:
    """로그 파일의 절대 경로를 반환합니다."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, LOG_FILENAME)


def _file_key(filepath: str) -> str:
    """
    파일의 고유 키를 생성합니다.
    파일명 + 파일 크기 + 수정 시간을 조합하여 동일 파일 여부를 판별합니다.
    """
    try:
        stat = os.stat(filepath)
        basename = os.path.basename(filepath)
        return f"{basename}|{stat.st_size}|{stat.st_mtime}"
    except OSError:
        return os.path.basename(filepath)


def load_processed_log() -> dict:
    """처리된 파일 로그를 불러옵니다."""
    log_path = _get_log_path()
    if os.path.isfile(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {"processed": []}
    return {"processed": []}


def save_processed_log(log_data: dict):
    """처리된 파일 로그를 저장합니다."""
    log_path = _get_log_path()
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def get_processed_keys() -> Set[str]:
    """이미 처리된 파일들의 키 집합을 반환합니다."""
    log_data = load_processed_log()
    return {entry["key"] for entry in log_data.get("processed", []) if "key" in entry}


def mark_as_processed(filepath: str):
    """파일을 처리 완료로 기록합니다."""
    log_data = load_processed_log()
    key = _file_key(filepath)

    # 이미 기록되어 있으면 스킵
    existing_keys = {entry["key"] for entry in log_data.get("processed", []) if "key" in entry}
    if key in existing_keys:
        return

    log_data.setdefault("processed", []).append({
        "key": key,
        "filename": os.path.basename(filepath),
        "path": filepath,
        "processed_at": datetime.now().isoformat(),
    })
    save_processed_log(log_data)


def is_already_processed(filepath: str) -> bool:
    """해당 파일이 이미 처리되었는지 확인합니다."""
    key = _file_key(filepath)
    return key in get_processed_keys()


def get_new_files(directory: str, extensions: tuple = (".mts", ".m2ts")) -> list:
    """
    지정된 디렉토리에서 아직 처리되지 않은 새 파일 목록을 반환합니다.

    Args:
        directory: 검색할 디렉토리 경로
        extensions: 검색할 파일 확장자 튜플

    Returns:
        처리되지 않은 파일 경로 리스트
    """
    if not os.path.isdir(directory):
        return []

    processed_keys = get_processed_keys()
    new_files = []

    for filename in os.listdir(directory):
        if filename.lower().endswith(extensions):
            filepath = os.path.join(directory, filename)
            key = _file_key(filepath)
            if key not in processed_keys:
                new_files.append(filepath)

    # 파일명 순으로 정렬
    new_files.sort()
    return new_files
