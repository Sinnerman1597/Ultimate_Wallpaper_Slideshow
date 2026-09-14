import sys
from PySide6.QtWidgets import QApplication
from core.wallpaper_engine import WallpaperEngine
from core.config_manager import ConfigManager
from ui.main_window import MainWindow
from utils.win32_helper import get_system_wallpaper_path


def main():
    app = QApplication(sys.argv)

    config = ConfigManager()
    engine = WallpaperEngine()

    # 第一次換桌布前，記住系統桌布路徑
    original = get_system_wallpaper_path()
    if original:
        config.data["original_wallpaper"] = original

    window = MainWindow(engine, config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
