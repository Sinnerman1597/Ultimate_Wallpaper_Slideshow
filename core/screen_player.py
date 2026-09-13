from pathlib import Path
from typing import List, Optional
from PySide6.QtCore import QObject, QTimer, Signal
from core.playlist import Playlist

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif'}
VIDEO_EXTS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.webm'}


class ScreenPlayer(QObject):
    """單一螢幕的獨立播放器"""
    wallpaper_changed = Signal(str)  # 發出目前桌布路徑（給外部參考）

    def __init__(self, screen_key: str, screen_mode_text: str, engine, video_wall, parent=None):
        super().__init__(parent)
        self.screen_key = screen_key          # "all" / "1" / "2" ...
        self.screen_mode_text = screen_mode_text  # "所有螢幕同步" / "螢幕1" ...
        self.engine = engine

        self.playlist = Playlist()
        # [{"path": str, "recursive": bool}, ...]
        self.sources: List[dict] = []
        self.interval_text = "10秒"
        self.last_numeric_interval = "10秒"  # 「播完為止」時圖片用的上一次秒數
        self.mode_text = "順序"
        self.is_paused = False
        self.video_wall = video_wall  # 共用一個 VideoWallpaper 實例（4-2 單螢幕）
        self._is_all = False
        self._video_walls = []          # 僅 all 使用
        self._ordered_geometries = []   # 僅 all 使用
        self._screen_index_0 = 0      # 0-based，稍後由 MainWindow 設定
        self._geometry = None  # (x, y, w, h)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next)

    @staticmethod
    def is_video_path(path: str) -> bool:
        return Path(path).suffix.lower() in VIDEO_EXTS

    def set_sources(self, sources: List[dict]):
        """sources: [{"path": "...", "recursive": True/False}, ...]"""
        self.sources = sources
        self._rebuild_playlist()

    def set_interval(self, interval_text: str):
        self.interval_text = interval_text
        # 只有一般秒數才更新「上一次秒數」
        if interval_text not in ("不限時間", "播完為止(僅影片)"):
            self.last_numeric_interval = interval_text
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
                found = []
                if recursive:
                    iterator = p.rglob("*")
                else:
                    iterator = p.iterdir()
                for f in iterator:
                    if not f.is_file():
                        continue
                    ext = f.suffix.lower()
                    if ext in IMAGE_EXTS or ext in VIDEO_EXTS:
                        found.append(str(f))
                found.sort()
                files.extend(found)
            elif p.is_file():
                ext = p.suffix.lower()
                if ext in IMAGE_EXTS or ext in VIDEO_EXTS:
                    files.append(str(p))

        self.playlist.set_images(files)
        mode = "random" if self.mode_text == "隨機" else "sequential"
        self.playlist.set_mode(mode)

    def apply_current(self):
        path = self.playlist.current()
        if not path:
            return None

        if self.is_video_path(path):
            loop = self.interval_text != "播完為止(僅影片)"
            if getattr(self, "_is_all", False) and self._video_walls:
                # 同步：每個螢幕各播同一支影片
                ok_any = False
                for idx, vw in enumerate(self._video_walls):
                    geo = None
                    if idx < len(self._ordered_geometries):
                        geo = self._ordered_geometries[idx]
                    if vw.play(path, screen_index=idx, loop=loop, geometry=geo):
                        ok_any = True
                if ok_any:
                    self.wallpaper_changed.emit(path)
                    return path
                return None

            if self.video_wall:
                ok = self.video_wall.play(
                    path,
                    screen_index=self._screen_index_0,
                    loop=loop,
                    geometry=self._geometry,
                )
                if ok:
                    self.wallpaper_changed.emit(path)
                    return path
            print(f"影片播放失敗: {path}")
            return None

        # 圖片：先停 mpv，再設靜態桌布
        if getattr(self, "_is_all", False):
            for vw in getattr(self, "_video_walls", []):
                vw.stop()
        elif self.video_wall:
            self.video_wall.stop()

        self.engine.apply_smart_fill(path, screen_mode=self.screen_mode_text)
        self.wallpaper_changed.emit(path)
        return path

    def next(self):
        path = self.playlist.next()
        if not path:
            return None
        result = self.apply_current()
        self.restart_timer()
        return result

    def prev(self):
        path = self.playlist.prev()
        if not path:
            return None
        result = self.apply_current()
        self.restart_timer()
        return result

    def restart_timer(self):
        self.timer.stop()
        self.is_paused = False

        text = self.interval_text
        if text == "不限時間":
            return

        # 播完為止：影片由 4-2/4-3 用結束事件切換；圖片用上一次秒數
        if text == "播完為止(僅影片)":
            text = self.last_numeric_interval or "10秒"

        mapping = {
            "10秒": 10, "15秒": 15, "30秒": 30,
            "1分鐘": 60, "5分鐘": 300, "10分鐘": 600,
            "15分鐘": 900, "30分鐘": 1800,
        }
        seconds = mapping.get(text, 10)
        self.timer.start(seconds * 1000)

    def start(self):
        if self.playlist.images:
            self.apply_current()
            self.restart_timer()

    def stop(self):
        self.timer.stop()
        self.is_paused = True
        if getattr(self, "_is_all", False):
            for vw in getattr(self, "_video_walls", []):
                vw.stop()
        elif self.video_wall:
            self.video_wall.stop()

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
