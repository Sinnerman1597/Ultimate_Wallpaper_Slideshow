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

    # 不再自動載入之前的來源，每次重啟都重新選擇
    window = MainWindow(source_manager, playlist, engine, config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
