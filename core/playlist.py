import random
from typing import List, Optional


class Playlist:
    def __init__(self):
        self.images: List[str] = []
        self.index = 0
        self.mode = "sequential"   # sequential | random

    def set_images(self, images: List[str]):
        self.images = images
        self.index = 0

    def set_mode(self, mode: str):
        self.mode = mode

    def current(self) -> Optional[str]:
        if not self.images:
            return None
        return self.images[self.index]

    def next(self) -> Optional[str]:
        if not self.images:
            return None
        if self.mode == "random":
            self.index = random.randint(0, len(self.images) - 1)
        else:
            self.index = (self.index + 1) % len(self.images)
        return self.current()

    def prev(self) -> Optional[str]:
        if not self.images:
            return None
        if self.mode == "random":
            self.index = random.randint(0, len(self.images) - 1)
        else:
            self.index = (self.index - 1) % len(self.images)
        return self.current()
