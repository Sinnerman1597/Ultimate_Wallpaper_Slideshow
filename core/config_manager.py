import json
from pathlib import Path
from typing import Dict, Any


class ConfigManager:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.data: Dict[str, Any] = {
            "interval": "15秒",
            "mode": "順序",
            "screen_mode": "所有螢幕同步",
            "sources": []
        }
        self.load()

    def load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                pass

    def save(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()
