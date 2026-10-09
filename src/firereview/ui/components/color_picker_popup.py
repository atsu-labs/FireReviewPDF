from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QPushButton, QLabel, QColorDialog, QFrame
)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QColor


# 頻出する標準12色（マーカーパレット10色＋白・黒）
STANDARD_PALETTE_COLORS = [
    "#ff1744",  # 赤
    "#2979ff",  # 青
    "#00e676",  # 緑
    "#ffd600",  # 黄
    "#ff9100",  # 橙
    "#f50057",  # ピンク
    "#d500f9",  # 紫
    "#8d6e63",  # 茶
    "#00e5ff",  # 水色
    "#aeea00",  # 黄緑
    "#ffffff",  # 白
    "#000000",  # 黒
]

# セッション間で共有される最近使った色の履歴（最大5色）
_RECENT_COLORS_HISTORY = []


def add_to_recent_colors(color_hex: str) -> None:
    """指定された色を最近使った色の履歴に追加します。"""
    if not color_hex:
        return
    color_hex = color_hex.lower()
    if color_hex in _RECENT_COLORS_HISTORY:
        _RECENT_COLORS_HISTORY.remove(color_hex)
    _RECENT_COLORS_HISTORY.insert(0, color_hex)
    if len(_RECENT_COLORS_HISTORY) > 5:
        _RECENT_COLORS_HISTORY.pop()


class ColorPickerPopup(QWidget):
    """
    ボタンクリック直下に展開するコンパクトなポップアップ型カラーパレット。
    標準パレット、最近使った色、塗りなし（オプション）、その他の色（QColorDialog）を提供します。
    """
    color_selected = Signal(str)

    def __init__(self, parent=None, current_color: str = "", allow_none: bool = False, title: str = "色を選択"):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.current_color = current_color.lower() if current_color else ""
        self.allow_none = allow_none
        self.title_text = title

        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("""
            QWidget#ColorPickerPopup {
                background-color: #242436;
                border: 1px solid #4a4a68;
                border-radius: 6px;
            }
            QLabel {
                color: #b0b0c8;
                font-size: 11px;
            }
            QPushButton.colorChip {
                border-radius: 4px;
                border: 1px solid #555577;
            }
            QPushButton.colorChip:hover {
                border: 2px solid #ffffff;
            }
            QPushButton.actionBtn {
                background-color: #323248;
                color: #e0e0ff;
                border: 1px solid #4a4a68;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton.actionBtn:hover {
                background-color: #424260;
                color: #ffffff;
                border: 1px solid #7c4dff;
            }
        """)
        self.setObjectName("ColorPickerPopup")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # タイトル
        title_label = QLabel(self.title_text)
        title_label.setStyleSheet("font-weight: bold; color: #ffffff;")
        main_layout.addWidget(title_label)

        # 塗りなしボタン（塗りの色選択時のみ）
        if self.allow_none:
            none_btn = QPushButton("✕ 塗りなし")
            none_btn.setObjectName("noneBtn")
            none_btn.setProperty("class", "actionBtn")
            none_btn.setStyleSheet("""
                QPushButton {
                    background-color: #323248;
                    color: #ff6e6e;
                    border: 1px solid #555577;
                    border-radius: 4px;
                    padding: 4px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #4a2830;
                    border-color: #ff5252;
                }
            """)
            none_btn.clicked.connect(self._on_none_clicked)
            main_layout.addWidget(none_btn)

        # 標準パレットセクション
        main_layout.addWidget(QLabel("標準色"))
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(5)

        cols = 6
        for idx, hex_color in enumerate(STANDARD_PALETTE_COLORS):
            row = idx // cols
            col = idx % cols
            btn = self._create_color_button(hex_color)
            grid.addWidget(btn, row, col)

        main_layout.addWidget(grid_widget)

        # 最近使った色セクション（履歴が存在する場合）
        if _RECENT_COLORS_HISTORY:
            main_layout.addWidget(QLabel("最近使った色"))
            recent_widget = QWidget()
            recent_layout = QHBoxLayout(recent_widget)
            recent_layout.setContentsMargins(0, 0, 0, 0)
            recent_layout.setSpacing(5)

            for hex_color in _RECENT_COLORS_HISTORY:
                btn = self._create_color_button(hex_color)
                recent_layout.addWidget(btn)
            recent_layout.addStretch()
            main_layout.addWidget(recent_widget)

        # その他の色... ボタン
        custom_btn = QPushButton("その他の色...")
        custom_btn.setProperty("class", "actionBtn")
        custom_btn.setStyleSheet("""
            QPushButton {
                background-color: #323248;
                color: #e0e0ff;
                border: 1px solid #4a4a68;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #424260;
                color: #ffffff;
                border: 1px solid #7c4dff;
            }
        """)
        custom_btn.clicked.connect(self._on_custom_color_clicked)
        main_layout.addWidget(custom_btn)

    def _create_color_button(self, hex_color: str) -> QPushButton:
        btn = QPushButton()
        btn.setFixedSize(22, 22)
        btn.setProperty("class", "colorChip")
        is_selected = (self.current_color == hex_color.lower())
        border_style = "2px solid #ffffff" if is_selected else "1px solid #555577"
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {hex_color};
                border: {border_style};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid #ffffff;
            }}
        """)
        btn.clicked.connect(lambda checked, c=hex_color: self._on_color_chip_clicked(c))
        return btn

    def _on_color_chip_clicked(self, hex_color: str):
        add_to_recent_colors(hex_color)
        self.color_selected.emit(hex_color)
        self.close()

    def _on_none_clicked(self):
        self.color_selected.emit("")
        self.close()

    def _on_custom_color_clicked(self):
        self.hide()
        initial = QColor(self.current_color) if self.current_color else QColor("#7c4dff")
        color = QColorDialog.getColor(initial, self.parent())
        if color.isValid():
            hex_color = color.name()
            add_to_recent_colors(hex_color)
            self.color_selected.emit(hex_color)
        self.close()

    def show_below(self, target_widget: QWidget):
        """対象ウィジェットの直下にポップアップを表示します。"""
        if not target_widget:
            self.show()
            return
        global_pos = target_widget.mapToGlobal(QPoint(0, target_widget.height() + 2))
        self.move(global_pos)
        self.show()
