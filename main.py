import sys
from PySide6.QtWidgets import QApplication
from core.source_manager import SourceManager
from core.playlist import Playlist
from core.wallpaper_engine import WallpaperEngine
from core.config_manager import ConfigManager
from ui.main_window import MainWindow
from utils.win32_helper import get_system_wallpaper_path


def main():
    app = QApplication(sys.argv)

    config = ConfigManager()
    source_manager = SourceManager()
    engine = WallpaperEngine()

    # 第一次換桌布前，記住系統桌布路徑
    from utils.win32_helper import get_system_wallpaper_path
    original = get_system_wallpaper_path()
    if original:
        config.data["original_wallpaper"] = original

    window = MainWindow(source_manager, engine, config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
