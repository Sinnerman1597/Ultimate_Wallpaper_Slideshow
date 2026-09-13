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
    IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif'}
    VIDEO_EXTS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.webm'}

    def __init__(self, source_manager, engine, config):
        super().__init__()
        self.source_manager = source_manager
        self.engine = engine
        self.config = config

        self.current_edit_key = "all"      # 目前正在設定的螢幕
        self.is_editing = False
        self.last_sync_sources = []      # 最後一次「所有螢幕同步」的來源
        self.independent_keys = set()    # 同步之後，有「再次確認過」的各別螢幕
        self._tree_check_guard = False

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

        # 從 config 還原來源列表與各螢幕設定
        self._restore_from_config()
        # 還原後依「誰有來源」決定互斥啟動
        all_player = self.players.get("all")
        all_has = all_player and bool(all_player.playlist.images)
        any_single = any(
            k != "all" and bool(p.playlist.images)
            for k, p in self.players.items()
        )
        if any_single:
            self._apply_mutex("1")   # 走「各別螢幕」分支即可
        elif self.players.get("all") and self.players["all"].playlist.images:
            self._apply_mutex("all")

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

        # ===== 左邊：三大區塊來源列表 =====
        left = QVBoxLayout()
        left.addWidget(QLabel("來源列表（勾選後按右側「確認」套用到目前螢幕）"))

        from PySide6.QtWidgets import QSplitter, QTreeWidget, QTreeWidgetItem, QAbstractItemView

        self.splitter = QSplitter(Qt.Orientation.Vertical)

        # --- 資料夾區塊（階層）---
        folder_widget = QWidget()
        folder_layout = QVBoxLayout(folder_widget)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_header = QHBoxLayout()
        self.chk_all_folders = QCheckBox()
        self.chk_all_folders.setToolTip("全選／取消全選資料夾")
        folder_header.addWidget(self.chk_all_folders)
        folder_header.addWidget(QLabel("📁 資料夾"))
        folder_header.addStretch()
        folder_layout.addLayout(folder_header)
        self.tree_folders = QTreeWidget()
        self.tree_folders.setHeaderHidden(True)
        self.tree_folders.setExpandsOnDoubleClick(False)  # 重要：雙擊不展開
        self.tree_folders.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        folder_layout.addWidget(self.tree_folders)
        self.splitter.addWidget(folder_widget)

        # --- 圖片 ---
        image_widget = QWidget()
        image_layout = QVBoxLayout(image_widget)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_header = QHBoxLayout()
        self.chk_all_images = QCheckBox()
        self.chk_all_images.setToolTip("全選／取消全選圖片")
        image_header.addWidget(self.chk_all_images)
        image_header.addWidget(QLabel("🖼 圖片"))
        image_header.addStretch()
        image_layout.addLayout(image_header)
        self.list_images = QListWidget()
        self.list_images.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        image_layout.addWidget(self.list_images)
        self.splitter.addWidget(image_widget)

        # --- 影片 ---
        video_widget = QWidget()
        video_layout = QVBoxLayout(video_widget)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_header = QHBoxLayout()
        self.chk_all_videos = QCheckBox()
        self.chk_all_videos.setToolTip("全選／取消全選影片")
        video_header.addWidget(self.chk_all_videos)
        video_header.addWidget(QLabel("🎬 影片"))
        video_header.addStretch()
        video_layout.addLayout(video_header)
        self.list_videos = QListWidget()
        self.list_videos.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        video_layout.addWidget(self.list_videos)
        self.splitter.addWidget(video_widget)

        self.splitter.setSizes([300, 200, 100])
        left.addWidget(self.splitter)

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
        self.tree_folders.itemDoubleClicked.connect(
            self.on_folder_double_clicked)
        self.tree_folders.itemExpanded.connect(self.on_folder_expanded)
        self.tree_folders.itemChanged.connect(self.on_folder_item_changed)
        self.chk_all_folders.stateChanged.connect(self._toggle_all_folders)
        self.chk_all_images.stateChanged.connect(self._toggle_all_images)
        self.chk_all_videos.stateChanged.connect(self._toggle_all_videos)

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
            self._save_all_config()

    def on_mode_changed(self, text):
        if not self.is_editing:
            player = self.players[self.current_edit_key]
            player.set_mode(text)
            self._save_all_config()

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "選擇資料夾")
        if not folder:
            return
        # 避免重複
        for i in range(self.tree_folders.topLevelItemCount()):
            if self.tree_folders.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole) == folder:
                return

        root = self._create_folder_item(folder, recursive=True)
        self.tree_folders.addTopLevelItem(root)
        self._load_subfolders(root)  # 載入一層子資料夾
        self._save_all_config()

    def _create_folder_item(self, path: str, recursive: bool = True):
        from PySide6.QtWidgets import QTreeWidgetItem
        item = QTreeWidgetItem()
        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled |
            Qt.ItemFlag.ItemIsSelectable |
            Qt.ItemFlag.ItemIsUserCheckable
        )
        item.setCheckState(0, Qt.CheckState.Checked)  # 新增時預設勾選
        item.setData(0, Qt.ItemDataRole.UserRole, path)
        item.setData(0, Qt.ItemDataRole.UserRole + 1, recursive)
        item.setText(0, path if recursive else f"{path}  【僅本層】")
        return item

    def _load_subfolders(self, parent_item):
        """載入下一層子資料夾（階層用）"""
        from PySide6.QtWidgets import QTreeWidgetItem
        path = parent_item.data(0, Qt.ItemDataRole.UserRole)
        if not path:
            return
        p = Path(path)
        if not p.is_dir():
            return
        try:
            for sub in sorted(p.iterdir()):
                if sub.is_dir():
                    # 避免重複加
                    exists = False
                    for i in range(parent_item.childCount()):
                        if parent_item.child(i).data(0, Qt.ItemDataRole.UserRole) == str(sub):
                            exists = True
                            break
                    if exists:
                        continue
                    child = self._create_folder_item(str(sub), recursive=True)
                    parent_item.addChild(child)
                    # 繼承母資料夾勾選狀態
                    child.setCheckState(0, parent_item.checkState(0))
        except Exception:
            pass

    def add_file(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "選擇檔案",
            filter="Media (*.jpg *.jpeg *.png *.bmp *.webp *.gif *.mp4 *.mkv *.avi *.mov *.webm)"
        )
        for f in files:
            ext = Path(f).suffix.lower()
            if ext in self.IMAGE_EXTS:
                self._add_to_list(self.list_images, f)
            elif ext in self.VIDEO_EXTS:
                self._add_to_list(self.list_videos, f)

        self._save_all_config()

    def _add_to_list(self, list_widget: QListWidget, path: str):
        for i in range(list_widget.count()):
            if list_widget.item(i).data(Qt.ItemDataRole.UserRole) == path:
                return
        item = QListWidgetItem(path)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked)
        item.setData(Qt.ItemDataRole.UserRole, path)
        list_widget.addItem(item)

    def _normalize_check_state(self, state):
        """相容 int 與 CheckState"""
        if state == Qt.CheckState.Checked or state == 2 or state == Qt.CheckState.Checked.value:
            return Qt.CheckState.Checked
        return Qt.CheckState.Unchecked

    def _set_tree_checked(self, item, state):
        item.setCheckState(0, state)
        for i in range(item.childCount()):
            self._set_tree_checked(item.child(i), state)

    def _toggle_all_folders(self, state):
        check = self._normalize_check_state(state)
        for i in range(self.tree_folders.topLevelItemCount()):
            self._set_tree_checked(self.tree_folders.topLevelItem(i), check)

    def _toggle_all_images(self, state):
        check = self._normalize_check_state(state)
        for i in range(self.list_images.count()):
            self.list_images.item(i).setCheckState(check)

    def _toggle_all_videos(self, state):
        check = self._normalize_check_state(state)
        for i in range(self.list_videos.count()):
            self.list_videos.item(i).setCheckState(check)

    def remove_selected(self):
        # 資料夾：收集所有勾選節點後刪除
        to_remove = []

        def collect(item):
            for i in range(item.childCount()):
                collect(item.child(i))
            if item.checkState(0) == Qt.CheckState.Checked:
                to_remove.append(item)

        for i in range(self.tree_folders.topLevelItemCount()):
            collect(self.tree_folders.topLevelItem(i))

        for item in to_remove:
            parent = item.parent()
            if parent:
                parent.removeChild(item)
            else:
                idx = self.tree_folders.indexOfTopLevelItem(item)
                if idx >= 0:
                    self.tree_folders.takeTopLevelItem(idx)

        # 圖片、影片
        for lw in (self.list_images, self.list_videos):
            for i in range(lw.count() - 1, -1, -1):
                if lw.item(i).checkState() == Qt.CheckState.Checked:
                    lw.takeItem(i)

        self._save_all_config()

    def on_folder_double_clicked(self, item, column):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if not path or not Path(path).is_dir():
            return
        was_expanded = item.isExpanded()
        recursive = not bool(item.data(0, Qt.ItemDataRole.UserRole + 1))
        item.setData(0, Qt.ItemDataRole.UserRole + 1, recursive)
        item.setText(0, path if recursive else f"{path}  【僅本層】")
        item.setExpanded(was_expanded)
        self._save_all_config()

    def _set_tree_checked_recursive(self, item, state):
        """由上往下設定勾選，不觸發 itemChanged 遞迴爆炸"""
        item.setCheckState(0, state)
        for i in range(item.childCount()):
            self._set_tree_checked_recursive(item.child(i), state)

    def on_folder_item_changed(self, item, column):
        """母資料夾勾選／取消 → 連動所有子資料夾"""
        if column != 0:
            return
        if self._tree_check_guard:
            return

        self._tree_check_guard = True
        try:
            state = item.checkState(0)
            # 只往下連動，不往上改父層
            for i in range(item.childCount()):
                self._set_tree_checked_recursive(item.child(i), state)
        finally:
            self._tree_check_guard = False

    def on_folder_expanded(self, item):
        """展開時載入下一層（若還沒載入）"""
        if item.childCount() == 0:
            self._load_subfolders(item)
        else:
            # 再往下一層預載
            for i in range(item.childCount()):
                child = item.child(i)
                if child.childCount() == 0:
                    self._load_subfolders(child)

    def _apply_mutex(self, active_key: str):
        """
        active_key == "all"：只跑同步，各別螢幕停止，並清空「已獨立」標記。
        active_key 為 "1"/"2"...：停止同步；
        - 在 independent_keys 裡的螢幕用自己的 sources
        - 其餘各別螢幕改用 last_sync_sources（維持同步時的內容）
        """
        if active_key == "all":
            self.independent_keys.clear()
            for key, player in self.players.items():
                if key == "all":
                    if player.playlist.images:
                        player.start()
                    else:
                        player.stop()
                else:
                    player.stop()
            return

        # 各別螢幕模式
        if "all" in self.players:
            self.players["all"].stop()

        for key, player in self.players.items():
            if key == "all":
                continue
            if key in self.independent_keys:
                # 使用者有為這個螢幕按過確認 → 用自己的來源
                if player.playlist.images:
                    player.start()
                else:
                    player.stop()
            else:
                # 尚未再確認 → 跟隨最後一次同步來源
                if self.last_sync_sources:
                    player.set_sources(list(self.last_sync_sources))
                    if player.playlist.images:
                        player.start()
                    else:
                        player.stop()
                else:
                    player.stop()

    def confirm_edit(self):
        sources = []

        # 收集有勾選的資料夾（含子節點）
        def collect_tree(item):
            checked = item.checkState(0) == Qt.CheckState.Checked
            path = item.data(0, Qt.ItemDataRole.UserRole)
            # recursive=True 表示「含子層」；False 表示「僅本層」
            recursive = bool(item.data(0, Qt.ItemDataRole.UserRole + 1))

            if checked and path:
                if not recursive:
                    # ===== 僅本層：絕對優先，只收本層，忽略所有子節點 =====
                    sources.append({"path": path, "recursive": False})
                    return

                # ===== 含子層 =====
                # 若有任何子節點被勾選 → 本層只收直接檔案，再依子節點規則往下
                # 若沒有子節點、或子節點都沒勾 → 整棵 rglob（等同只選這個資料夾）
                any_child_checked = False
                for i in range(item.childCount()):
                    if item.child(i).checkState(0) == Qt.CheckState.Checked:
                        any_child_checked = True
                        break

                if item.childCount() == 0 or not any_child_checked:
                    sources.append({"path": path, "recursive": True})
                else:
                    sources.append({"path": path, "recursive": False})
                    for i in range(item.childCount()):
                        collect_tree(item.child(i))
                return

            # 自己沒勾選 → 仍檢查子節點（例如只勾了深層的 D）
            for i in range(item.childCount()):
                collect_tree(item.child(i))

        for i in range(self.tree_folders.topLevelItemCount()):
            collect_tree(self.tree_folders.topLevelItem(i))

        # 圖片
        for i in range(self.list_images.count()):
            item = self.list_images.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                path = item.data(Qt.ItemDataRole.UserRole)
                if path:
                    sources.append({"path": path, "recursive": False})

        # 影片（目前引擎還是以圖片為主，先收進清單，之後接影片再播）
        for i in range(self.list_videos.count()):
            item = self.list_videos.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                path = item.data(Qt.ItemDataRole.UserRole)
                if path:
                    sources.append({"path": path, "recursive": False})

        player = self.players[self.current_edit_key]
        player.set_sources(sources)
        player.set_interval(self.combo_interval.currentText())
        player.set_mode(self.combo_mode.currentText())

        if self.current_edit_key == "all":
            self.last_sync_sources = [dict(s) for s in sources]
            self.independent_keys.clear()
        else:
            self.independent_keys.add(self.current_edit_key)

        # 互斥：同步 vs 各別螢幕
        self._apply_mutex(self.current_edit_key)

        self.is_editing = False
        self.btn_edit.setEnabled(True)
        self.btn_confirm.setEnabled(False)
        self.combo_screen.setEnabled(True)
        QMessageBox.information(self, "完成", f"已套用到目前螢幕（{len(sources)} 個來源）。")
        self._save_all_config()

    def _collect_ui_sources(self) -> dict:
        """收集左側三大區塊目前的來源（供下次啟動還原列表）"""
        folders = []
        for i in range(self.tree_folders.topLevelItemCount()):
            item = self.tree_folders.topLevelItem(i)
            path = item.data(0, Qt.ItemDataRole.UserRole)
            recursive = bool(item.data(0, Qt.ItemDataRole.UserRole + 1))
            if path:
                folders.append({"path": path, "recursive": recursive})

        images = []
        for i in range(self.list_images.count()):
            p = self.list_images.item(i).data(Qt.ItemDataRole.UserRole)
            if p:
                images.append(p)

        videos = []
        for i in range(self.list_videos.count()):
            p = self.list_videos.item(i).data(Qt.ItemDataRole.UserRole)
            if p:
                videos.append(p)

        return {"folders": folders, "images": images, "videos": videos}

    def _save_all_config(self):
        """把 UI 來源 + 各螢幕 player 設定寫入 config.json"""
        players_data = {}
        for key, player in self.players.items():
            players_data[key] = {
                "sources": player.sources,
                "interval": player.interval_text,
                "mode": player.mode_text,
            }
        self.config.set("players", players_data)
        self.config.set("ui_sources", self._collect_ui_sources())
        self.config.set("last_edit_key", self.current_edit_key)

    def _restore_from_config(self):
        """啟動時還原左側列表與各 ScreenPlayer"""
        ui = self.config.get("ui_sources") or {}
        folders = ui.get("folders") or []
        images = ui.get("images") or []
        videos = ui.get("videos") or []

        # 還原資料夾（僅頂層；子層展開時再載入）
        for fd in folders:
            path = fd.get("path")
            recursive = fd.get("recursive", True)
            if not path or not Path(path).exists():
                continue
            # 避免重複
            exists = False
            for i in range(self.tree_folders.topLevelItemCount()):
                if self.tree_folders.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole) == path:
                    exists = True
                    break
            if exists:
                continue
            root = self._create_folder_item(path, recursive=recursive)
            self.tree_folders.addTopLevelItem(root)
            self._load_subfolders(root)

        for p in images:
            if Path(p).exists():
                self._add_to_list(self.list_images, p)

        for p in videos:
            if Path(p).exists():
                self._add_to_list(self.list_videos, p)

        # 還原各螢幕 player
        players_data = self.config.get("players") or {}
        for key, player in self.players.items():
            pdata = players_data.get(key)
            if not pdata:
                continue
            sources = pdata.get("sources") or []
            # 過濾不存在的路徑
            valid = []
            for s in sources:
                path = s.get("path") if isinstance(s, dict) else None
                if path and Path(path).exists():
                    valid.append(s)
            player.set_sources(valid)
            player.set_interval(pdata.get("interval", "10秒"))
            player.set_mode(pdata.get("mode", "順序"))

        # 還原上次編輯的螢幕選項
        last_key = self.config.get("last_edit_key", "all")
        if last_key == "all":
            self.combo_screen.setCurrentText("所有螢幕同步")
        else:
            text = f"螢幕{last_key}"
            idx = self.combo_screen.findText(text)
            if idx >= 0:
                self.combo_screen.setCurrentIndex(idx)
        self.current_edit_key = self._get_key_from_combo()
        self._update_lock_label()

        # 同步右側週期／模式顯示
        player = self.players.get(self.current_edit_key)
        if player:
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

    def closeEvent(self, event):
        """關閉視窗時存檔"""
        self._save_all_config()
        super().closeEvent(event)

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
