import sys
from PySide6.QtWidgets import QApplication
from core.source_manager import SourceManager
from core.playlist import Playlist
from core.wallpaper_engine import WallpaperEngine
from core.config_manager import ConfigManager
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    config = ConfigManager()
    source_manager = SourceManager()
    playlist = Playlist()
    engine = WallpaperEngine()

    # 載入之前儲存的來源
    for src in config.get("sources", []):
        if src["type"] == "folder":
            source_manager.add_folder(src["path"], src.get("recursive", False))
        else:
            source_manager.add_file(src["path"])
        # 還原啟用狀態
        if source_manager.sources:
            source_manager.sources[-1]["enabled"] = src.get("enabled", True)

    window = MainWindow(source_manager, playlist, engine, config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
