"""mpv 影片桌布：掛到 WorkerW + 滑鼠穿透 + 禁止操作"""
from __future__ import annotations

import ctypes
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

from utils.mpv_helper import get_mpv_path

try:
    import win32gui
    import win32con
    import win32api
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

_cached_workerw: int | None = None


# 全模組只找一次 WorkerW，避免每次播影片都送 0x052C 弄到工作列
_cached_workerw: int | None = None


def _find_workerw() -> int:
    """取得桌面 WorkerW；成功後快取，之後直接重用"""
    global _cached_workerw

    if not HAS_WIN32:
        return 0

    # 已有快取且視窗還在
    if _cached_workerw:
        try:
            if win32gui.IsWindow(_cached_workerw):
                return _cached_workerw
        except Exception:
            pass
        _cached_workerw = None

    progman = win32gui.FindWindow("Progman", None)
    if not progman:
        return 0

    # 觸發系統建立用來放桌布的 WorkerW（只在第一次找時送）
    result = ctypes.c_ulong()
    ctypes.windll.user32.SendMessageTimeoutW(
        progman, 0x052C, 0, 0, 0, 1000, ctypes.byref(result)
    )

    workerw = 0

    def enum_handler(hwnd, _):
        nonlocal workerw
        if win32gui.FindWindowEx(hwnd, 0, "SHELLDLL_DefView", None):
            workerw = win32gui.FindWindowEx(0, hwnd, "WorkerW", None)
        return True

    win32gui.EnumWindows(enum_handler, None)

    _cached_workerw = workerw or 0
    return _cached_workerw


def _make_click_through(hwnd: int):
    """滑鼠穿透，不擋桌面圖示與其他視窗操作"""
    if not hwnd:
        return
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    style |= win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_NOACTIVATE
    style &= ~win32con.WS_EX_APPWINDOW
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
    # 不搶啟用
    try:
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_BOTTOM,
            0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE,
        )
    except Exception:
        pass


class VideoWallpaper:
    def __init__(self, screen_key: str = ""):
        self.screen_key = screen_key
        self._proc: Optional[subprocess.Popen] = None
        self._current_path: Optional[str] = None
        self._host_hwnd: int = 0
        self._ass_path: Optional[str] = None

    def is_playing(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def stop(self):
        if self._proc is not None:
            try:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
            except Exception:
                pass
            self._proc = None
        self._current_path = None

        if self._host_hwnd and HAS_WIN32:
            try:
                win32gui.DestroyWindow(self._host_hwnd)
            except Exception:
                pass
            self._host_hwnd = 0

        if self._ass_path:
            try:
                Path(self._ass_path).unlink(missing_ok=True)
            except Exception:
                pass
            self._ass_path = None

    def _create_host_window(self, x: int, y: int, w: int, h: int) -> int:
        """在 WorkerW 下建一個全螢幕宿主，給 mpv --wid 使用"""
        if not HAS_WIN32:
            return 0
        worker = _find_workerw()
        parent = worker if worker else 0

        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = win32gui.DefWindowProc
        wc.lpszClassName = "UWSVideoHost"
        wc.hInstance = win32api.GetModuleHandle(None)
        try:
            win32gui.RegisterClass(wc)
        except Exception:
            pass  # 可能已註冊

        style = win32con.WS_POPUP | win32con.WS_VISIBLE | win32con.WS_CHILD
        if not parent:
            style = win32con.WS_POPUP | win32con.WS_VISIBLE

        hwnd = win32gui.CreateWindowEx(
            win32con.WS_EX_NOACTIVATE | win32con.WS_EX_TOOLWINDOW,
            "UWSVideoHost",
            "",
            style,
            x, y, w, h,
            parent,
            0,
            wc.hInstance,
            None,
        )
        if hwnd:
            _make_click_through(hwnd)
            win32gui.SetWindowPos(
                hwnd, win32con.HWND_BOTTOM, x, y, w, h,
                win32con.SWP_SHOWWINDOW | win32con.SWP_NOACTIVATE,
            )
        return hwnd

    def _make_ass_label(self, folder_name: str, file_name: str) -> Optional[str]:
        import os
        import tempfile

        text = f"{folder_name}-{file_name}" if folder_name else file_name
        for ch in ("{", "}", "\\"):
            text = text.replace(ch, " ")

        # PlayRes 用較大畫布；Alignment=9 右上
        # BorderStyle=3 + BackColour 白 = 不透明白底；Primary 黑字
        # ASS 顏色：&HAABBGGRR
        content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Label,Microsoft YaHei,20,&H00000000,&H00000000,&H00FFFFFF,&H00FFFFFF,-1,0,0,0,100,100,0,0,3,6,0,9,20,20,16,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,9:59:59.00,Label,,0,0,0,,{{\\fs14}}{text}
"""
        try:
            fd, ass_path = tempfile.mkstemp(suffix=".ass", prefix="uws_osd_")
            os.close(fd)
            Path(ass_path).write_text(content, encoding="utf-8-sig")
            self._ass_path = ass_path
            return ass_path
        except Exception as e:
            print(f"建立 ASS 失敗: {e}")
            return None

    def play(
        self,
        video_path: str,
        screen_index: int = 0,
        loop: bool = True,
        geometry: Optional[Tuple[int, int, int, int]] = None,
        show_label: bool = True,
    ) -> bool:
        exe = get_mpv_path()
        if not exe:
            print("找不到 mpv.exe")
            return False

        path = str(Path(video_path).resolve())
        if not Path(path).is_file():
            print(f"影片不存在: {path}")
            return False

        if self.is_playing() and self._current_path == path:
            return True

        self.stop()

        # 幾何：未傳入時用虛擬桌面估計（MainWindow 可傳 screen.geometry）
        if geometry:
            x, y, w, h = geometry
        else:
            x, y, w, h = 0, 0, 1920, 1080

        host = self._create_host_window(x, y, w, h)
        self._host_hwnd = host

        cmd = [
            str(exe),
            "--no-border",
            "--no-osc",
            "--no-osd-bar",
            "--really-quiet",
            "--hwdec=auto",
            "--vo=gpu",
            "--keepaspect=yes",
            "--panscan=0.0",
            "--cursor-autohide=always",
            "--input-default-bindings=no",
            "--input-vo-keyboard=no",
            "--no-input-builtin-bindings",
            "--stop-screensaver=no",
            "--mute=yes",
        ]

        if host:
            # 嵌進宿主視窗 = 桌布層、不可當一般播放器操作
            cmd.append(f"--wid={host}")
        else:
            cmd += [
                f"--screen={screen_index}",
                "--fs",
                f"--fs-screen={screen_index}",
            ]

        if loop:
            cmd.append("--loop-file=inf")
        else:
            cmd.append("--loop-file=no")

        if show_label:
            p = Path(path)
            ass = self._make_ass_label(p.parent.name, p.name)
            if ass:
                cmd += [
                    f"--sub-file={ass}",
                    "--sid=1",
                    "--sub-visibility=yes",
                    # 關鍵：讓字幕畫在黑邊／整窗，而不是只在影片矩形內
                    "--sub-use-margins=yes",
                    "--sub-ass-force-margins=yes",
                    "--sub-ass-override=force",
                    "--sub-align-x=right",
                    "--sub-align-y=top",
                    "--sub-margin-x=16",
                    "--sub-margin-y=12",
                    "--sub-scale=1.00",
                ]

        cmd.append(path)

        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._current_path = path
        except Exception as e:
            print(f"啟動 mpv 失敗: {e}")
            self.stop()
            return False

        # 再設一次穿透（有些環境 --wid 後會變）
        if host:
            time.sleep(0.3)
            _make_click_through(host)

        return True
