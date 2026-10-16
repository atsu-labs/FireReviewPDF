from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QLabel, QComboBox
from PySide6.QtCore import Qt, QSize, Signal
import qtawesome as qta
from ..canvas import ToolMode

class MainToolBar(QFrame):
    tool_changed = Signal(int)  # Emits selected ToolMode
    zoom_changed = Signal(str)  # Emits current text of zoom combo
    open_pdf_requested = Signal()
    save_project_requested = Signal()
    export_pdf_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ToolBar")
        self.tool_btns = []
        self.quick_action_btns = []
        self._setup_ui()

    def _setup_ui(self):
        t_layout = QHBoxLayout(self)
        t_layout.setContentsMargins(10, 0, 10, 0)

        # クイックファイル操作
        quick_actions = [
            ('fa5s.folder-open', "PDF図面を開く (Ctrl+O)", self.open_pdf_requested),
            ('fa5s.save', "プロジェクトを保存 (Ctrl+S)", self.save_project_requested),
            ('fa5s.file-export', "PDFを書き出し (Ctrl+E)", self.export_pdf_requested),
        ]

        for icon_name, tip, sig in quick_actions:
            btn = QPushButton()
            btn.setIcon(qta.icon(icon_name, color='#ffffff'))
            btn.setIconSize(QSize(18, 18))
            btn.setObjectName("QuickActionBtn")
            btn.setToolTip(tip)
            btn.setFixedSize(36, 36)
            btn.clicked.connect(sig.emit)
            t_layout.addWidget(btn)
            self.quick_action_btns.append(btn)

        # セパレーター
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #333344; background-color: #333344; width: 1px; margin: 4px 6px;")
        t_layout.addWidget(sep)

        tools = [
            ('fa5s.mouse-pointer', "選択 (V)", ToolMode.SELECT),
            ('fa5s.hand-paper', "パン (H)", ToolMode.NONE),
            ('fa5s.pencil-alt', "直線（折れ線） (L)", ToolMode.DRAW_LINE),
            ('fa5s.square', "矩形 (R)", ToolMode.POLYGON_AREA),
            ('fa5s.circle', "円 (C)", ToolMode.DRAW_CIRCLE_DRAG),
            ('fa5s.circle-notch', "円弧", ToolMode.DRAW_ARC),
            ('fa5s.cloud', "雲マーク (K)", ToolMode.DRAW_CLOUD),
            ('fa5s.font', "テキスト (T)", ToolMode.TEXT),
            ('fa5s.map-marker-alt', "マーカー (M)", ToolMode.DRAW_MARKER),
            ('fa5s.list-alt', "凡例", ToolMode.DRAW_LEGEND),
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

    def set_tool_enabled(self, mode, enabled):
        for btn in self.tool_btns:
            if btn.property("tool_mode") == mode:
                btn.setEnabled(enabled)
                break
