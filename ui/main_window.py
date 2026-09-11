from ui.floating_toolbar import FloatingToolbar
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QPushButton, QLabel, QComboBox,
    QFileDialog, QGroupBox, QListWidgetItem, QAbstractItemView,
    QApplication, QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt, QTimer
from core.screen_player import ScreenPlayer


class MainWindow(QMainWindow):
    def __init__(self, source_manager, engine, config):
        super().__init__()
        self.source_manager = source_manager
        self.engine = engine
        self.config = config

        self.current_edit_key = "all"      # 目前正在設定的螢幕
        self.is_editing = False

        # 每個螢幕一個獨立播放器
        self._create_players()

        self.setWindowTitle("UWS")
        self.resize(960, 640)

        self._setup_ui()
        self._connect_signals()
        self._init_screen_combo()
        self._update_lock_label()

        # 每個螢幕一個浮動工具列（使用已排序的 ordered_screens）
        self.toolbars = []
        for idx, screen in enumerate(self.ordered_screens):
            key = str(idx + 1)
            tb = FloatingToolbar()
            tb.prev_clicked.connect(
                lambda checked=False, k=key: self._toolbar_prev(k))
            tb.next_clicked.connect(
                lambda checked=False, k=key: self._toolbar_next(k))
            tb.pause_clicked.connect(
                lambda checked=False, k=key, toolbar=tb: self._toolbar_pause(k, toolbar))
            tb.delete_clicked.connect(
                lambda checked=False, k=key: self._toolbar_delete(k))
            tb.show()
            geo = screen.availableGeometry()
            tb.move(geo.right() - 240, geo.bottom() - 80)
            self.toolbars.append(tb)

        # 啟動所有播放器
        for player in self.players.values():
            player.start()

    def _create_players(self):
        # 依螢幕左到右排序
        screens = sorted(QApplication.screens(),
                         key=lambda s: s.geometry().x())
        self.ordered_screens = screens          # 存起來給工具列用
        self.screen_count = len(screens)

        self.players = {}
        self.players["all"] = ScreenPlayer("all", "所有螢幕同步", self.engine)

        for i, screen in enumerate(screens, start=1):
            key = str(i)
            self.players[key] = ScreenPlayer(key, f"螢幕{i}", self.engine)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # ===== 左邊：來源列表 =====
        left = QVBoxLayout()
        left.addWidget(QLabel("來源列表（勾選後按確認才會套用到目前螢幕）"))
        self.source_list = QListWidget()
        self.source_list.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        left.addWidget(self.source_list)

        btn_row = QHBoxLayout()
        self.btn_add_folder = QPushButton("新增資料夾")
        self.btn_add_file = QPushButton("新增檔案")
        self.btn_remove = QPushButton("刪除選取")
        btn_row.addWidget(self.btn_add_folder)
        btn_row.addWidget(self.btn_add_file)
        btn_row.addWidget(self.btn_remove)
        left.addLayout(btn_row)

        layout.addLayout(left, 2)

        # ===== 右邊：設定 =====
        right = QVBoxLayout()

        self.lbl_lock_status = QLabel("目前設定：所有螢幕同步")
        self.lbl_lock_status.setStyleSheet(
            "font-weight: bold; color: #0066cc; font-size: 14px;")
        right.addWidget(self.lbl_lock_status)

        # 更新週期
        group_time = QGroupBox("更新週期（套用到目前設定的螢幕）")
        time_layout = QVBoxLayout()
        self.combo_interval = QComboBox()
        self.combo_interval.addItems([
            "10秒", "15秒", "30秒", "1分鐘", "5分鐘",
            "10分鐘", "15分鐘", "30分鐘", "不限時間"
        ])
        self.combo_interval.setCurrentText("10秒")
        time_layout.addWidget(self.combo_interval)
        group_time.setLayout(time_layout)
        right.addWidget(group_time)

        # 播放模式
        group_mode = QGroupBox("播放模式（套用到目前設定的螢幕）")
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

        btn_row2 = QHBoxLayout()
        self.btn_edit = QPushButton("調整來源")
        self.btn_confirm = QPushButton("確認")
        self.btn_confirm.setEnabled(False)
        btn_row2.addWidget(self.btn_edit)
        btn_row2.addWidget(self.btn_confirm)
        screen_layout.addLayout(btn_row2)

        self.lbl_screen_info = QLabel(f"目前偵測到 {self.screen_count} 個螢幕")
        screen_layout.addWidget(self.lbl_screen_info)
        group_screen.setLayout(screen_layout)
        right.addWidget(group_screen)

        # 手動控制（操作目前正在設定的螢幕）
        group_ctrl = QGroupBox("手動控制（目前設定的螢幕）")
        ctrl_layout = QVBoxLayout()
        self.btn_prev = QPushButton("上一張")
        self.btn_next = QPushButton("下一張")
        ctrl_layout.addWidget(self.btn_prev)
        ctrl_layout.addWidget(self.btn_next)
        group_ctrl.setLayout(ctrl_layout)
        right.addWidget(group_ctrl)

        right.addStretch()
        layout.addLayout(right, 1)

    def _init_screen_combo(self):
        self.combo_screen.clear()
        self.combo_screen.addItem("所有螢幕同步")
        for i in range(1, self.screen_count + 1):
            self.combo_screen.addItem(f"螢幕{i}")

    def _connect_signals(self):
        self.btn_add_folder.clicked.connect(self.add_folder)
        self.btn_add_file.clicked.connect(self.add_file)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_prev.clicked.connect(self.prev_current)
        self.btn_next.clicked.connect(self.next_current)
        self.combo_interval.currentTextChanged.connect(
            self.on_interval_changed)
        self.combo_mode.currentTextChanged.connect(self.on_mode_changed)
        self.combo_screen.currentTextChanged.connect(self.on_screen_changed)
        self.btn_edit.clicked.connect(self.start_edit)
        self.btn_confirm.clicked.connect(self.confirm_edit)
        self.source_list.itemDoubleClicked.connect(self.on_item_double_clicked)

    def _get_key_from_combo(self) -> str:
        text = self.combo_screen.currentText()
        if text == "所有螢幕同步":
            return "all"
        return text.replace("螢幕", "")

    def _update_lock_label(self):
        if self.current_edit_key == "all":
            self.lbl_lock_status.setText("目前設定：所有螢幕同步")
        else:
            self.lbl_lock_status.setText(f"目前設定：螢幕{self.current_edit_key}")

    def start_edit(self):
        self.is_editing = True
        self.btn_edit.setEnabled(False)
        self.btn_confirm.setEnabled(True)
        self.combo_screen.setEnabled(False)
        QMessageBox.information(self, "調整來源",
                                "請勾選要給目前螢幕使用的來源。\n"
                                "資料夾項目可點擊後方的【僅本層】文字來切換。\n"
                                "完成後按「確認」。")

    def confirm_edit(self):
        sources = []
        for i in range(self.source_list.count()):
            item = self.source_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                path = item.data(Qt.ItemDataRole.UserRole)
                recursive = item.data(Qt.ItemDataRole.UserRole + 1)
                if path:
                    sources.append(
                        {"path": path, "recursive": bool(recursive)})

        player = self.players[self.current_edit_key]
        player.set_sources(sources)
        player.set_interval(self.combo_interval.currentText())
        player.set_mode(self.combo_mode.currentText())
        player.start()

        self.is_editing = False
        self.btn_edit.setEnabled(True)
        self.btn_confirm.setEnabled(False)
        self.combo_screen.setEnabled(True)
        QMessageBox.information(self, "完成", f"已套用到目前螢幕（{len(sources)} 個來源）。")

    def on_screen_changed(self, text):
        if self.is_editing:
            return
        self.current_edit_key = self._get_key_from_combo()
        self._update_lock_label()

        player = self.players[self.current_edit_key]
        # 同步 UI 顯示該螢幕的設定
        idx = self.combo_interval.findText(player.interval_text)
        if idx >= 0:
            self.combo_interval.blockSignals(True)
            self.combo_interval.setCurrentIndex(idx)
            self.combo_interval.blockSignals(False)
        idx = self.combo_mode.findText(player.mode_text)
        if idx >= 0:
            self.combo_mode.blockSignals(True)
            self.combo_mode.setCurrentIndex(idx)
            self.combo_mode.blockSignals(False)

    def on_interval_changed(self, text):
        if not self.is_editing:
            player = self.players[self.current_edit_key]
            player.set_interval(text)

    def on_mode_changed(self, text):
        if not self.is_editing:
            player = self.players[self.current_edit_key]
            player.set_mode(text)

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "選擇資料夾")
        if not folder:
            return
        if not self.source_manager.add_folder(folder):
            return

        # 預設遞迴（含子層），可點擊切換為僅本層
        recursive = True
        text = f"{folder}"
        item = QListWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked)
        item.setData(Qt.ItemDataRole.UserRole, folder)          # path
        item.setData(Qt.ItemDataRole.UserRole + 1, recursive)   # recursive
        self.source_list.addItem(item)
        self._update_item_display(item)

    def add_file(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "選擇檔案",
            filter="Media (*.jpg *.jpeg *.png *.bmp *.webp *.gif *.mp4 *.mkv *.avi *.mov *.webm)"
        )
        for f in files:
            if self.source_manager.add_file(f):
                item = QListWidgetItem(f)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                item.setData(Qt.ItemDataRole.UserRole, f)
                item.setData(Qt.ItemDataRole.UserRole + 1, False)
                self.source_list.addItem(item)

    def _update_item_display(self, item: QListWidgetItem):
        path = item.data(Qt.ItemDataRole.UserRole)
        recursive = item.data(Qt.ItemDataRole.UserRole + 1)
        if Path(path).is_dir():
            if recursive:
                item.setText(path)
            else:
                item.setText(f"{path}  【僅本層】")
        else:
            item.setText(path)

    def on_item_double_clicked(self, item: QListWidgetItem):
        """雙擊資料夾項目才切換「僅本層」"""
        path = item.data(Qt.ItemDataRole.UserRole)
        if not path or not Path(path).is_dir():
            return
        recursive = item.data(Qt.ItemDataRole.UserRole + 1)
        item.setData(Qt.ItemDataRole.UserRole + 1, not recursive)
        self._update_item_display(item)

    def remove_selected(self):
        rows = sorted({self.source_list.row(i)
                      for i in self.source_list.selectedItems()}, reverse=True)
        for row in rows:
            self.source_manager.remove_source(row)
            self.source_list.takeItem(row)

    def prev_current(self):
        self.players[self.current_edit_key].prev()

    def next_current(self):
        self.players[self.current_edit_key].next()

    # ===== 浮動工具列專用（對應各自螢幕）=====
    def _toolbar_prev(self, key: str):
        if key in self.players:
            self.players[key].prev()

    def _toolbar_next(self, key: str):
        if key in self.players:
            self.players[key].next()

    def _toolbar_pause(self, key: str, toolbar):
        player = self.players.get(key)
        if not player:
            return
        if player.timer.isActive():
            # 目前正在自動換 → 改為暫停
            player.stop()
            toolbar.set_paused(True)   # 顯示 ▶
        else:
            # 目前暫停中 → 恢復自動換
            player.restart_timer()
            toolbar.set_paused(False)  # 顯示 ⏸

    def _toolbar_delete(self, key: str):
        if key in self.players:
            self.players[key].delete_current()
