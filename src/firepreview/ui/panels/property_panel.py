from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QColorDialog, QHBoxLayout, QFontComboBox, 
                             QSpinBox, QSlider, QFrame, QGridLayout, QPlainTextEdit, QComboBox)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QFont

class PropertyPanel(QWidget):
    attribute_changed = Signal(str, dict) # id, {attr: value}
    delete_requested = Signal(str) # id
    calculate_requested = Signal(str) # id — triggers distance/area calculation

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_item_id = None
        self.current_item_type = None
        self.current_color = "#7c4dff"
        self.current_fill_color = ""
        self._block_signals = False
        self._start_marker_values = ["", "circle", "arrow"]
        self._end_marker_values = ["", "circle", "arrow"]
        self._center_marker_values = ["", "circle", "cross", "x"]
        self.setup_ui()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(10)
        
        # Header
        self.type_title = QLabel("要素を選択してください")
        self.type_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        self.main_layout.addWidget(self.type_title)
        
        self.sub_title = QLabel("選択中の要素")
        self.sub_title.setStyleSheet("color: #888899; font-size: 12px;")
        self.main_layout.addWidget(self.sub_title)

        # --- Alignment Section ---
        self.align_container = QWidget()
        align_layout = QVBoxLayout(self.align_container)
        align_layout.setContentsMargins(0, 0, 0, 0)
        align_layout.addWidget(self._create_section_label("整列"))
        grid = QGridLayout()
        grid.setSpacing(5)
        for i, text in enumerate(["|←", "↔", "→|", "↑", "↕", "↓"]):
            btn = QPushButton(text)
            btn.setFixedSize(35, 30)
            btn.setStyleSheet("background-color: #2a2a3d; color: white; border-radius: 4px;")
            grid.addWidget(btn, 0, i)
        align_layout.addLayout(grid)
        self.main_layout.addWidget(self.align_container)

        # --- Appearance Section (Common) ---
        self.appearance_container = QWidget()
        app_layout = QVBoxLayout(self.appearance_container)
        app_layout.setContentsMargins(0, 0, 0, 0)
        app_layout.addWidget(self._create_section_label("外観"))
        
        app_layout.addWidget(QLabel("不透明度"))
        opacity_layout = QHBoxLayout()
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_layout.addWidget(self.opacity_slider)
        self.opacity_label = QLabel("100%")
        opacity_layout.addWidget(self.opacity_label)
        app_layout.addLayout(opacity_layout)

        app_layout.addWidget(QLabel("カラー"))
        color_layout = QHBoxLayout()
        self.color_preview = QFrame()
        self.color_preview.setFixedSize(24, 24)
        self.color_preview.setStyleSheet("background-color: #7c4dff; border-radius: 4px;")
        color_layout.addWidget(self.color_preview)
        self.color_hex_label = QLabel("#7C4DFF")
        self.color_hex_label.setStyleSheet("color: #ffffff; font-family: monospace;")
        color_layout.addWidget(self.color_hex_label)
        color_layout.addStretch()
        self.color_btn = QPushButton("✎")
        self.color_btn.setFixedSize(30, 30)
        self.color_btn.clicked.connect(self._on_color_clicked)
        color_layout.addWidget(self.color_btn)
        app_layout.addLayout(color_layout)
        self.main_layout.addWidget(self.appearance_container)

        # --- Fill Color Section (For Shapes with Fill) ---
        self.fill_container = QWidget()
        fill_layout = QVBoxLayout(self.fill_container)
        fill_layout.setContentsMargins(0, 0, 0, 0)
        fill_layout.addWidget(self._create_section_label("塗りの色"))
        fill_color_layout = QHBoxLayout()
        self.fill_color_preview = QFrame()
        self.fill_color_preview.setFixedSize(24, 24)
        self.fill_color_preview.setStyleSheet("background-color: transparent; border: 1px solid #3d3d5c; border-radius: 4px;")
        fill_color_layout.addWidget(self.fill_color_preview)
        self.fill_color_hex_label = QLabel("なし")
        self.fill_color_hex_label.setStyleSheet("color: #ffffff; font-family: monospace;")
        fill_color_layout.addWidget(self.fill_color_hex_label)
        fill_color_layout.addStretch()
        self.fill_color_btn = QPushButton("✎")
        self.fill_color_btn.setFixedSize(30, 30)
        self.fill_color_btn.clicked.connect(self._on_fill_color_clicked)
        fill_color_layout.addWidget(self.fill_color_btn)
        self.fill_clear_btn = QPushButton("✕")
        self.fill_clear_btn.setFixedSize(30, 30)
        self.fill_clear_btn.setToolTip("塗りなし")
        self.fill_clear_btn.clicked.connect(self._on_fill_color_cleared)
        fill_color_layout.addWidget(self.fill_clear_btn)
        fill_layout.addLayout(fill_color_layout)
        self.main_layout.addWidget(self.fill_container)

        # --- Marker Section ---
        self.marker_container = QWidget()
        mk_layout = QVBoxLayout(self.marker_container)
        mk_layout.setContentsMargins(0, 0, 0, 0)
        mk_layout.addWidget(self._create_section_label("マーカー"))

        # Polyline start/end markers
        self.line_marker_container = QWidget()
        lm_layout = QHBoxLayout(self.line_marker_container)
        lm_layout.setContentsMargins(0, 0, 0, 0)
        lm_layout.addWidget(QLabel("始点:"))
        self.start_marker_combo = QComboBox()
        self.start_marker_combo.addItems(["なし", "丸", "矢印"])
        self.start_marker_combo.currentIndexChanged.connect(self._on_start_marker_changed)
        lm_layout.addWidget(self.start_marker_combo)
        lm_layout.addWidget(QLabel("  終点:"))
        self.end_marker_combo = QComboBox()
        self.end_marker_combo.addItems(["なし", "丸", "矢印"])
        self.end_marker_combo.currentIndexChanged.connect(self._on_end_marker_changed)
        lm_layout.addWidget(self.end_marker_combo)
        lm_layout.addStretch()
        mk_layout.addWidget(self.line_marker_container)

        # Circle center marker
        self.circle_marker_container = QWidget()
        cm_layout = QHBoxLayout(self.circle_marker_container)
        cm_layout.setContentsMargins(0, 0, 0, 0)
        cm_layout.addWidget(QLabel("中心点:"))
        self.center_marker_combo = QComboBox()
        self.center_marker_combo.addItems(["なし", "丸", "十字", "バツ"])
        self.center_marker_combo.currentIndexChanged.connect(self._on_center_marker_changed)
        cm_layout.addWidget(self.center_marker_combo)
        cm_layout.addStretch()
        mk_layout.addWidget(self.circle_marker_container)

        self.main_layout.addWidget(self.marker_container)

        # --- Line Section (For Shapes) ---
        self.line_container = QWidget()
        line_layout = QVBoxLayout(self.line_container)
        line_layout.setContentsMargins(0, 0, 0, 0)
        line_layout.addWidget(self._create_section_label("線の設定"))
        line_layout.addWidget(QLabel("線の太さ"))
        self.line_width_spin = QSpinBox()
        self.line_width_spin.setRange(1, 100)
        self.line_width_spin.setSuffix(" px")
        self.line_width_spin.valueChanged.connect(self._on_line_width_changed)
        line_layout.addWidget(self.line_width_spin)
        self.main_layout.addWidget(self.line_container)

        # --- Calculate Section (For Shapes that can compute real values) ---
        self.calc_container = QWidget()
        calc_layout = QVBoxLayout(self.calc_container)
        calc_layout.setContentsMargins(0, 0, 0, 0)
        calc_layout.addWidget(self._create_section_label("計測値"))
        self.calc_btn = QPushButton("📐 計算する")
        self.calc_btn.setStyleSheet("background-color: #2a2a3d; color: white; border: 1px solid #7c4dff; border-radius: 4px; padding: 5px;")
        self.calc_btn.setToolTip("キャリブレーション済みの場合、距離/面積を計算してラベルに反映します")
        self.calc_btn.clicked.connect(self._on_calc_clicked)
        calc_layout.addWidget(self.calc_btn)
        self.main_layout.addWidget(self.calc_container)

        # --- Typography Section (For Text/Labels) ---
        self.text_container = QWidget()
        text_layout = QVBoxLayout(self.text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.addWidget(self._create_section_label("タイポグラフィ"))
        
        font_layout = QHBoxLayout()
        self.font_combo = QFontComboBox()
        self.font_combo.currentFontChanged.connect(self._on_font_family_changed)
        font_layout.addWidget(self.font_combo, 2)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(1, 200)
        self.font_size_spin.setSuffix(" pt")
        self.font_size_spin.valueChanged.connect(self._on_font_size_changed)
        font_layout.addWidget(self.font_size_spin, 1)
        text_layout.addLayout(font_layout)

        text_layout.addWidget(QLabel("ラベル / テキスト"))
        self.text_edit = QPlainTextEdit()
        self.text_edit.setFixedHeight(60)
        self.text_edit.textChanged.connect(self._on_text_changed)
        text_layout.addWidget(self.text_edit)
        self.main_layout.addWidget(self.text_container)

        self.main_layout.addStretch()
        
        self.delete_btn = QPushButton("この要素を削除")
        self.delete_btn.setStyleSheet("color: #ff5555; background: transparent; border: 1px solid #ff5555; border-radius: 4px; padding: 5px;")
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        self.main_layout.addWidget(self.delete_btn)
        
        self.setEnabled(False)

    def _create_section_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #888899; font-size: 11px; font-weight: bold; margin-top: 5px;")
        return lbl

    def set_item_data(self, item_id, item_type, text, color_hex, font_family="Arial", font_size=12, line_width=2, opacity=100, fill_color="", center_marker="", start_marker="", end_marker=""):
        self._block_signals = True
        self.current_item_id = item_id
        self.current_item_type = item_type
        
        type_names = {"line": "直線（計測）", "polyline": "直線", "polygon": "矩形", "circle": "円", "text": "テキスト"}
        self.type_title.setText(type_names.get(item_type, "要素"))
        
        # Dynamic visibility
        is_shape = item_type in ["line", "polyline", "polygon", "circle"]
        is_text = item_type == "text"
        has_label = text != ""
        has_fill = item_type in ["polygon", "circle"]
        can_calc = item_type in ["polyline", "polygon", "circle"]
        has_line_markers = item_type == "polyline"
        has_circle_marker = item_type == "circle"
        
        self.line_container.setVisible(is_shape)
        self.fill_container.setVisible(has_fill)
        self.calc_container.setVisible(can_calc)
        self.text_container.setVisible(is_text or has_label)

        self.line_marker_container.setVisible(has_line_markers)
        self.circle_marker_container.setVisible(has_circle_marker)
        self.marker_container.setVisible(has_line_markers or has_circle_marker)
        
        # Update values
        self.text_edit.setPlainText(text)
        self.color_preview.setStyleSheet(f"background-color: {color_hex}; border-radius: 4px;")
        self.color_hex_label.setText(color_hex.upper())
        self.current_color = color_hex
        
        self.font_combo.setCurrentFont(QFont(font_family))
        self.font_size_spin.setValue(font_size)
        self.line_width_spin.setValue(line_width)
        
        self.opacity_slider.setValue(opacity)
        self.opacity_label.setText(f"{opacity}%")
        
        # Fill color
        self.current_fill_color = fill_color
        if fill_color:
            self.fill_color_preview.setStyleSheet(f"background-color: {fill_color}; border-radius: 4px;")
            self.fill_color_hex_label.setText(fill_color.upper())
        else:
            self.fill_color_preview.setStyleSheet("background-color: transparent; border: 1px solid #3d3d5c; border-radius: 4px;")
            self.fill_color_hex_label.setText("なし")

        # Markers
        sm_idx = self._start_marker_values.index(start_marker) if start_marker in self._start_marker_values else 0
        self.start_marker_combo.setCurrentIndex(sm_idx)
        em_idx = self._end_marker_values.index(end_marker) if end_marker in self._end_marker_values else 0
        self.end_marker_combo.setCurrentIndex(em_idx)
        cm_idx = self._center_marker_values.index(center_marker) if center_marker in self._center_marker_values else 0
        self.center_marker_combo.setCurrentIndex(cm_idx)
        
        self.setEnabled(True)
        self._block_signals = False

    def clear_panel(self):
        self._block_signals = True
        self.current_item_id = None
        self.current_item_type = None
        self.type_title.setText("要素を選択してください")
        self.text_edit.setPlainText("")
        self.color_preview.setStyleSheet("background-color: transparent; border: 1px solid #3d3d5c;")
        self.fill_container.setVisible(False)
        self.calc_container.setVisible(False)
        self.marker_container.setVisible(False)
        self.setEnabled(False)
        self._block_signals = False

    def _on_text_changed(self):
        if not self._block_signals and self.current_item_id:
            self.attribute_changed.emit(self.current_item_id, {"text": self.text_edit.toPlainText()})

    def _on_font_family_changed(self, font):
        if not self._block_signals and self.current_item_id:
            self.attribute_changed.emit(self.current_item_id, {"font_family": font.family()})

    def _on_font_size_changed(self, size):
        if not self._block_signals and self.current_item_id:
            self.attribute_changed.emit(self.current_item_id, {"font_size": size})

    def _on_line_width_changed(self, width):
        if not self._block_signals and self.current_item_id:
            self.attribute_changed.emit(self.current_item_id, {"line_width": width})

    def _on_opacity_changed(self, opacity):
        self.opacity_label.setText(f"{opacity}%")
        if not self._block_signals and self.current_item_id:
            self.attribute_changed.emit(self.current_item_id, {"opacity": opacity})

    def _on_color_clicked(self):
        if not self.current_item_id: return
        color = QColorDialog.getColor(QColor(self.current_color))
        if color.isValid():
            hex_color = color.name()
            self.color_preview.setStyleSheet(f"background-color: {hex_color}; border-radius: 4px;")
            self.color_hex_label.setText(hex_color.upper())
            self.current_color = hex_color
            self.attribute_changed.emit(self.current_item_id, {"color": hex_color})

    def _on_fill_color_clicked(self):
        if not self.current_item_id: return
        initial = QColor(self.current_fill_color) if self.current_fill_color else QColor("#7c4dff")
        color = QColorDialog.getColor(initial)
        if color.isValid():
            hex_color = color.name()
            self.fill_color_preview.setStyleSheet(f"background-color: {hex_color}; border-radius: 4px;")
            self.fill_color_hex_label.setText(hex_color.upper())
            self.current_fill_color = hex_color
            self.attribute_changed.emit(self.current_item_id, {"fill_color": hex_color})

    def _on_fill_color_cleared(self):
        if not self.current_item_id: return
        self.current_fill_color = ""
        self.fill_color_preview.setStyleSheet("background-color: transparent; border: 1px solid #3d3d5c; border-radius: 4px;")
        self.fill_color_hex_label.setText("なし")
        self.attribute_changed.emit(self.current_item_id, {"fill_color": ""})

    def _on_start_marker_changed(self, index):
        if not self._block_signals and self.current_item_id:
            self.attribute_changed.emit(self.current_item_id, {"start_marker": self._start_marker_values[index]})

    def _on_end_marker_changed(self, index):
        if not self._block_signals and self.current_item_id:
            self.attribute_changed.emit(self.current_item_id, {"end_marker": self._end_marker_values[index]})

    def _on_center_marker_changed(self, index):
        if not self._block_signals and self.current_item_id:
            self.attribute_changed.emit(self.current_item_id, {"center_marker": self._center_marker_values[index]})

    def _on_calc_clicked(self):
        if self.current_item_id:
            self.calculate_requested.emit(self.current_item_id)

    def _on_delete_clicked(self):
        if self.current_item_id:
            self.delete_requested.emit(self.current_item_id)
            self.clear_panel()
