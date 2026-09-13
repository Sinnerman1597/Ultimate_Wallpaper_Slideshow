import random
from typing import List, Optional


class Playlist:
    def __init__(self):
        self.images: List[str] = []
        self.index: int = 0
        self.mode: str = "sequential"  # sequential | random
        self._history: List[int] = []  # 已播放過的 index，供上一張使用

    def set_images(self, images: List[str]):
        self.images = list(images) if images else []
        self.index = 0
        self._history = []

    def set_mode(self, mode: str):
        if mode in ("sequential", "random"):
            self.mode = mode

    def current(self) -> Optional[str]:
        if not self.images:
            return None
        if self.index < 0 or self.index >= len(self.images):
            self.index = 0
        return self.images[self.index]

    def next(self) -> Optional[str]:
        if not self.images:
            return None

        # 記下目前這張，供上一張返回
        self._history.append(self.index)

        if self.mode == "random":
            if len(self.images) == 1:
                self.index = 0
            else:
                # 盡量不連續抽到同一張
                choices = list(range(len(self.images)))
                choices.remove(self.index)
                self.index = random.choice(choices)
        else:
            self.index = (self.index + 1) % len(self.images)

        return self.current()

    def prev(self) -> Optional[str]:
        if not self.images:
            return None

        if self._history:
            # 回到上一張真正顯示過的
            self.index = self._history.pop()
        else:
            # 沒有歷史時：順序模式往回；隨機模式也往回一格（不新抽）
            self.index = (self.index - 1) % len(self.images)

        return self.current()
