from ui.floating_toolbar import FloatingToolbar
from pathlib import Path
import shutil
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QPushButton, QLabel, QComboBox,
    QFileDialog, QGroupBox, QListWidgetItem, QAbstractItemView,
    QApplication
)
from PySide6.QtCore import Qt, QTimer
from send2trash import send2trash


class MainWindow(QMainWindow):
    def __init__(self, source_manager, playlist, engine, config):
        super().__init__()
        self.source_manager = source_manager
        self.playlist = playlist
        self.engine = engine
        self.config = config

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_wallpaper)

        self.setWindowTitle("UWS")
        self.resize(920, 600)
        self._setup_ui()
        self._connect_signals()
        self._restore_from_config()
        # 多螢幕浮動工具列
        self.toolbars = []
        screens = QApplication.screens()
        for screen in screens:
            tb = FloatingToolbar()
            tb.prev_clicked.connect(self.prev_wallpaper)
            tb.next_clicked.connect(self.next_wallpaper)
            tb.pause_clicked.connect(self.toggle_pause)
            tb.delete_clicked.connect(self.delete_current)
            tb.show()

            # 放在螢幕右下角
            geo = screen.availableGeometry()
            tb.move(geo.right() - 240, geo.bottom() - 80)
            self.toolbars.append(tb)

        # 啟動後如果有圖片就直接套用
        self.refresh_and_apply()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # ===== 左邊：來源列表 =====
        left = QVBoxLayout()
        left.addWidget(QLabel("來源列表（勾選 = 啟用）"))
        self.source_list = QListWidget()
        self.source_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        left.addWidget(self.source_list)

        btn_row = QHBoxLayout()
        self.btn_add_folder = QPushButton("新增資料夾")
        self.btn_add_file = QPushButton("新增圖片")
        self.btn_remove = QPushButton("刪除選取")
        btn_row.addWidget(self.btn_add_folder)
        btn_row.addWidget(self.btn_add_file)
        btn_row.addWidget(self.btn_remove)
        left.addLayout(btn_row)

        self.btn_refresh = QPushButton("重新掃描並套用")
        left.addWidget(self.btn_refresh)

        layout.addLayout(left, 2)

        # ===== 右邊：設定 =====
        right = QVBoxLayout()

        # 更新週期
        group_time = QGroupBox("更新週期")
        time_layout = QVBoxLayout()
        self.combo_interval = QComboBox()
        self.combo_interval.addItems([
            "10秒", "15秒", "30秒", "1分鐘", "5分鐘",
            "10分鐘", "15分鐘", "30分鐘", "不限時間"
        ])
        self.combo_interval.setCurrentText("15秒")
        time_layout.addWidget(self.combo_interval)
        group_time.setLayout(time_layout)
        right.addWidget(group_time)

        # 播放模式
        group_mode = QGroupBox("播放模式")
        mode_layout = QVBoxLayout()
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["順序", "隨機"])
        mode_layout.addWidget(self.combo_mode)
        group_mode.setLayout(mode_layout)
        right.addWidget(group_mode)

        # 多螢幕
        group_screen = QGroupBox("多螢幕")
        screen_layout = QVBoxLayout()
        self.combo_screen = QComboBox()
        screen_layout.addWidget(self.combo_screen)

        # 顯示偵測到的螢幕數量
        from PySide6.QtWidgets import QApplication
        self.screen_count = len(QApplication.screens())
        self.lbl_screen_info = QLabel(f"目前偵測到 {self.screen_count} 個螢幕")
        screen_layout.addWidget(self.lbl_screen_info)
        group_screen.setLayout(screen_layout)
        right.addWidget(group_screen)

        # 縮放說明
        group_scale = QGroupBox("縮放模式")
        scale_layout = QVBoxLayout()
        scale_layout.addWidget(QLabel("智慧填滿\n（直圖左右自動取邊緣色留白）"))
        group_scale.setLayout(scale_layout)
        right.addWidget(group_scale)

        # 手動控制
        group_ctrl = QGroupBox("手動控制")
        ctrl_layout = QVBoxLayout()
        self.btn_prev = QPushButton("上一張")
        self.btn_next = QPushButton("下一張")
        ctrl_layout.addWidget(self.btn_prev)
        ctrl_layout.addWidget(self.btn_next)
        group_ctrl.setLayout(ctrl_layout)
        right.addWidget(group_ctrl)

        right.addStretch()
        layout.addLayout(right, 1)

    def _connect_signals(self):
        self.btn_add_folder.clicked.connect(self.add_folder)
        self.btn_add_file.clicked.connect(self.add_file)
        self.btn_remove.clicked.connect(self.remove_source)
        self.btn_refresh.clicked.connect(self.refresh_and_apply)
        self.btn_prev.clicked.connect(self.prev_wallpaper)
        self.btn_next.clicked.connect(self.next_wallpaper)
        self.combo_interval.currentTextChanged.connect(
            self.on_interval_changed)
        self.combo_mode.currentTextChanged.connect(self.on_mode_changed)
        self.combo_screen.currentTextChanged.connect(
            self.on_screen_mode_changed)
        self.source_list.itemChanged.connect(self.on_source_item_changed)
        self.source_list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self.source_list.customContextMenuRequested.connect(
            self.show_source_context_menu)

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "選擇資料夾")
        if folder:
            if self.source_manager.add_folder(folder):
                item = QListWidgetItem(folder)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                self.source_list.addItem(item)
                self.refresh_and_apply()

    def add_file(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "選擇圖片",
            filter="Images (*.jpg *.jpeg *.png *.bmp *.webp *.gif)"
        )
        for f in files:
            if self.source_manager.add_file(f):
                item = QListWidgetItem(f)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                self.source_list.addItem(item)
        if files:
            self.refresh_and_apply()

    def remove_source(self):
        row = self.source_list.currentRow()
        if row >= 0:
            self.source_manager.remove_source(row)
            self.source_list.takeItem(row)
            self.refresh_and_apply()

    def on_source_item_changed(self, item: QListWidgetItem):
        row = self.source_list.row(item)
        enabled = item.checkState() == Qt.CheckState.Checked
        self.source_manager.set_enabled(row, enabled)
        self.refresh_and_apply()

    def refresh_and_apply(self):
        mode = self.combo_screen.currentText()
        files = self.source_manager.get_files_for_screen(mode)
        self.playlist.set_images(files)
        if files:
            self.apply_current()
            self.restart_timer()
        else:
            self.timer.stop()

    def apply_current(self):
        path = self.playlist.current()
        if path:
            mode = self.combo_screen.currentText()
            self.engine.apply_smart_fill(path, screen_mode=mode)

    def next_wallpaper(self):
        path = self.playlist.next()
        if path:
            mode = self.combo_screen.currentText()
            self.engine.apply_smart_fill(path, screen_mode=mode)
            self.restart_timer()

    def prev_wallpaper(self):
        path = self.playlist.prev()
        if path:
            mode = self.combo_screen.currentText()
            self.engine.apply_smart_fill(path, screen_mode=mode)
            self.restart_timer()

    def on_interval_changed(self, text):
        self.restart_timer()

    def on_mode_changed(self, text):
        mode = "random" if text == "隨機" else "sequential"
        self.playlist.set_mode(mode)

    def restart_timer(self):
        self.timer.stop()
        text = self.combo_interval.currentText()
        if text == "不限時間":
            return
        mapping = {
            "10秒": 10, "15秒": 15, "30秒": 30,
            "1分鐘": 60, "5分鐘": 300, "10分鐘": 600,
            "15分鐘": 900, "30分鐘": 1800,
        }
        seconds = mapping.get(text, 15)
        self.timer.start(seconds * 1000)

    def toggle_pause(self):
        if self.timer.isActive():
            self.timer.stop()
            for tb in self.toolbars:
                tb.set_paused(True)
        else:
            self.restart_timer()
            for tb in self.toolbars:
                tb.set_paused(False)

    def delete_current(self):
        current = self.playlist.current()
        if not current:
            return
        src = Path(current)
        if not src.exists():
            return
        try:
            send2trash(str(src))
            images = self.source_manager.get_all_images()
            self.playlist.set_images(images)
            if self.playlist.images:
                self.next_wallpaper()
            else:
                self.timer.stop()
        except Exception as e:
            print(f"移至資源回收筒失敗: {e}")
            # 如果失敗，可在這裡加備案（移到 Delete 資料夾），目前先單純提示

    def _restore_from_config(self):
        # 還原下拉選單
        interval = self.config.get("interval", "15秒")
        idx = self.combo_interval.findText(interval)
        if idx >= 0:
            self.combo_interval.setCurrentIndex(idx)

        mode = self.config.get("mode", "順序")
        idx = self.combo_mode.findText(mode)
        if idx >= 0:
            self.combo_mode.setCurrentIndex(idx)

        screen_mode = self.config.get("screen_mode", "所有螢幕同步")
        idx = self.combo_screen.findText(screen_mode)
        if idx >= 0:
            self.combo_screen.setCurrentIndex(idx)

        # 動態產生多螢幕選項
        self.combo_screen.clear()
        self.combo_screen.addItem("所有螢幕同步")
        for i in range(1, self.screen_count + 1):
            self.combo_screen.addItem(f"螢幕{i}")

        # 還原之前選擇的項目
        screen_mode = self.config.get("screen_mode", "所有螢幕同步")
        idx = self.combo_screen.findText(screen_mode)
        if idx >= 0:
            self.combo_screen.setCurrentIndex(idx)
        else:
            self.combo_screen.setCurrentIndex(0)

    def _save_sources_to_config(self):
        sources_data = []
        for s in self.source_manager.sources:
            sources_data.append({
                "path": s["path"],
                "enabled": s["enabled"],
                "recursive": s.get("recursive", False),
                "type": s["type"]
            })
        self.config.set("sources", sources_data)

    def on_interval_changed(self, text):
        self.config.set("interval", text)
        self.restart_timer()

    def on_mode_changed(self, text):
        self.config.set("mode", text)
        mode = "random" if text == "隨機" else "sequential"
        self.playlist.set_mode(mode)

    def on_screen_mode_changed(self, text):
        self.config.set("screen_mode", text)

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "選擇資料夾")
        if not folder:
            return

        # 簡單對話：是否含子資料夾
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "子資料夾",
            "是否包含子資料夾內的檔案？\n（選「是」= 遞迴，選「否」= 僅本層）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        recursive = reply == QMessageBox.StandardButton.Yes

        if self.source_manager.add_folder(folder, recursive=recursive, media_filter="image", bind_screen="all"):
            text = f"{folder}  [{'含子層' if recursive else '僅本層'}] [圖片] [所有螢幕]"
            item = QListWidgetItem(text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, len(
                self.source_manager.sources) - 1)
            self.source_list.addItem(item)
            self.refresh_and_apply()

    def add_file(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "選擇圖片",
            filter="Images (*.jpg *.jpeg *.png *.bmp *.webp *.gif)"
        )
        changed = False
        for f in files:
            if self.source_manager.add_file(f):
                item = QListWidgetItem(f)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                self.source_list.addItem(item)
                changed = True
        if changed:
            self._save_sources_to_config()
            self.refresh_and_apply()

    def remove_source(self):
        row = self.source_list.currentRow()
        if row < 0:
            return

        # 暫時阻止 itemChanged 觸發，避免混亂
        self.source_list.blockSignals(True)
        self.source_manager.remove_source(row)
        self.source_list.takeItem(row)
        self.source_list.blockSignals(False)

        self.refresh_and_apply()

    def on_source_item_changed(self, item: QListWidgetItem):
        row = self.source_list.row(item)
        enabled = item.checkState() == Qt.CheckState.Checked
        self.source_manager.set_enabled(row, enabled)
        self._save_sources_to_config()
        self.refresh_and_apply()

    def show_source_context_menu(self, pos):
        item = self.source_list.itemAt(pos)
        if not item:
            return
        row = self.source_list.row(item)
        if row < 0 or row >= len(self.source_manager.sources):
            return

        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)

        # 綁定螢幕
        screen_menu = menu.addMenu("綁定螢幕")
        act_all = screen_menu.addAction("所有螢幕")
        act_all.triggered.connect(lambda: self._set_bind(row, "all"))
        for i in range(1, self.screen_count + 1):
            act = screen_menu.addAction(f"螢幕{i}")
            act.triggered.connect(
                lambda checked, n=i: self._set_bind(row, str(n)))

        # 子資料夾
        rec_menu = menu.addMenu("子資料夾")
        act_no = rec_menu.addAction("僅本層")
        act_no.triggered.connect(lambda: self._set_recursive(row, False))
        act_yes = rec_menu.addAction("含子層")
        act_yes.triggered.connect(lambda: self._set_recursive(row, True))

        # 媒體類型
        media_menu = menu.addMenu("媒體類型")
        act_img = media_menu.addAction("只圖片")
        act_img.triggered.connect(lambda: self._set_media(row, "image"))
        act_vid = media_menu.addAction("只影片")
        act_vid.triggered.connect(lambda: self._set_media(row, "video"))
        act_both = media_menu.addAction("圖片+影片")
        act_both.triggered.connect(lambda: self._set_media(row, "both"))

        menu.exec(self.source_list.mapToGlobal(pos))

    def _set_bind(self, row, bind):
        self.source_manager.set_bind_screen(row, bind)
        self._update_item_text(row)
        self.refresh_and_apply()

    def _set_recursive(self, row, recursive):
        self.source_manager.set_recursive(row, recursive)
        self._update_item_text(row)
        self.refresh_and_apply()

    def _set_media(self, row, media):
        self.source_manager.set_media_filter(row, media)
        self._update_item_text(row)
        self.refresh_and_apply()

    def _update_item_text(self, row):
        src = self.source_manager.sources[row]
        rec = "含子層" if src.get("recursive") else "僅本層"
        media_map = {"image": "圖片", "video": "影片", "both": "圖片+影片"}
        media = media_map.get(src.get("media_filter", "image"), "圖片")
        bind = src.get("bind_screen", "all")
        bind_text = "所有螢幕" if bind == "all" else f"螢幕{bind}"
        text = f"{src['path']}  [{rec}] [{media}] [{bind_text}]"
        self.source_list.item(row).setText(text)
