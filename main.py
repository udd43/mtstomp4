"""
MTS → MP4 변환기 GUI 애플리케이션
ttkbootstrap 기반의 모던한 인터페이스
"""

import os
import sys
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import List

from scan_log import (
    get_new_files, mark_as_processed, is_already_processed,
    load_processed_log, save_processed_log
)

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    HAS_TTKBOOTSTRAP = True
except ImportError:
    import tkinter.ttk as ttk
    HAS_TTKBOOTSTRAP = False

from converter import (
    find_ffmpeg, convert_mts_to_mp4, get_output_path,
    PRESETS, ConvertPreset
)


class FileItem:
    """변환 대기열의 파일 항목"""
    def __init__(self, path: str):
        self.path = path
        self.filename = os.path.basename(path)
        self.size = os.path.getsize(path)
        self.status = "대기"  # 대기 / 변환중 / 완료 / 오류 / 취소
        self.progress = 0.0
        self.error_msg = ""

    @property
    def size_str(self) -> str:
        """사람이 읽기 좋은 파일 크기"""
        size = self.size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


# 카메라 기본 경로
CAMERA_STREAM_PATH = r"J:\PRIVATE\AVCHD\BDMV\STREAM"
SCAN_INTERVAL_MS = 3000  # 3초마다 드라이브 체크


class MTSConverterApp:
    """MTS → MP4 변환기 메인 GUI"""

    def __init__(self):
        # 메인 윈도우 생성
        if HAS_TTKBOOTSTRAP:
            self.root = ttk.Window(
                title="MTS → MP4 변환기",
                themename="darkly",
                size=(900, 680),
                resizable=(True, True),
            )
        else:
            self.root = tk.Tk()
            self.root.title("MTS → MP4 변환기")
            self.root.geometry("900x680")

        self.root.minsize(700, 500)

        # 아이콘 설정 (있으면)
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
        if os.path.isfile(icon_path):
            self.root.iconbitmap(icon_path)

        # 상태 변수
        self.files: List[FileItem] = []
        self.is_converting = False
        self.cancel_requested = False
        self.output_dir = tk.StringVar(value="")
        self.preset_var = tk.StringVar(value="standard")
        self.overall_progress = tk.DoubleVar(value=0)
        self.current_progress = tk.DoubleVar(value=0)
        self.status_text = tk.StringVar(value="파일을 추가하세요")
        self.file_count_text = tk.StringVar(value="파일: 0개")

        # ETA(남은시간) 관련
        self.eta_current_text = tk.StringVar(value="")
        self.eta_overall_text = tk.StringVar(value="")
        self.convert_start_time = 0.0
        self.file_start_time = 0.0

        # 자동 스캔 관련
        self.auto_scan_active = False
        self.scan_timer_id = None
        self.auto_scan_text = tk.StringVar(value="자동 감지: 꺼짐")
        self.drive_connected = False

        # FFmpeg 확인
        self.ffmpeg_path = find_ffmpeg()

        # 기본 폰트를 맑은 고딕으로 설정
        import tkinter.font as tkfont
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family="맑은 고딕", size=10)
        text_font = tkfont.nametofont("TkTextFont")
        text_font.configure(family="맑은 고딕", size=10)

        # UI 구성
        self._build_ui()

        # FFmpeg 없으면 경고
        if not self.ffmpeg_path:
            self.root.after(500, self._warn_no_ffmpeg)

    def _warn_no_ffmpeg(self):
        messagebox.showwarning(
            "FFmpeg 없음",
            "FFmpeg를 찾을 수 없습니다.\n\n"
            "변환을 위해 FFmpeg를 설치해주세요:\n"
            "https://ffmpeg.org/download.html\n\n"
            "설치 후 시스템 PATH에 추가하거나,\n"
            "이 프로그램 폴더에 ffmpeg.exe를 넣어주세요."
        )

    def _build_ui(self):
        """UI 위젯 구성"""
        # ─── 상단: 헤더 ─────────────────────────────
        header_frame = ttk.Frame(self.root, padding=(20, 15, 20, 10))
        header_frame.pack(fill=tk.X)

        title_label = ttk.Label(
            header_frame,
            text="🎬 MTS → MP4 변환기",
            font=("맑은 고딕", 20, "bold"),
        )
        title_label.pack(side=tk.LEFT)

        subtitle = ttk.Label(
            header_frame,
            text="AVCHD 동영상을 MP4로 간편하게 변환",
            font=("맑은 고딕", 10),
        )
        subtitle.pack(side=tk.LEFT, padx=(15, 0), pady=(8, 0))

        # ─── 파일 추가 영역 ─────────────────────────
        add_frame = ttk.Frame(self.root, padding=(20, 5, 20, 5))
        add_frame.pack(fill=tk.X)

        if HAS_TTKBOOTSTRAP:
            btn_add_files = ttk.Button(
                add_frame, text="📂 파일 추가",
                command=self._add_files, bootstyle="info-outline",
                width=14
            )
            btn_add_folder = ttk.Button(
                add_frame, text="📁 폴더 추가",
                command=self._add_folder, bootstyle="info-outline",
                width=14
            )
            self.btn_auto_scan = ttk.Button(
                add_frame, text="📹 자동 감지",
                command=self._toggle_auto_scan, bootstyle="warning-outline",
                width=14
            )
            btn_clear = ttk.Button(
                add_frame, text="🗑 전체 삭제",
                command=self._clear_files, bootstyle="danger-outline",
                width=14
            )
        else:
            btn_add_files = ttk.Button(
                add_frame, text="파일 추가",
                command=self._add_files, width=14
            )
            btn_add_folder = ttk.Button(
                add_frame, text="폴더 추가",
                command=self._add_folder, width=14
            )
            self.btn_auto_scan = ttk.Button(
                add_frame, text="자동 감지",
                command=self._toggle_auto_scan, width=14
            )
            btn_clear = ttk.Button(
                add_frame, text="전체 삭제",
                command=self._clear_files, width=14
            )

        btn_add_files.pack(side=tk.LEFT, padx=(0, 8))
        btn_add_folder.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_auto_scan.pack(side=tk.LEFT, padx=(0, 8))
        btn_clear.pack(side=tk.LEFT, padx=(0, 8))

        # 파일 카운트
        count_label = ttk.Label(
            add_frame, textvariable=self.file_count_text,
            font=("맑은 고딕", 10)
        )
        count_label.pack(side=tk.RIGHT)

        # 자동 감지 상태
        self.auto_scan_label = ttk.Label(
            add_frame, textvariable=self.auto_scan_text,
            font=("맑은 고딕", 9),
        )
        self.auto_scan_label.pack(side=tk.RIGHT, padx=(0, 15))

        # ─── 파일 리스트 (Treeview) ──────────────────
        list_frame = ttk.Frame(self.root, padding=(20, 5, 20, 5))
        list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("filename", "size", "status", "progress")
        self.tree = ttk.Treeview(
            list_frame, columns=columns, show="headings",
            selectmode="extended", height=12
        )
        self.tree.heading("filename", text="파일명", anchor=tk.W)
        self.tree.heading("size", text="크기", anchor=tk.CENTER)
        self.tree.heading("status", text="상태", anchor=tk.CENTER)
        self.tree.heading("progress", text="진행률", anchor=tk.CENTER)

        self.tree.column("filename", width=380, minwidth=200, anchor=tk.W)
        self.tree.column("size", width=100, minwidth=80, anchor=tk.CENTER)
        self.tree.column("status", width=100, minwidth=80, anchor=tk.CENTER)
        self.tree.column("progress", width=100, minwidth=80, anchor=tk.CENTER)

        # 스크롤바
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 선택된 파일 삭제 바인딩
        self.tree.bind("<Delete>", lambda e: self._remove_selected())

        # ─── 설정 영역 ──────────────────────────────
        settings_frame = ttk.LabelFrame(
            self.root, text=" ⚙ 설정 ",
        )
        settings_frame.pack(fill=tk.X, padx=20, pady=(5, 5))

        # 내부 패딩을 위한 inner frame
        settings_inner = ttk.Frame(settings_frame, padding=(15, 10, 15, 10))

        # 출력 폴더
        out_row = ttk.Frame(settings_inner)
        out_row.pack(fill=tk.X, pady=(0, 8))
        settings_inner.pack(fill=tk.X)

        ttk.Label(out_row, text="출력 폴더:", width=10).pack(side=tk.LEFT)
        out_entry = ttk.Entry(out_row, textvariable=self.output_dir)
        out_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 8))

        if HAS_TTKBOOTSTRAP:
            btn_browse = ttk.Button(
                out_row, text="찾아보기",
                command=self._browse_output, bootstyle="secondary",
                width=10
            )
        else:
            btn_browse = ttk.Button(
                out_row, text="찾아보기",
                command=self._browse_output, width=10
            )
        btn_browse.pack(side=tk.RIGHT)

        # 품질 프리셋
        preset_row = ttk.Frame(settings_inner)
        preset_row.pack(fill=tk.X)

        ttk.Label(preset_row, text="화질:", width=10).pack(side=tk.LEFT)

        for key, preset in PRESETS.items():
            if HAS_TTKBOOTSTRAP:
                rb = ttk.Radiobutton(
                    preset_row, text=f"{preset.label}",
                    variable=self.preset_var, value=key,
                    bootstyle="info"
                )
            else:
                rb = ttk.Radiobutton(
                    preset_row, text=f"{preset.label}",
                    variable=self.preset_var, value=key,
                )
            rb.pack(side=tk.LEFT, padx=(5, 20))

        # 프리셋 설명
        preset_desc = ttk.Label(
            preset_row, text="",
            font=("맑은 고딕", 9),
        )
        preset_desc.pack(side=tk.RIGHT)

        def update_desc(*_):
            p = PRESETS.get(self.preset_var.get())
            if p:
                preset_desc.config(text=f"({p.description})")

        self.preset_var.trace_add("write", update_desc)
        update_desc()

        # ─── 진행률 영역 ────────────────────────────
        progress_frame = ttk.Frame(self.root, padding=(20, 5, 20, 5))
        progress_frame.pack(fill=tk.X)

        # 현재 파일 진행률
        cur_label = ttk.Label(progress_frame, text="현재 파일:")
        cur_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 8))

        if HAS_TTKBOOTSTRAP:
            self.current_bar = ttk.Progressbar(
                progress_frame, variable=self.current_progress,
                maximum=100, bootstyle="info-striped",
            )
        else:
            self.current_bar = ttk.Progressbar(
                progress_frame, variable=self.current_progress,
                maximum=100,
            )
        self.current_bar.grid(row=0, column=1, sticky=tk.EW, pady=2)

        # 현재 파일 남은시간
        self.cur_eta_label = ttk.Label(
            progress_frame, textvariable=self.eta_current_text,
            font=("맑은 고딕", 9), width=18, anchor=tk.E
        )
        self.cur_eta_label.grid(row=0, column=2, sticky=tk.E, padx=(8, 0))

        # 전체 진행률
        all_label = ttk.Label(progress_frame, text="전체:")
        all_label.grid(row=1, column=0, sticky=tk.W, padx=(0, 8))

        if HAS_TTKBOOTSTRAP:
            self.overall_bar = ttk.Progressbar(
                progress_frame, variable=self.overall_progress,
                maximum=100, bootstyle="success-striped",
            )
        else:
            self.overall_bar = ttk.Progressbar(
                progress_frame, variable=self.overall_progress,
                maximum=100,
            )
        self.overall_bar.grid(row=1, column=1, sticky=tk.EW, pady=2)

        # 전체 남은시간
        self.all_eta_label = ttk.Label(
            progress_frame, textvariable=self.eta_overall_text,
            font=("맑은 고딕", 9), width=18, anchor=tk.E
        )
        self.all_eta_label.grid(row=1, column=2, sticky=tk.E, padx=(8, 0))

        progress_frame.columnconfigure(1, weight=1)

        # ─── 하단: 버튼 & 상태 ──────────────────────
        bottom_frame = ttk.Frame(self.root, padding=(20, 10, 20, 15))
        bottom_frame.pack(fill=tk.X)

        status_label = ttk.Label(
            bottom_frame, textvariable=self.status_text,
            font=("Segoe UI", 10)
        )
        status_label.pack(side=tk.LEFT)

        if HAS_TTKBOOTSTRAP:
            self.btn_convert = ttk.Button(
                bottom_frame, text="▶  변환 시작",
                command=self._start_conversion,
                bootstyle="success",
                width=16,
            )
            self.btn_cancel = ttk.Button(
                bottom_frame, text="■  중지",
                command=self._cancel_conversion,
                bootstyle="danger",
                width=12,
                state=tk.DISABLED,
            )
        else:
            self.btn_convert = ttk.Button(
                bottom_frame, text="변환 시작",
                command=self._start_conversion,
                width=16,
            )
            self.btn_cancel = ttk.Button(
                bottom_frame, text="중지",
                command=self._cancel_conversion,
                width=12,
                state=tk.DISABLED,
            )

        self.btn_cancel.pack(side=tk.RIGHT, padx=(8, 0))
        self.btn_convert.pack(side=tk.RIGHT)

    # ──────────────────────────────────────────────
    #   파일 관리
    # ──────────────────────────────────────────────

    def _add_files(self):
        """파일 선택 대화상자"""
        if self.is_converting:
            return
        paths = filedialog.askopenfilenames(
            title="MTS 파일 선택",
            filetypes=[
                ("MTS 파일", "*.mts;*.MTS;*.m2ts;*.M2TS"),
                ("모든 파일", "*.*"),
            ]
        )
        self._insert_files(paths)

    def _add_folder(self):
        """폴더의 모든 MTS 파일 추가"""
        if self.is_converting:
            return
        folder = filedialog.askdirectory(title="MTS 파일이 있는 폴더 선택")
        if not folder:
            return
        paths = []
        for root, dirs, files in os.walk(folder):
            for f in files:
                if f.lower().endswith((".mts", ".m2ts")):
                    paths.append(os.path.join(root, f))
        if not paths:
            messagebox.showinfo("알림", "선택한 폴더에 MTS 파일이 없습니다.")
            return
        self._insert_files(paths)

        # 출력 폴더가 비어 있으면 소스 폴더로 설정
        if not self.output_dir.get():
            self.output_dir.set(folder)

    def _insert_files(self, paths):
        """파일 목록에 추가"""
        existing = {f.path for f in self.files}
        for p in paths:
            if p not in existing:
                item = FileItem(p)
                self.files.append(item)
                self.tree.insert("", tk.END, iid=p, values=(
                    item.filename, item.size_str, item.status, "0%"
                ))
        self._update_count()

        # 첫 파일 추가 시 출력 폴더 자동 설정
        if self.files and not self.output_dir.get():
            self.output_dir.set(os.path.dirname(self.files[0].path))

    def _remove_selected(self):
        """선택된 파일 제거"""
        if self.is_converting:
            return
        selected = self.tree.selection()
        for iid in selected:
            self.tree.delete(iid)
            self.files = [f for f in self.files if f.path != iid]
        self._update_count()

    def _clear_files(self):
        """전체 파일 목록 초기화"""
        if self.is_converting:
            return
        self.tree.delete(*self.tree.get_children())
        self.files.clear()
        self._update_count()
        self.overall_progress.set(0)
        self.current_progress.set(0)
        self.status_text.set("파일을 추가하세요")

    def _update_count(self):
        self.file_count_text.set(f"파일: {len(self.files)}개")

    def _browse_output(self):
        """출력 폴더 선택"""
        folder = filedialog.askdirectory(title="출력 폴더 선택")
        if folder:
            self.output_dir.set(folder)

    # ──────────────────────────────────────────────
    #   변환
    # ──────────────────────────────────────────────

    def _start_conversion(self):
        """변환 시작"""
        if self.is_converting:
            return

        # 유효성 검사
        pending = [f for f in self.files if f.status in ("대기", "오류")]
        if not pending:
            messagebox.showinfo("알림", "변환할 파일이 없습니다.")
            return

        output_dir = self.output_dir.get().strip()
        if not output_dir:
            messagebox.showwarning("경고", "출력 폴더를 선택하세요.")
            return

        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as e:
                messagebox.showerror("오류", f"출력 폴더 생성 실패:\n{e}")
                return

        # FFmpeg 다시 확인
        self.ffmpeg_path = find_ffmpeg()
        if not self.ffmpeg_path:
            self._warn_no_ffmpeg()
            return

        # UI 상태 변경
        self.is_converting = True
        self.cancel_requested = False
        self.btn_convert.config(state=tk.DISABLED)
        self.btn_cancel.config(state=tk.NORMAL)

        # ETA 타이머 초기화
        self.convert_start_time = time.time()
        self.eta_current_text.set("")
        self.eta_overall_text.set("")

        # 별도 스레드에서 변환
        thread = threading.Thread(
            target=self._convert_worker,
            args=(pending, output_dir),
            daemon=True
        )
        thread.start()

    def _convert_worker(self, files: List[FileItem], output_dir: str):
        """백그라운드 변환 작업 (스레드)"""
        total = len(files)
        preset = self.preset_var.get()

        for idx, file_item in enumerate(files):
            if self.cancel_requested:
                file_item.status = "취소"
                self._update_tree_item(file_item)
                continue

            file_item.status = "변환중"
            file_item.progress = 0
            self._update_tree_item(file_item)
            self._set_status(f"변환중: {file_item.filename} ({idx + 1}/{total})")

            # 현재 파일 시작 시간 기록
            self.file_start_time = time.time()

            output_path = get_output_path(file_item.path, output_dir)

            def on_progress(pct, fi=file_item, _idx=idx, _total=total):
                fi.progress = pct
                self.root.after(0, lambda: self.current_progress.set(pct))
                self.root.after(0, lambda: self._update_tree_item(fi))
                # 전체 진행률 계산
                overall = ((_idx + pct / 100) / _total) * 100
                self.root.after(0, lambda: self.overall_progress.set(overall))

                # ETA 계산 및 표시
                self._update_eta(pct, _idx, _total)

            try:
                success = convert_mts_to_mp4(
                    input_path=file_item.path,
                    output_path=output_path,
                    preset_name=preset,
                    ffmpeg_path=self.ffmpeg_path,
                    progress_callback=on_progress,
                    cancel_check=lambda: self.cancel_requested,
                )
                if success:
                    file_item.status = "✅ 완료"
                    file_item.progress = 100
                    # 처리 완료 로그 기록
                    mark_as_processed(file_item.path)
                else:
                    file_item.status = "취소"
            except Exception as e:
                file_item.status = "❌ 오류"
                file_item.error_msg = str(e)
                self.root.after(0, lambda msg=str(e): messagebox.showerror(
                    "변환 오류", f"{file_item.filename}\n\n{msg}"
                ))

            self._update_tree_item(file_item)

        # 완료
        self.root.after(0, self._conversion_finished)

    def _conversion_finished(self):
        """변환 완료 후 UI 복원"""
        self.is_converting = False
        self.btn_convert.config(state=tk.NORMAL)
        self.btn_cancel.config(state=tk.DISABLED)

        # ETA 표시 초기화 - 소요시간 표시
        total_elapsed = time.time() - self.convert_start_time
        elapsed_str = self._format_eta(0).replace(" 남음", "")  # 빈 문자열
        if total_elapsed < 60:
            elapsed_str = f"총 {int(total_elapsed)}초 소요"
        elif total_elapsed < 3600:
            m, s = divmod(int(total_elapsed), 60)
            elapsed_str = f"총 {m}분 {s}초 소요"
        else:
            h, remainder = divmod(int(total_elapsed), 3600)
            m, _ = divmod(remainder, 60)
            elapsed_str = f"총 {h}시간 {m}분 소요"
        self.eta_current_text.set("")
        self.eta_overall_text.set(elapsed_str)

        done = sum(1 for f in self.files if "완료" in f.status)
        errors = sum(1 for f in self.files if "오류" in f.status)
        cancelled = sum(1 for f in self.files if f.status == "취소")

        parts = []
        if done:
            parts.append(f"완료 {done}개")
        if errors:
            parts.append(f"오류 {errors}개")
        if cancelled:
            parts.append(f"취소 {cancelled}개")

        self.status_text.set(f"변환 완료! ({', '.join(parts)})")
        self.overall_progress.set(100 if not errors and not cancelled else self.overall_progress.get())

        if done > 0 and errors == 0 and cancelled == 0:
            messagebox.showinfo(
                "완료",
                f"모든 파일이 성공적으로 변환되었습니다!\n총 {done}개 파일"
            )

    def _cancel_conversion(self):
        """변환 중지 요청"""
        if self.is_converting:
            self.cancel_requested = True
            self.status_text.set("중지 요청됨... 현재 작업 완료 후 중지됩니다")
            self.btn_cancel.config(state=tk.DISABLED)

    def _update_tree_item(self, file_item: FileItem):
        """Treeview 항목 업데이트 (메인 스레드에서)"""
        def update():
            try:
                self.tree.item(file_item.path, values=(
                    file_item.filename,
                    file_item.size_str,
                    file_item.status,
                    f"{file_item.progress:.0f}%"
                ))
            except tk.TclError:
                pass
        self.root.after(0, update)

    def _set_status(self, text: str):
        """상태 텍스트 업데이트"""
        self.root.after(0, lambda: self.status_text.set(text))

    @staticmethod
    def _format_eta(seconds: float) -> str:
        """초를 사람이 읽기 좋은 시간 문자열로 변환"""
        if seconds < 0 or seconds > 86400:  # 24시간 이상이면 표시 안함
            return ""
        seconds = int(seconds)
        if seconds < 60:
            return f"{seconds}초 남음"
        elif seconds < 3600:
            m, s = divmod(seconds, 60)
            return f"{m}분 {s}초 남음"
        else:
            h, remainder = divmod(seconds, 3600)
            m, s = divmod(remainder, 60)
            return f"{h}시간 {m}분 남음"

    def _update_eta(self, current_pct: float, file_idx: int, total_files: int):
        """현재 파일 ETA 및 전체 ETA를 계산하여 UI 갱신"""
        now = time.time()

        # ── 현재 파일 남은시간 ──
        if current_pct > 1.0:
            file_elapsed = now - self.file_start_time
            file_remaining = file_elapsed * (100.0 - current_pct) / current_pct
            cur_eta_str = self._format_eta(file_remaining)
        else:
            cur_eta_str = "계산중..."

        # ── 전체 남은시간 ──
        overall_pct = ((file_idx + current_pct / 100) / total_files) * 100
        if overall_pct > 0.5:
            total_elapsed = now - self.convert_start_time
            total_remaining = total_elapsed * (100.0 - overall_pct) / overall_pct
            all_eta_str = self._format_eta(total_remaining)
        else:
            all_eta_str = "계산중..."

        self.root.after(0, lambda: self.eta_current_text.set(cur_eta_str))
        self.root.after(0, lambda: self.eta_overall_text.set(all_eta_str))

    # ──────────────────────────────────────────────
    #   자동 스캔 (J: 드라이브 감지)
    # ──────────────────────────────────────────────

    def _toggle_auto_scan(self):
        """자동 스캔 켜기/끄기 토글"""
        if self.auto_scan_active:
            self._stop_auto_scan()
        else:
            self._start_auto_scan()

    def _start_auto_scan(self):
        """자동 스캔 시작"""
        self.auto_scan_active = True
        self.auto_scan_text.set("자동 감지: 대기중...")

        if HAS_TTKBOOTSTRAP:
            self.btn_auto_scan.config(text="📹 감지 중지", bootstyle="danger")
        else:
            self.btn_auto_scan.config(text="감지 중지")

        self.status_text.set("카메라 연결 대기중... (J: 드라이브)")
        self._scan_drive()

    def _stop_auto_scan(self):
        """자동 스캔 중지"""
        self.auto_scan_active = False
        self.drive_connected = False

        if self.scan_timer_id:
            self.root.after_cancel(self.scan_timer_id)
            self.scan_timer_id = None

        self.auto_scan_text.set("자동 감지: 꺼짐")

        if HAS_TTKBOOTSTRAP:
            self.btn_auto_scan.config(text="📹 자동 감지", bootstyle="warning-outline")
        else:
            self.btn_auto_scan.config(text="자동 감지")

        self.status_text.set("자동 감지가 중지되었습니다")

    def _scan_drive(self):
        """J: 드라이브 및 새 파일을 주기적으로 확인"""
        if not self.auto_scan_active:
            return

        stream_path = CAMERA_STREAM_PATH

        if os.path.isdir(stream_path):
            # 드라이브 연결됨
            if not self.drive_connected:
                self.drive_connected = True
                self.auto_scan_text.set("자동 감지: 연결됨 ✅")
                self.status_text.set("카메라 감지됨! 새 파일 검색중...")

            # 새 파일 검색
            new_files = get_new_files(stream_path)
            if new_files:
                added_count = self._auto_insert_files(new_files)
                if added_count > 0:
                    self.status_text.set(
                        f"새 파일 {added_count}개 발견! 목록에 추가되었습니다."
                    )
            else:
                if not self.is_converting:
                    self.status_text.set("새 파일 없음. 계속 감시중...")
        else:
            # 드라이브 연결 안됨
            if self.drive_connected:
                self.drive_connected = False
                self.auto_scan_text.set("자동 감지: 대기중...")
                self.status_text.set("카메라 연결이 해제되었습니다. 재연결 대기중...")
            else:
                self.auto_scan_text.set("자동 감지: 대기중...")

        # 다음 스캔 예약
        self.scan_timer_id = self.root.after(SCAN_INTERVAL_MS, self._scan_drive)

    def _auto_insert_files(self, paths: list) -> int:
        """
        자동 감지된 파일을 목록에 추가합니다.
        이미 목록에 있거나 처리 로그에 있는 파일은 제외합니다.

        Returns:
            새로 추가된 파일 수
        """
        existing_paths = {f.path for f in self.files}
        added = 0

        for p in paths:
            # 이미 현재 목록에 있으면 스킵
            if p in existing_paths:
                continue
            # 이미 처리된 파일이면 스킵
            if is_already_processed(p):
                continue

            item = FileItem(p)
            self.files.append(item)
            self.tree.insert("", tk.END, iid=p, values=(
                item.filename, item.size_str, item.status, "0%"
            ))
            added += 1

        if added > 0:
            self._update_count()

            # 출력 폴더가 비어 있으면 자동 설정
            if not self.output_dir.get():
                self.output_dir.set(os.path.dirname(paths[0]))

        return added

    def run(self):
        """앱 실행"""
        self.root.mainloop()


def main():
    app = MTSConverterApp()
    app.run()


if __name__ == "__main__":
    main()
