import json
from pathlib import Path
from typing import Dict, Any


class ConfigManager:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.data: Dict[str, Any] = {
            "last_edit_key": "all",
            "ui_sources": {
                "folders": [],   # [{"path": str, "recursive": bool}, ...]
                "images": [],    # [path, ...]
                "videos": []
            },
            "players": {
                # "all" / "1" / "2": {
                #   "sources": [{"path": str, "recursive": bool}, ...],
                #   "interval": "10秒",
                #   "mode": "順序"
                # }
            }
        }
        self.load()

    def load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    self.data.update(loaded)
            except Exception as e:
                print(f"讀取設定失敗: {e}")

    def save(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"儲存設定失敗: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()
