"""獨立圖片預覽：快速上一張／下一張／刪除（與桌布互不干擾）"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QKeyEvent, QResizeEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QMessageBox, QSizePolicy,
)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif"}


class PreviewPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.files: List[str] = []
        self.index: int = 0
        # 簡單快取：路徑 -> 原始 QPixmap（未縮放），加速來回切換
        self._cache: dict[str, QPixmap] = {}
        self._cache_order: List[str] = []
        self._cache_max = 12

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        self.btn_open = QPushButton("開啟資料夾")
        self.btn_open.clicked.connect(self.open_folder)
        top.addWidget(self.btn_open)
        top.addStretch()
        layout.addLayout(top)

        self.lbl_title = QLabel("尚未載入圖片")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.lbl_title)

        self.lbl_image = QLabel()
        self.lbl_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_image.setMinimumSize(320, 240)
        self.lbl_image.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.lbl_image.setStyleSheet("background: #1e1e1e; color: #aaa;")
        self.lbl_image.setText("請開啟資料夾")
        layout.addWidget(self.lbl_image, stretch=1)

        self.lbl_info = QLabel("")
        self.lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_info)

        btns = QHBoxLayout()
        self.btn_prev = QPushButton("上一張 (A / ←)")
        self.btn_next = QPushButton("下一張 (D / →)")
        self.btn_del = QPushButton("刪除 (W / ↑)")
        self.btn_del.setStyleSheet("color: #c00; font-weight: bold;")
        self.btn_prev.clicked.connect(self.prev_image)
        self.btn_next.clicked.connect(self.next_image)
        self.btn_del.clicked.connect(self.delete_current)
        btns.addWidget(self.btn_prev)
        btns.addWidget(self.btn_next)
        btns.addWidget(self.btn_del)
        layout.addLayout(btns)

    # ----- 來源 -----
    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "選擇圖片資料夾")
        if not folder:
            return
        files = []
        p = Path(folder)
        try:
            for f in sorted(p.iterdir()):
                if f.is_file() and f.suffix.lower() in IMAGE_EXTS:
                    files.append(str(f.resolve()))
        except Exception as e:
            QMessageBox.warning(self, "錯誤", f"讀取資料夾失敗：{e}")
            return
        if not files:
            QMessageBox.information(self, "提示", "此資料夾沒有支援的圖片。")
            return
        self._cache.clear()
        self._cache_order.clear()
        self.files = files
        self.index = 0
        self.show_current()
        self.setFocus()

    # ----- 顯示（效能：快取 + FastTransformation）-----
    def _get_pixmap(self, path: str) -> Optional[QPixmap]:
        if path in self._cache:
            return self._cache[path]
        pm = QPixmap(path)
        if pm.isNull():
            return None
        self._cache[path] = pm
        self._cache_order.append(path)
        while len(self._cache_order) > self._cache_max:
            old = self._cache_order.pop(0)
            self._cache.pop(old, None)
        return pm

    def _prefetch_neighbors(self):
        for j in (self.index - 1, self.index + 1):
            if 0 <= j < len(self.files):
                self._get_pixmap(self.files[j])

    def show_current(self):
        if not self.files:
            self.lbl_title.setText("尚未載入圖片")
            self.lbl_image.setText("請開啟資料夾")
            self.lbl_image.setPixmap(QPixmap())
            self.lbl_info.setText("")
            return

        if self.index < 0:
            self.index = 0
        if self.index >= len(self.files):
            self.index = len(self.files) - 1

        path = self.files[self.index]
        p = Path(path)
        self.lbl_title.setText(f"{p.parent.name}-{p.name}")
        self.lbl_info.setText(f"{self.index + 1} / {len(self.files)}")

        pm = self._get_pixmap(path)
        if pm is None or pm.isNull():
            self.lbl_image.setText("無法載入")
            self.lbl_image.setPixmap(QPixmap())
            return

        area = self.lbl_image.size()
        if area.width() < 10 or area.height() < 10:
            area = QSize(800, 600)
        # FastTransformation：瀏覽優先，幾乎無感延遲
        scaled = pm.scaled(
            area,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self.lbl_image.setPixmap(scaled)
        self._prefetch_neighbors()

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        if self.files:
            self.show_current()

    # ----- 操作 -----
    def prev_image(self):
        if not self.files:
            return
        self.index = (self.index - 1) % len(self.files)
        self.show_current()

    def next_image(self):
        if not self.files:
            return
        self.index = (self.index + 1) % len(self.files)
        self.show_current()

    def delete_current(self):
        if not self.files:
            return
        path = self.files[self.index]
        try:
            from send2trash import send2trash
            send2trash(path)
        except Exception as e:
            QMessageBox.warning(self, "刪除失敗", str(e))
            return

        self._cache.pop(path, None)
        if path in self._cache_order:
            self._cache_order.remove(path)
        del self.files[self.index]

        if not self.files:
            self.index = 0
            self.show_current()
            return
        if self.index >= len(self.files):
            self.index = len(self.files) - 1
        self.show_current()

    # ----- 鍵盤：方向鍵 + WASD -----
    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key in (Qt.Key.Key_Left, Qt.Key.Key_A):
            self.prev_image()
            event.accept()
            return
        if key in (Qt.Key.Key_Right, Qt.Key.Key_D):
            self.next_image()
            event.accept()
            return
        if key in (Qt.Key.Key_Up, Qt.Key.Key_W):
            self.delete_current()
            event.accept()
            return
        super().keyPressEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.setFocus()
