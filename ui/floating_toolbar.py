from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class FloatingToolbar(QWidget):
    prev_clicked = Signal()
    next_clicked = Signal()
    pause_clicked = Signal()
    delete_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(0.45)          # 預設半透明
        self.setFixedHeight(42)
        self.setMinimumWidth(220)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        font = QFont("Segoe UI", 14)

        self.btn_prev = QPushButton("▲")
        self.btn_next = QPushButton("▼")
        self.btn_pause = QPushButton("⏸")
        self.btn_delete = QPushButton("✕")

        for btn in (self.btn_prev, self.btn_next, self.btn_pause, self.btn_delete):
            btn.setFont(font)
            btn.setFixedSize(40, 32)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(30, 30, 30, 180);
                    color: white;
                    border: none;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: rgba(70, 70, 70, 220);
                }
            """)
            layout.addWidget(btn)

        self.btn_delete.setStyleSheet("""
            QPushButton {
                background-color: rgba(180, 40, 40, 200);
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: rgba(220, 50, 50, 230);
            }
        """)

        self.btn_prev.clicked.connect(self.prev_clicked.emit)
        self.btn_next.clicked.connect(self.next_clicked.emit)
        self.btn_pause.clicked.connect(self.pause_clicked.emit)
        self.btn_delete.clicked.connect(self.delete_clicked.emit)

        self.is_paused = False

    def enterEvent(self, event):
        self.setWindowOpacity(0.92)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setWindowOpacity(0.45)
        super().leaveEvent(event)

    def set_paused(self, paused: bool):
        self.is_paused = paused
        self.btn_pause.setText("▶" if paused else "⏸")
