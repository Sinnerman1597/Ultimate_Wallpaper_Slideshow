import os
from pathlib import Path
from typing import List, Dict

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif'}


class SourceManager:
    def __init__(self):
        self.sources: List[Dict] = []   # [{path, enabled, recursive, type}]

    def add_folder(self, folder_path: str, recursive: bool = False):
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
            "type": "folder"
        })
        return True

    def add_file(self, file_path: str):
        p = Path(file_path)
        if p.suffix.lower() not in IMAGE_EXTS:
            return False
        for s in self.sources:
            if s["path"] == str(p):
                return False
        self.sources.append({
            "path": str(p),
            "enabled": True,
            "recursive": False,
            "type": "file"
        })
        return True

    def remove_source(self, index: int):
        if 0 <= index < len(self.sources):
            self.sources.pop(index)

    def set_enabled(self, index: int, enabled: bool):
        if 0 <= index < len(self.sources):
            self.sources[index]["enabled"] = enabled

    def get_all_images(self) -> List[str]:
        images = []
        for src in self.sources:
            if not src["enabled"]:
                continue
            p = Path(src["path"])
            if src["type"] == "file":
                if p.exists():
                    images.append(str(p))
            else:
                if not p.is_dir():
                    continue
                if src["recursive"]:
                    for f in p.rglob("*"):
                        if f.is_file() and f.suffix.lower() in IMAGE_EXTS:
                            images.append(str(f))
                else:
                    for f in p.iterdir():
                        if f.is_file() and f.suffix.lower() in IMAGE_EXTS:
                            images.append(str(f))
        return images
