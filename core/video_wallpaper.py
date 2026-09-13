"""mpv 影片桌布：置底 + 滑鼠穿透（不使用 WorkerW，避免工作列異常）"""
from __future__ import annotations

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


def _make_click_through(hwnd: int):
    if not hwnd or not HAS_WIN32:
        return
    try:
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        style |= (
            win32con.WS_EX_LAYERED
            | win32con.WS_EX_TRANSPARENT
            | win32con.WS_EX_NOACTIVATE
            | win32con.WS_EX_TOOLWINDOW
        )
        style &= ~win32con.WS_EX_APPWINDOW
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
    except Exception:
        pass


def _make_click_through_tree(hwnd: int):
    """host 與底下所有子視窗都穿透（mpv 繪製層常在子視窗）"""
    if not hwnd or not HAS_WIN32:
        return
    _make_click_through(hwnd)
    try:
        child = win32gui.GetWindow(hwnd, win32con.GW_CHILD)
        while child:
            _make_click_through_tree(child)
            child = win32gui.GetWindow(child, win32con.GW_HWNDNEXT)
    except Exception:
        pass


def _pin_bottom(hwnd: int, x: int, y: int, w: int, h: int):
    if not hwnd or not HAS_WIN32:
        return
    try:
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_BOTTOM,
            x, y, w, h,
            win32con.SWP_SHOWWINDOW | win32con.SWP_NOACTIVATE,
        )
    except Exception:
        pass


class VideoWallpaper:
    def __init__(self, screen_key: str = ""):
        self.screen_key = screen_key
        self._proc: Optional[subprocess.Popen] = None
        self._current_path: Optional[str] = None
        self._host_hwnd: int = 0
        self._geo: Tuple[int, int, int, int] = (0, 0, 1920, 1080)

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
        if not HAS_WIN32:
            return 0

        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = win32gui.DefWindowProc
        wc.lpszClassName = f"UWSVideoHost_{self.screen_key or 'x'}"
        wc.hInstance = win32api.GetModuleHandle(None)
        try:
            win32gui.RegisterClass(wc)
        except Exception:
            pass

        hwnd = win32gui.CreateWindowEx(
            win32con.WS_EX_NOACTIVATE
            | win32con.WS_EX_TOOLWINDOW
            | win32con.WS_EX_LAYERED
            | win32con.WS_EX_TRANSPARENT,
            wc.lpszClassName,
            "",
            win32con.WS_POPUP | win32con.WS_VISIBLE,
            x, y, w, h,
            0,
            0,
            wc.hInstance,
            None,
        )
        if hwnd:
            _make_click_through(hwnd)
            _pin_bottom(hwnd, x, y, w, h)
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

        if geometry:
            x, y, w, h = geometry
        else:
            x, y, w, h = 0, 0, 1920, 1080
        self._geo = (x, y, w, h)

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

        # mpv 建立子視窗需要一點時間，再設穿透與置底
        if host:
            for delay in (0.2, 0.5, 1.0):
                time.sleep(delay)
                _make_click_through_tree(host)
                _pin_bottom(host, x, y, w, h)

        return True
