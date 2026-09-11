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

    window = MainWindow(source_manager, engine, config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
