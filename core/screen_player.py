from pathlib import Path
from typing import List, Optional
from PySide6.QtCore import QObject, QTimer, Signal
from core.playlist import Playlist

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif'}
VIDEO_EXTS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.webm'}


class ScreenPlayer(QObject):
    """單一螢幕的獨立播放器"""
    wallpaper_changed = Signal(str)  # 發出目前桌布路徑（給外部參考）

    def __init__(self, screen_key: str, screen_mode_text: str, engine, parent=None):
        super().__init__(parent)
        self.screen_key = screen_key          # "all" / "1" / "2" ...
        self.screen_mode_text = screen_mode_text  # "所有螢幕同步" / "螢幕1" ...
        self.engine = engine

        self.playlist = Playlist()
        # [{"path": str, "recursive": bool}, ...]
        self.sources: List[dict] = []
        self.interval_text = "10秒"
        self.mode_text = "順序"
        self.is_paused = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next)

    def set_sources(self, sources: List[dict]):
        """sources: [{"path": "...", "recursive": True/False}, ...]"""
        self.sources = sources
        self._rebuild_playlist()

    def set_interval(self, interval_text: str):
        self.interval_text = interval_text
        self.restart_timer()

    def set_mode(self, mode_text: str):
        self.mode_text = mode_text
        mode = "random" if mode_text == "隨機" else "sequential"
        self.playlist.set_mode(mode)

    def _rebuild_playlist(self):
        files = []
        for src in self.sources:
            p = Path(src["path"])
            recursive = src.get("recursive", False)
            if p.is_dir():
                if recursive:
                    for f in p.rglob("*"):
                        if f.is_file() and f.suffix.lower() in IMAGE_EXTS:
                            files.append(str(f))
                else:
                    for f in p.iterdir():
                        if f.is_file() and f.suffix.lower() in IMAGE_EXTS:
                            files.append(str(f))
            elif p.is_file() and p.suffix.lower() in IMAGE_EXTS:
                files.append(str(p))
        self.playlist.set_images(files)
        mode = "random" if self.mode_text == "隨機" else "sequential"
        self.playlist.set_mode(mode)

    def apply_current(self):
        path = self.playlist.current()
        if path:
            self.engine.apply_smart_fill(
                path, screen_mode=self.screen_mode_text)
            self.wallpaper_changed.emit(path)
            return path
        return None

    def next(self):
        path = self.playlist.next()
        if path:
            self.engine.apply_smart_fill(
                path, screen_mode=self.screen_mode_text)
            self.wallpaper_changed.emit(path)
            self.restart_timer()
            return path
        return None

    def prev(self):
        path = self.playlist.prev()
        if path:
            self.engine.apply_smart_fill(
                path, screen_mode=self.screen_mode_text)
            self.wallpaper_changed.emit(path)
            self.restart_timer()
            return path
        return None

    def restart_timer(self):
        self.timer.stop()
        self.is_paused = False
        if self.interval_text == "不限時間":
            return
        mapping = {
            "10秒": 10, "15秒": 15, "30秒": 30,
            "1分鐘": 60, "5分鐘": 300, "10分鐘": 600,
            "15分鐘": 900, "30分鐘": 1800,
        }
        seconds = mapping.get(self.interval_text, 10)
        self.timer.start(seconds * 1000)

    def start(self):
        if self.playlist.images:
            self.apply_current()
            self.restart_timer()

    def stop(self):
        self.timer.stop()
        self.is_paused = True

    def delete_current(self):
        current = self.playlist.current()
        if not current:
            return False
        from send2trash import send2trash
        try:
            send2trash(current)
            self._rebuild_playlist()
            if self.playlist.images:
                self.next()
            else:
                self.stop()
            return True
        except Exception as e:
            print(f"刪除失敗: {e}")
            return False
