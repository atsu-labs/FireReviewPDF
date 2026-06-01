from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QWidget, QSpinBox, 
                                 QPushButton, QDoubleSpinBox, QComboBox, QCheckBox, 
                                 QFontComboBox, QColorDialog, QSlider)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from ..canvas import ToolMode

class ToolOptionsBar(QFrame):
    # Signals to notify the orchestrator (MainWindow/Canvas) about option changes
    line_width_changed = Signal(int)
    shape_color_changed = Signal(str)
    fill_color_changed = Signal(str)
    fill_opacity_changed = Signal(int)
    radius_changed = Signal(float)
    start_marker_changed = Signal(int)
    end_marker_changed = Signal(int)
    center_marker_changed = Signal(int)
    shape_continuous_changed = Signal(bool)
    
    font_changed = Signal(str)
    font_size_changed = Signal(int)
    text_color_changed = Signal(str)
    text_continuous_changed = Signal(bool)
    marker_style_changed = Signal(str)
    marker_continuous_changed = Signal(bool)
    marker_opacity_changed = Signal(int)
    marker_color_changed = Signal(str)
    arc_span_changed = Signal(float)
    arc_radial_line_changed = Signal(bool)


    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ToolOptionsBar")
        self.setMinimumHeight(40)
        
        # State variables
        self.current_line_width = 2
        self.current_shape_color = "#7c4dff"
        self.current_fill_color = "#7c4dff"
        self.current_fill_opacity = 30
        self.current_text_font = "BIZ UDゴシック"
        self.current_text_size = 12
        self.current_text_color = "#ff0000"
        self.current_marker_color = "#ff1744"
        self.unit = "mm"

        self._start_marker_values = ["", "circle", "arrow"]
        self._end_marker_values = ["", "circle", "arrow"]
        self._center_marker_values = ["", "circle", "cross", "x"]

        self._setup_ui()

    def _setup_ui(self):
        o_layout = QHBoxLayout(self)
        o_layout.setContentsMargins(15, 0, 15, 0)

        self.default_opt_label = QLabel("ツールプロパティ: 未選択")
        o_layout.addWidget(self.default_opt_label)
        
        # --- Shape tool options ---
        self.shape_options_widget = QWidget()
        shape_layout = QHBoxLayout(self.shape_options_widget)
        shape_layout.setContentsMargins(0, 0, 0, 0)

        shape_layout.addWidget(QLabel("線の太さ:"))
        self.tool_line_width_spin = QSpinBox()
        self.tool_line_width_spin.setRange(1, 20)
        self.tool_line_width_spin.setValue(self.current_line_width)
        self.tool_line_width_spin.valueChanged.connect(self._on_line_width_changed)
        shape_layout.addWidget(self.tool_line_width_spin)

        shape_layout.addWidget(QLabel("線の色:"))
        self.tool_shape_color_preview = QFrame()
        self.tool_shape_color_preview.setFixedSize(20, 20)
        self.tool_shape_color_preview.setStyleSheet(f"background-color: {self.current_shape_color}; border-radius: 4px;")
        shape_layout.addWidget(self.tool_shape_color_preview)
        
        self.tool_shape_color_btn = QPushButton("変更")
        self.tool_shape_color_btn.clicked.connect(self._on_shape_color_clicked)
        shape_layout.addWidget(self.tool_shape_color_btn)

        # Fill color
        self.tool_fill_container = QWidget()
        fill_layout = QHBoxLayout(self.tool_fill_container)
        fill_layout.setContentsMargins(0, 0, 0, 0)
        fill_layout.addWidget(QLabel("塗りの色:"))
        self.tool_fill_color_preview = QFrame()
        self.tool_fill_color_preview.setFixedSize(20, 20)
        self.tool_fill_color_preview.setStyleSheet(f"background-color: {self.current_fill_color}; border: 1px solid #888; border-radius: 4px;")
        fill_layout.addWidget(self.tool_fill_color_preview)
        
        self.tool_fill_color_btn = QPushButton("変更")
        self.tool_fill_color_btn.clicked.connect(self._on_fill_color_clicked)
        fill_layout.addWidget(self.tool_fill_color_btn)
        
        self.tool_fill_clear_btn = QPushButton("なし")
        self.tool_fill_clear_btn.clicked.connect(self._on_fill_color_cleared)
        fill_layout.addWidget(self.tool_fill_clear_btn)
        
        fill_layout.addWidget(QLabel("不透明度:"))
        self.tool_fill_opacity_spin = QSpinBox()
        self.tool_fill_opacity_spin.setRange(0, 100)
        self.tool_fill_opacity_spin.setValue(self.current_fill_opacity)
        self.tool_fill_opacity_spin.setSuffix("%")
        self.tool_fill_opacity_spin.setFixedWidth(65)
        self.tool_fill_opacity_spin.valueChanged.connect(self._on_fill_opacity_changed)
        fill_layout.addWidget(self.tool_fill_opacity_spin)
        shape_layout.addWidget(self.tool_fill_container)

        # Radius input for calibrated circle tool
        self.tool_radius_container = QWidget()
        radius_layout = QHBoxLayout(self.tool_radius_container)
        radius_layout.setContentsMargins(0, 0, 0, 0)
        radius_layout.addWidget(QLabel("半径:"))
        self.tool_radius_spin = QDoubleSpinBox()
        self._update_radius_spinner_ranges()
        self.tool_radius_spin.valueChanged.connect(self.radius_changed.emit)
        radius_layout.addWidget(self.tool_radius_spin)
        shape_layout.addWidget(self.tool_radius_container)

        # Line endpoint markers (DRAW_LINE only)
        self.tool_line_marker_container = QWidget()
        lm_layout = QHBoxLayout(self.tool_line_marker_container)
        lm_layout.setContentsMargins(0, 0, 0, 0)
        lm_layout.addWidget(QLabel("始点:"))
        self.tool_start_marker_combo = QComboBox()
        self.tool_start_marker_combo.addItems(["なし", "丸", "矢印"])
        self.tool_start_marker_combo.currentIndexChanged.connect(self.start_marker_changed.emit)
        lm_layout.addWidget(self.tool_start_marker_combo)
        lm_layout.addWidget(QLabel("終点:"))
        self.tool_end_marker_combo = QComboBox()
        self.tool_end_marker_combo.addItems(["なし", "丸", "矢印"])
        self.tool_end_marker_combo.currentIndexChanged.connect(self.end_marker_changed.emit)
        lm_layout.addWidget(self.tool_end_marker_combo)
        shape_layout.addWidget(self.tool_line_marker_container)

        # Circle center marker (DRAW_CIRCLE_DRAG only)
        self.tool_circle_marker_container = QWidget()
        cm_layout = QHBoxLayout(self.tool_circle_marker_container)
        cm_layout.setContentsMargins(0, 0, 0, 0)
        cm_layout.addWidget(QLabel("中心点:"))
        self.tool_center_marker_combo = QComboBox()
        self.tool_center_marker_combo.addItems(["なし", "丸", "十字", "バツ"])
        self.tool_center_marker_combo.currentIndexChanged.connect(self.center_marker_changed.emit)
        cm_layout.addWidget(self.tool_center_marker_combo)
        shape_layout.addWidget(self.tool_circle_marker_container)

        # Arc settings (DRAW_ARC only)
        self.tool_arc_settings_container = QWidget()
        arc_layout = QHBoxLayout(self.tool_arc_settings_container)
        arc_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tool_arc_radial_line_check = QCheckBox("距離線を表示")
        self.tool_arc_radial_line_check.setChecked(False)
        self.tool_arc_radial_line_check.setStyleSheet("color: white;")
        self.tool_arc_radial_line_check.toggled.connect(self._on_tool_arc_radial_line_changed)
        arc_layout.addWidget(self.tool_arc_radial_line_check)
        
        arc_layout.addWidget(QLabel(" 角度:"))
        self.tool_arc_span_slider = QSlider(Qt.Horizontal)
        self.tool_arc_span_slider.setRange(1, 360)
        self.tool_arc_span_slider.setValue(30)
        self.tool_arc_span_slider.setFixedWidth(100)
        self.tool_arc_span_slider.valueChanged.connect(self._on_tool_arc_span_slider_changed)
        arc_layout.addWidget(self.tool_arc_span_slider)
        
        self.tool_arc_span_spin = QSpinBox()
        self.tool_arc_span_spin.setRange(1, 360)
        self.tool_arc_span_spin.setValue(30)
        self.tool_arc_span_spin.setSuffix("°")
        self.tool_arc_span_spin.valueChanged.connect(self._on_tool_arc_span_spin_changed)
        arc_layout.addWidget(self.tool_arc_span_spin)
        
        shape_layout.addWidget(self.tool_arc_settings_container)

        # Continuous creation checkbox
        self.tool_shape_continuous_check = QCheckBox("連続作成")
        self.tool_shape_continuous_check.setChecked(False)
        self.tool_shape_continuous_check.setStyleSheet("color: white;")
        self.tool_shape_continuous_check.toggled.connect(self.shape_continuous_changed.emit)
        shape_layout.addWidget(self.tool_shape_continuous_check)

        o_layout.addWidget(self.shape_options_widget)
        self.shape_options_widget.hide()

        # --- Text tool options ---
        self.text_options_widget = QWidget()
        text_layout = QHBoxLayout(self.text_options_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        
        self.font_label = QLabel("フォント:")
        text_layout.addWidget(self.font_label)
        self.font_label.hide()
        
        self.tool_font_combo = QFontComboBox()
        self.tool_font_combo.setCurrentFont(QFont(self.current_text_font))
        self.tool_font_combo.currentFontChanged.connect(self._on_font_changed)
        text_layout.addWidget(self.tool_font_combo)
        self.tool_font_combo.hide()
        
        text_layout.addWidget(QLabel("サイズ:"))
        self.tool_font_size_spin = QSpinBox()
        self.tool_font_size_spin.setRange(1, 200)
        self.tool_font_size_spin.setValue(self.current_text_size)
        self.tool_font_size_spin.valueChanged.connect(self._on_font_size_changed)
        text_layout.addWidget(self.tool_font_size_spin)
        
        text_layout.addWidget(QLabel("色:"))
        self.tool_color_preview = QFrame()
        self.tool_color_preview.setFixedSize(20, 20)
        self.tool_color_preview.setStyleSheet(f"background-color: {self.current_text_color}; border-radius: 4px;")
        text_layout.addWidget(self.tool_color_preview)
        
        self.tool_color_btn = QPushButton("変更")
        self.tool_color_btn.clicked.connect(self._on_text_color_clicked)
        text_layout.addWidget(self.tool_color_btn)
        
        self.tool_continuous_check = QCheckBox("連続入力")
        self.tool_continuous_check.setChecked(False)
        self.tool_continuous_check.setStyleSheet("color: white;")
        self.tool_continuous_check.toggled.connect(self.text_continuous_changed.emit)
        text_layout.addWidget(self.tool_continuous_check)
        
        o_layout.addWidget(self.text_options_widget)
        self.text_options_widget.hide()
        
        # --- Marker tool options ---
        self.marker_options_widget = QWidget()
        marker_layout = QHBoxLayout(self.marker_options_widget)
        marker_layout.setContentsMargins(0, 0, 0, 0)
        
        marker_layout.addWidget(QLabel("種類:"))
        self.tool_marker_style_combo = QComboBox()
        self.tool_marker_style_combo.addItems(["四角形", "チェック"])
        self.tool_marker_style_combo.currentIndexChanged.connect(self._on_marker_style_combo_changed)
        marker_layout.addWidget(self.tool_marker_style_combo)
        
        marker_layout.addWidget(QLabel("色:"))
        self.marker_colors_widget = QWidget()
        colors_layout = QHBoxLayout(self.marker_colors_widget)
        colors_layout.setContentsMargins(0, 0, 0, 0)
        colors_layout.setSpacing(4)
        
        from PySide6.QtWidgets import QButtonGroup
        self.color_group = QButtonGroup(self)
        self.color_group.setExclusive(True)
        self.palette_colors = ["#ff1744", "#2979ff", "#00e676", "#ffd600", "#ff9100", "#f50057", "#d500f9", "#8d6e63", "#00e5ff", "#aeea00"]
        self.color_buttons = []
        
        for i, hex_color in enumerate(self.palette_colors):
            btn = QPushButton()
            btn.setFixedSize(18, 18)
            btn.setCheckable(True)
            if hex_color.lower() == self.current_marker_color.lower():
                btn.setChecked(True)
            btn.setStyleSheet(f"QPushButton {{ background-color: {hex_color}; border-radius: 9px; border: 1px solid #555; }} "
                              f"QPushButton:checked {{ border: 2px solid #ffffff; }}")
            btn.clicked.connect(lambda checked, c=hex_color: self._on_marker_palette_clicked(c))
            colors_layout.addWidget(btn)
            self.color_group.addButton(btn)
            self.color_buttons.append(btn)
            
        marker_layout.addWidget(self.marker_colors_widget)

        marker_layout.addWidget(QLabel("不透明度:"))
        self.tool_marker_opacity_spin = QSpinBox()
        self.tool_marker_opacity_spin.setRange(0, 100)
        self.tool_marker_opacity_spin.setValue(70)
        self.tool_marker_opacity_spin.setSuffix("%")
        self.tool_marker_opacity_spin.setFixedWidth(60)
        self.tool_marker_opacity_spin.valueChanged.connect(self._on_marker_opacity_changed)
        marker_layout.addWidget(self.tool_marker_opacity_spin)
        
        self.tool_marker_continuous_check = QCheckBox("連続作成")
        self.tool_marker_continuous_check.setChecked(False)
        self.tool_marker_continuous_check.setStyleSheet("color: white;")
        self.tool_marker_continuous_check.toggled.connect(self.marker_continuous_changed.emit)
        marker_layout.addWidget(self.tool_marker_continuous_check)

        o_layout.addWidget(self.marker_options_widget)
        self.marker_options_widget.hide()
        
        o_layout.addStretch()

    # --- UI updates when tool switches ---
    def update_options_visibility(self, mode, is_page_calibrated):
        is_shape_tool = mode in [ToolMode.DRAW_LINE, ToolMode.POLYGON_AREA, ToolMode.DRAW_CIRCLE_DRAG, ToolMode.DRAW_ARC]
        has_fill = mode in [ToolMode.POLYGON_AREA, ToolMode.DRAW_CIRCLE_DRAG]
        has_radius = mode == ToolMode.DRAW_CIRCLE_DRAG and is_page_calibrated
        has_line_markers = mode == ToolMode.DRAW_LINE
        has_circle_marker = mode in [ToolMode.DRAW_CIRCLE_DRAG, ToolMode.DRAW_ARC]
        has_arc_settings = mode == ToolMode.DRAW_ARC

        if mode in [ToolMode.TEXT, ToolMode.DRAW_LEGEND]:
            self.default_opt_label.hide()
            self.shape_options_widget.hide()
            self.marker_options_widget.hide()
            self.tool_continuous_check.setVisible(mode == ToolMode.TEXT)
            self.text_options_widget.show()
        elif mode == ToolMode.DRAW_MARKER:
            self.default_opt_label.hide()
            self.shape_options_widget.hide()
            self.text_options_widget.hide()
            self.marker_options_widget.show()
        elif is_shape_tool:
            self.default_opt_label.hide()
            self.text_options_widget.hide()
            self.marker_options_widget.hide()
            self.tool_fill_container.setVisible(has_fill)
            self.tool_radius_container.setVisible(has_radius)
            self.tool_line_marker_container.setVisible(has_line_markers)
            self.tool_circle_marker_container.setVisible(has_circle_marker)
            self.tool_arc_settings_container.setVisible(has_arc_settings)
            self.shape_options_widget.show()
        else:
            self.default_opt_label.show()
            self.shape_options_widget.hide()
            self.text_options_widget.hide()
            self.marker_options_widget.hide()

    def apply_unit_change(self, new_unit, old_unit):
        self.unit = new_unit
        current_val = self.tool_radius_spin.value()
        
        if old_unit == 'mm' and new_unit == 'm':
            new_radius_val = current_val / 1000.0
        elif old_unit == 'm' and new_unit == 'mm':
            new_radius_val = current_val * 1000.0
        else:
            new_radius_val = current_val

        self._update_radius_spinner_ranges()
        self.tool_radius_spin.blockSignals(True)
        self.tool_radius_spin.setValue(new_radius_val)
        self.tool_radius_spin.blockSignals(False)

    def _update_radius_spinner_ranges(self):
        if self.unit == 'm':
            self.tool_radius_spin.setRange(0.001, 1000)
            self.tool_radius_spin.setDecimals(3)
            self.tool_radius_spin.setSuffix(" m")
            self.tool_radius_spin.setValue(15.0)
        else:
            self.tool_radius_spin.setRange(0.1, 1000000)
            self.tool_radius_spin.setDecimals(1)
            self.tool_radius_spin.setSuffix(" mm")
            self.tool_radius_spin.setValue(15000.0)

    # --- Option Change Handlers ---
    def _on_line_width_changed(self, width):
        self.current_line_width = width
        self.line_width_changed.emit(width)

    def _on_shape_color_clicked(self):
        color = QColorDialog.getColor(QColor(self.current_shape_color), self)
        if color.isValid():
            self.current_shape_color = color.name()
            self.tool_shape_color_preview.setStyleSheet(f"background-color: {self.current_shape_color}; border-radius: 4px;")
            self._update_fill_preview()
            self.shape_color_changed.emit(self.current_shape_color)

    def _on_fill_color_clicked(self):
        initial = QColor(self.current_fill_color) if self.current_fill_color else QColor(self.current_shape_color)
        color = QColorDialog.getColor(initial, self)
        if color.isValid():
            self.current_fill_color = color.name()
            if self.tool_fill_opacity_spin.value() == 0:
                self.tool_fill_opacity_spin.setValue(30)
                self.current_fill_opacity = 30
            else:
                self.current_fill_opacity = self.tool_fill_opacity_spin.value()
            self._update_fill_preview()
            self.fill_color_changed.emit(self.current_fill_color)
            self.fill_opacity_changed.emit(self.current_fill_opacity)

    def _on_fill_color_cleared(self):
        self.current_fill_color = ""
        self.current_fill_opacity = 0
        self.tool_fill_opacity_spin.setValue(0)
        self._update_fill_preview()
        self.fill_color_changed.emit("")
        self.fill_opacity_changed.emit(0)

    def _on_fill_opacity_changed(self, value):
        self.current_fill_opacity = value
        self._update_fill_preview()
        self.fill_opacity_changed.emit(value)

    def _update_fill_preview(self):
        if self.current_fill_color:
            self.tool_fill_color_preview.setStyleSheet(f"background-color: {self.current_fill_color}; border: 1px solid #888; border-radius: 4px;")
        elif self.current_fill_opacity > 0:
            self.tool_fill_color_preview.setStyleSheet(f"background-color: {self.current_shape_color}; border: 2px dashed #888; border-radius: 4px;")
        else:
            self.tool_fill_color_preview.setStyleSheet("background-color: transparent; border: 1px solid #888; border-radius: 4px;")

    def _on_font_changed(self, font):
        self.current_text_font = font.family()
        self.font_changed.emit(self.current_text_font)

    def _on_font_size_changed(self, size):
        self.current_text_size = size
        self.font_size_changed.emit(size)

    def _on_text_color_clicked(self):
        color = QColorDialog.getColor(QColor(self.current_text_color), self)
        if color.isValid():
            self.current_text_color = color.name()
            self.tool_color_preview.setStyleSheet(f"background-color: {self.current_text_color}; border-radius: 4px;")
            self.text_color_changed.emit(self.current_text_color)

    def _on_marker_style_combo_changed(self, index):
        style = "square" if index == 0 else "check"
        self.marker_style_changed.emit(style)

    def _on_marker_palette_clicked(self, hex_color):
        self.current_marker_color = hex_color
        # パレットの選択状態を視覚的に強調するため、丸ボタンの境界線をすべて更新
        for btn, c in zip(self.color_buttons, self.palette_colors):
            btn.setStyleSheet(f"QPushButton {{ background-color: {c}; border-radius: 9px; border: 1px solid #555; }} "
                              f"QPushButton:checked {{ border: 2px solid #ffffff; }}")
        self.marker_color_changed.emit(hex_color)

    def _on_marker_opacity_changed(self, value):
        self.marker_opacity_changed.emit(value)

    def _on_tool_arc_radial_line_changed(self, checked):
        self.arc_radial_line_changed.emit(checked)
        
    def _on_tool_arc_span_slider_changed(self, val):
        self.tool_arc_span_spin.blockSignals(True)
        self.tool_arc_span_spin.setValue(val)
        self.tool_arc_span_spin.blockSignals(False)
        self.arc_span_changed.emit(float(val))
        
    def _on_tool_arc_span_spin_changed(self, val):
        self.tool_arc_span_slider.blockSignals(True)
        self.tool_arc_span_slider.setValue(val)
        self.tool_arc_span_slider.blockSignals(False)
        self.arc_span_changed.emit(float(val))

