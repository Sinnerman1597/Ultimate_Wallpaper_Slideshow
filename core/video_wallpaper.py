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
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

user_WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p
)


def _find_workerw() -> int:
    if not HAS_WIN32:
        return 0
    progman = win32gui.FindWindow("Progman", None)
    if not progman:
        return 0
    # 送 0x052C 產生用來放桌布的 WorkerW
    result = ctypes.c_ulong()
    ctypes.windll.user32.SendMessageTimeoutW(
        progman, 0x052C, 0, 0, 0, 1000, ctypes.byref(result)
    )

    workerw = 0

    def enum_handler(hwnd, _):
        nonlocal workerw
        if win32gui.FindWindowEx(hwnd, 0, "SHELLDLL_DefView", None):
            # 下一個 WorkerW 才是桌布層
            workerw = win32gui.FindWindowEx(0, hwnd, "WorkerW", None)
        return True

    win32gui.EnumWindows(enum_handler, None)
    return workerw or 0


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
    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self._current_path: Optional[str] = None
        self._host_hwnd: int = 0

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

    def play(
        self,
        video_path: str,
        screen_index: int = 0,
        loop: bool = True,
        geometry: Optional[Tuple[int, int, int, int]] = None,
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
