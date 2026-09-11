import os
from pathlib import Path
from typing import List, Dict

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif'}
VIDEO_EXTS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.webm'}


class SourceManager:
    def __init__(self):
        # path, enabled, recursive, type, media_filter, bind_screen
        # media_filter: "image" | "video" | "both"
        # bind_screen: "all" | "1" | "2" | ...
        self.sources: List[Dict] = []

    def add_folder(self, folder_path: str, recursive: bool = False,
                   media_filter: str = "image", bind_screen: str = "all"):
        p = Path(folder_path)
        if not p.is_dir():
            return False
        # 避免重複加入
        for s in self.sources:
            if s["path"] == str(p):
                return False
        self.sources.append({
            "path": str(p),
            "enabled": True,
            "recursive": recursive,
            "type": "folder",
            "media_filter": media_filter,
            "bind_screen": bind_screen
        })
        return True

    def add_file(self, file_path: str, bind_screen: str = "all"):
        p = Path(file_path)
        ext = p.suffix.lower()
        if ext not in IMAGE_EXTS and ext not in VIDEO_EXTS:
            return False
        for s in self.sources:
            if s["path"] == str(p):
                return False
        self.sources.append({
            "path": str(p),
            "enabled": True,
            "recursive": False,
            "type": "file",
            "media_filter": "image" if ext in IMAGE_EXTS else "video",
            "bind_screen": bind_screen
        })
        return True

    def remove_source(self, index: int):
        if 0 <= index < len(self.sources):
            self.sources.pop(index)

    def set_enabled(self, index: int, enabled: bool):
        if 0 <= index < len(self.sources):
            self.sources[index]["enabled"] = enabled

    def set_recursive(self, index: int, recursive: bool):
        if 0 <= index < len(self.sources):
            self.sources[index]["recursive"] = recursive

    def set_media_filter(self, index: int, media_filter: str):
        if 0 <= index < len(self.sources):
            self.sources[index]["media_filter"] = media_filter

    def set_bind_screen(self, index: int, bind_screen: str):
        if 0 <= index < len(self.sources):
            self.sources[index]["bind_screen"] = bind_screen

    def _match_ext(self, path: Path, media_filter: str) -> bool:
        ext = path.suffix.lower()
        if media_filter == "image":
            return ext in IMAGE_EXTS
        if media_filter == "video":
            return ext in VIDEO_EXTS
        return ext in IMAGE_EXTS or ext in VIDEO_EXTS

    def get_files_for_screen(self, screen_mode: str) -> List[str]:
        """
        screen_mode: "所有螢幕同步" / "螢幕1" / "螢幕2" ...
        """
        target = "all"
        if screen_mode.startswith("螢幕"):
            try:
                target = screen_mode.replace("螢幕", "")
            except Exception:
                target = "all"

        result = []
        for src in self.sources:
            if not src["enabled"]:
                continue

            # 綁定檢查
            bind = src.get("bind_screen", "all")
            if bind != "all" and bind != target and target != "all":
                continue
            # 如果目前是「所有螢幕同步」，只收 bind=all 的來源
            if target == "all" and bind != "all":
                continue

            p = Path(src["path"])
            media_filter = src.get("media_filter", "image")

            if src["type"] == "file":
                if p.exists() and self._match_ext(p, media_filter):
                    result.append(str(p))
            else:
                if not p.is_dir():
                    continue
                if src.get("recursive", False):
                    for f in p.rglob("*"):
                        if f.is_file() and self._match_ext(f, media_filter):
                            result.append(str(f))
                else:
                    for f in p.iterdir():
                        if f.is_file() and self._match_ext(f, media_filter):
                            result.append(str(f))
        return result

    # 相容舊程式
    def get_all_images(self) -> List[str]:
        return self.get_files_for_screen("所有螢幕同步")
