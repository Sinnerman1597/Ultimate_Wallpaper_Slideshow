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
    engine = WallpaperEngine()

    # 啟動當下先記住系統桌布（必須在第一次換桌布前）
    original_wallpaper = get_system_wallpaper_path()
    if original_wallpaper:
        config.data["original_wallpaper"] = original_wallpaper
        # 不要 config.set，避免一啟動就寫入；關閉時一併存

    window = MainWindow(source_manager, engine, config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
