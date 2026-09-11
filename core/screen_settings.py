from typing import Dict, List, Any


class ScreenSettings:
    """每個螢幕獨立設定"""

    def __init__(self):
        # key: "all" / "1" / "2" / ...
        self.settings: Dict[str, Dict[str, Any]] = {
            "all": {
                "sources": [],          # 來源路徑列表
                "interval": "15秒",
                "mode": "順序"
            }
        }

    def ensure_screen(self, key: str):
        if key not in self.settings:
            self.settings[key] = {
                "sources": [],
                "interval": "15秒",
                "mode": "順序"
            }

    def get(self, key: str) -> Dict[str, Any]:
        self.ensure_screen(key)
        return self.settings[key]

    def set_sources(self, key: str, sources: List[str]):
        self.ensure_screen(key)
        self.settings[key]["sources"] = sources

    def set_interval(self, key: str, interval: str):
        self.ensure_screen(key)
        self.settings[key]["interval"] = interval

    def set_mode(self, key: str, mode: str):
        self.ensure_screen(key)
        self.settings[key]["mode"] = mode
