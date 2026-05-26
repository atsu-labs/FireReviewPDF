from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QLabel, QComboBox
from PySide6.QtCore import Qt, QSize, Signal
import qtawesome as qta
from ..canvas import ToolMode

class MainToolBar(QFrame):
    tool_changed = Signal(int)  # Emits selected ToolMode
    zoom_changed = Signal(str)  # Emits current text of zoom combo

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ToolBar")
        self.tool_btns = []
        self._setup_ui()

    def _setup_ui(self):
        t_layout = QHBoxLayout(self)
        t_layout.setContentsMargins(10, 0, 10, 0)

        tools = [
            ('fa5s.mouse-pointer', "選択", ToolMode.SELECT),
            ('fa5s.hand-paper', "パン", ToolMode.NONE),
            ('fa5s.pencil-alt', "直線（折れ線）", ToolMode.DRAW_LINE),
            ('fa5s.square', "矩形", ToolMode.POLYGON_AREA),
            ('fa5s.circle', "円", ToolMode.DRAW_CIRCLE_DRAG),
            ('fa5s.font', "テキスト", ToolMode.TEXT),
        ]

        for icon_name, tip, mode in tools:
            btn = QPushButton()
            btn.setIcon(qta.icon(icon_name, color='white'))
            btn.setIconSize(QSize(20, 20))
            btn.setObjectName("ToolBtn")
            btn.setProperty("tool_mode", mode)
            btn.setToolTip(tip)
            btn.setFixedSize(40, 40)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, m=mode, b=btn: self._on_tool_clicked(m, b))
            t_layout.addWidget(btn)
            self.tool_btns.append(btn)

        t_layout.addStretch()
        
        t_layout.addWidget(QLabel("表示倍率:"))
        self.zoom_combo = QComboBox()
        self.zoom_combo.setEditable(True)
        self.zoom_combo.setFixedWidth(85)
        self.zoom_combo.setStyleSheet(
            "QComboBox { background-color: #2a2a3d; color: #ffffff; border: 1px solid #555566; border-radius: 4px; padding: 2px 5px; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { background-color: #1e1e2e; color: #ffffff; selection-background-color: #7c4dff; }"
        )
        presets = ["25%", "50%", "75%", "100%", "125%", "150%", "200%", "300%", "400%"]
        self.zoom_combo.addItems(presets)
        self.zoom_combo.setCurrentText("100%")
        
        # Connect zoom events
        self.zoom_combo.currentIndexChanged.connect(self._on_zoom_combo_changed)
        self.zoom_combo.lineEdit().returnPressed.connect(self._on_zoom_combo_changed)
        t_layout.addWidget(self.zoom_combo)

        self.scale_status_label = QLabel("スケール: 未キャリブレーション")
        t_layout.addWidget(self.scale_status_label)

        self.pdf_size_label = QLabel("サイズ: 不明")
        t_layout.addWidget(self.pdf_size_label)

    def _on_tool_clicked(self, mode, active_btn):
        self.set_active_tool_button(active_btn)
        self.tool_changed.emit(mode)

    def _on_zoom_combo_changed(self):
        text = self.zoom_combo.currentText().strip()
        self.zoom_changed.emit(text)

    def set_active_tool_button(self, active_btn):
        for btn in self.tool_btns:
            is_active = (active_btn is not None and btn == active_btn)
            btn.setChecked(is_active)
            btn.setProperty("active", is_active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def set_tool_mode(self, mode):
        """Finds and sets the active tool button based on the mode."""
        active_btn = None
        for btn in self.tool_btns:
            if btn.property("tool_mode") == mode:
                active_btn = btn
                break
        self.set_active_tool_button(active_btn)
