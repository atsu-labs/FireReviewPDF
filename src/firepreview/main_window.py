import os
import math
from PySide6.QtWidgets import (QMainWindow, QFileDialog, 
                             QLabel, QHBoxLayout, QWidget, QVBoxLayout, 
                             QInputDialog, QMessageBox, QPushButton, 
                             QFrame, QSpacerItem, QSizePolicy, QFontComboBox, QSpinBox, QDoubleSpinBox, QColorDialog, QCheckBox, QComboBox,
                             QDialog, QDialogButtonBox, QMenu)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QColor, QFont
import qtawesome as qta

from .services.pdf_exporter import export_pdf_document
from .services.pdf_handler import PDFHandler
from .services.project_store import load_project as load_project_file, save_project as save_project_file
from .ui.canvas import PDFCanvas, ToolMode
from .models import DrawingModel, Annotation
from .ui.panels.property_panel import PropertyPanel
from .ui.panels.navigator_panel import NavigatorPanel
from .ui.styles import GLOBAL_STYLE

class MainWindow(QMainWindow):
    # PDF描画解像度（pdf_handler.get_page_pixmap と合わせる）
    PDF_RENDER_DPI = 150
    # 縮尺比率を整数表示に丸める際の許容差（例: 100.03 -> 1/100）
    SCALE_RATIO_ROUNDING_TOLERANCE = 0.05
    # 表示倍率を整数表示に丸める際の許容差（±0.5%以内なら整数表示）
    ZOOM_LABEL_ROUNDING_TOLERANCE = 0.05
    FIXED_CIRCLE_RADIUS_MM = 15000

    def __init__(self):
        super().__init__()
        self.setWindowTitle("FirePreview")
        self.resize(1400, 900)

        self.pdf_handler = PDFHandler()
        self.model = DrawingModel()
        self.current_page = 0  # 内部ページ番号は0始まり
        
        self.current_text_font = "Arial"
        self.current_text_size = 12
        self.current_text_color = "#ff0000"

        # Shape tool defaults
        self.current_shape_color = "#7c4dff"
        self.current_fill_color = "#7c4dff"  # デフォルトは線と同色
        self.current_fill_opacity = 30  # デフォルトは線と同じ色・30%
        self.current_line_width = 2
        self.current_start_marker = ""
        self.current_end_marker = ""
        self.current_center_marker = ""
        self._start_marker_values = ["", "circle", "arrow"]
        self._end_marker_values = ["", "circle", "arrow"]
        self._center_marker_values = ["", "circle", "cross", "x"]

        self.setup_ui()
        self._setup_menus()
        self.apply_styles()

    def _setup_menus(self):
        menubar = self.menuBar()
        # Ensure menubar style matches dark theme
        menubar.setStyleSheet("QMenuBar { background-color: #151521; color: #ffffff; border-bottom: 1px solid #333344; } QMenuBar::item:selected { background-color: #2a2a3d; }")
        
        file_menu = menubar.addMenu("ファイル")
        
        open_action = QAction("PDF図面を開く", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_pdf)
        file_menu.addAction(open_action)

        swap_action = QAction("背景PDFを差し替え", self)
        swap_action.triggered.connect(self.swap_pdf)
        file_menu.addAction(swap_action)

        file_menu.addSeparator()

        save_action = QAction("プロジェクトを保存", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)

        load_action = QAction("プロジェクトを読み込み", self)
        load_action.setShortcut("Ctrl+L")
        load_action.triggered.connect(self.load_project)
        file_menu.addAction(load_action)

        file_menu.addSeparator()

        export_action = QAction("PDFを書き出し", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_pdf)
        file_menu.addAction(export_action)

    def setup_ui(self):
        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. Header
        self._setup_header()

        # 2. Main Tool Bar
        self._setup_toolbar()

        # 3. Tool Options Bar
        self._setup_options_bar()

        # 4. Content Area (Navigator | Canvas | Property)
        content_area = QHBoxLayout()
        content_area.setSpacing(0)

        # Navigator (Left)
        self.navigator = NavigatorPanel()
        self.navigator.setFixedWidth(220)
        self.navigator.page_changed.connect(self.go_to_page)
        content_area.addWidget(self.navigator)

        # Canvas (Center)
        self.canvas = PDFCanvas()
        self.canvas.setStyleSheet("background-color: #0f0f1a; border: none;")
        self.canvas.calibration_points_selected.connect(self.on_calibration_selected)
        self.canvas.measurement_complete.connect(self.on_measurement_complete)
        self.canvas.polygon_complete.connect(self.on_polygon_complete)
        self.canvas.point_selected.connect(self.on_point_selected)
        self.canvas.polyline_complete.connect(self.on_polyline_complete)
        self.canvas.circle_drag_complete.connect(self.on_circle_drag_complete)
        self.canvas.item_selected.connect(self.on_item_selected)
        self.canvas.selection_cleared.connect(self.on_selection_cleared)
        self.canvas.item_moved.connect(self.on_item_moved)
        self.canvas.text_editing_finished.connect(self.on_text_editing_finished)
        self.canvas.request_tool_change.connect(self.on_request_tool_change)
        self.canvas.existing_text_edited.connect(self.on_existing_text_edited)
        self.canvas.zoom_changed.connect(self._update_zoom_label)
        content_area.addWidget(self.canvas)

        # Property Panel (Right)
        self.prop_panel = PropertyPanel()
        self.prop_panel.setFixedWidth(280)
        self.prop_panel.attribute_changed.connect(self.on_property_changed)
        self.prop_panel.delete_requested.connect(self.on_delete_item)
        self.prop_panel.calculate_requested.connect(self.on_calculate_requested)
        content_area.addWidget(self.prop_panel)

        self.main_layout.addLayout(content_area)

        # 5. Status Bar
        self._setup_status_bar()

    def _setup_header(self):
        header = QFrame()
        header.setObjectName("MainHeader")
        header.setFixedHeight(50)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(15, 0, 15, 0)

        title = QLabel("FirePreview")
        title.setStyleSheet("font-weight: bold; font-size: 18px; color: #ffffff;")
        h_layout.addWidget(title)

        h_layout.addSpacing(20)
        
        btn_files = QPushButton(" すべてのファイル")
        btn_files.setIcon(qta.icon('fa5s.folder', color='white'))
        btn_save = QPushButton(" 保存")
        btn_save.setIcon(qta.icon('fa5s.save', color='white'))
        h_layout.addWidget(btn_files)
        h_layout.addWidget(btn_save)

        h_layout.addStretch()

        btn_share = QPushButton()
        btn_share.setIcon(qta.icon('fa5s.share-square', color='white'))
        self.btn_settings = QPushButton()
        self.btn_settings.setIcon(qta.icon('fa5s.cog', color='white'))
        self.btn_settings.clicked.connect(self._on_settings_clicked)
        user_info = QLabel(" 👤 ユーザー名")
        h_layout.addWidget(btn_share)
        h_layout.addWidget(self.btn_settings)
        h_layout.addWidget(user_info)

        self.main_layout.addWidget(header)

    def _setup_toolbar(self):
        toolbar = QFrame()
        toolbar.setObjectName("ToolBar")
        t_layout = QHBoxLayout(toolbar)
        t_layout.setContentsMargins(10, 0, 10, 0)

        tools = [
            ('fa5s.mouse-pointer', "選択", ToolMode.SELECT),
            ('fa5s.hand-paper', "パン", ToolMode.NONE),
            ('fa5s.pencil-alt', "直線（折れ線）", ToolMode.DRAW_LINE),
            ('fa5s.square', "矩形", ToolMode.POLYGON_AREA),
            ('fa5s.circle', "円", ToolMode.DRAW_CIRCLE_DRAG),
            ('fa5s.font', "テキスト", ToolMode.TEXT),
            ('fa5s.ruler', "計測ライン", ToolMode.MEASURE_LINE),
            ('fa5s.bullseye', "15m円（計測）", ToolMode.CIRCLE_FIXED),
            ('fa5s.drafting-compass', "キャリブレーション", ToolMode.CALIBRATE),
        ]

        self.tool_btns = []
        for icon_name, tip, mode in tools:
            btn = QPushButton()
            btn.setIcon(qta.icon(icon_name, color='white'))
            btn.setIconSize(QSize(20, 20))
            btn.setObjectName("ToolBtn")
            btn.setProperty("tool_mode", mode)
            btn.setToolTip(tip)
            btn.setFixedSize(40, 40)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, m=mode, b=btn: self.set_tool(m, b))
            t_layout.addWidget(btn)
            self.tool_btns.append(btn)

        t_layout.addStretch()
        
        self.zoom_label = QLabel("表示倍率: 100%")
        t_layout.addWidget(self.zoom_label)
        self.scale_status_label = QLabel("スケール: 未キャリブレーション")
        t_layout.addWidget(self.scale_status_label)
        self.pdf_size_label = QLabel(PDFHandler.SIZE_LABEL_UNKNOWN)
        t_layout.addWidget(self.pdf_size_label)

        self.main_layout.addWidget(toolbar)

    def _setup_options_bar(self):
        self.options_bar = QFrame()
        self.options_bar.setObjectName("ToolOptionsBar")
        self.options_bar.setMinimumHeight(40)
        o_layout = QHBoxLayout(self.options_bar)
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
        self.tool_line_width_spin.valueChanged.connect(self._on_tool_line_width_changed)
        shape_layout.addWidget(self.tool_line_width_spin)

        shape_layout.addWidget(QLabel("線の色:"))
        self.tool_shape_color_preview = QFrame()
        self.tool_shape_color_preview.setFixedSize(20, 20)
        self.tool_shape_color_preview.setStyleSheet(f"background-color: {self.current_shape_color}; border-radius: 4px;")
        shape_layout.addWidget(self.tool_shape_color_preview)
        self.tool_shape_color_btn = QPushButton("変更")
        self.tool_shape_color_btn.clicked.connect(self._on_tool_shape_color_clicked)
        shape_layout.addWidget(self.tool_shape_color_btn)

        # Fill color (shown for polygon and circle tools)
        self.tool_fill_container = QWidget()
        fill_layout = QHBoxLayout(self.tool_fill_container)
        fill_layout.setContentsMargins(0, 0, 0, 0)
        fill_layout.addWidget(QLabel("塗りの色:"))
        self.tool_fill_color_preview = QFrame()
        self.tool_fill_color_preview.setFixedSize(20, 20)
        self.tool_fill_color_preview.setStyleSheet(f"background-color: {self.current_fill_color}; border: 1px solid #888; border-radius: 4px;")
        fill_layout.addWidget(self.tool_fill_color_preview)
        self.tool_fill_color_btn = QPushButton("変更")
        self.tool_fill_color_btn.clicked.connect(self._on_tool_fill_color_clicked)
        fill_layout.addWidget(self.tool_fill_color_btn)
        self.tool_fill_clear_btn = QPushButton("なし")
        self.tool_fill_clear_btn.clicked.connect(self._on_tool_fill_color_cleared)
        fill_layout.addWidget(self.tool_fill_clear_btn)
        fill_layout.addWidget(QLabel("不透明度:"))
        self.tool_fill_opacity_spin = QSpinBox()
        self.tool_fill_opacity_spin.setRange(0, 100)
        self.tool_fill_opacity_spin.setValue(30)
        self.tool_fill_opacity_spin.setSuffix("%")
        self.tool_fill_opacity_spin.setFixedWidth(65)
        self.tool_fill_opacity_spin.valueChanged.connect(self._on_tool_fill_opacity_changed)
        fill_layout.addWidget(self.tool_fill_opacity_spin)
        shape_layout.addWidget(self.tool_fill_container)

        # Radius input for calibrated circle tool
        self.tool_radius_container = QWidget()
        radius_layout = QHBoxLayout(self.tool_radius_container)
        radius_layout.setContentsMargins(0, 0, 0, 0)
        radius_layout.addWidget(QLabel("半径:"))
        self.tool_radius_spin = QDoubleSpinBox()
        if self.model.unit == 'm':
            self.tool_radius_spin.setRange(0.001, 1000)
            self.tool_radius_spin.setDecimals(3)
            self.tool_radius_spin.setValue(15.0)
            self.tool_radius_spin.setSuffix(" m")
        else:
            self.tool_radius_spin.setRange(0.1, 1000000)
            self.tool_radius_spin.setDecimals(1)
            self.tool_radius_spin.setValue(15000.0)
            self.tool_radius_spin.setSuffix(" mm")
        radius_layout.addWidget(self.tool_radius_spin)
        shape_layout.addWidget(self.tool_radius_container)

        # Line endpoint markers (shown for DRAW_LINE only)
        self.tool_line_marker_container = QWidget()
        lm_layout = QHBoxLayout(self.tool_line_marker_container)
        lm_layout.setContentsMargins(0, 0, 0, 0)
        lm_layout.addWidget(QLabel("始点:"))
        self.tool_start_marker_combo = QComboBox()
        self.tool_start_marker_combo.addItems(["なし", "丸", "矢印"])
        self.tool_start_marker_combo.currentIndexChanged.connect(self._on_tool_start_marker_changed)
        lm_layout.addWidget(self.tool_start_marker_combo)
        lm_layout.addWidget(QLabel("終点:"))
        self.tool_end_marker_combo = QComboBox()
        self.tool_end_marker_combo.addItems(["なし", "丸", "矢印"])
        self.tool_end_marker_combo.currentIndexChanged.connect(self._on_tool_end_marker_changed)
        lm_layout.addWidget(self.tool_end_marker_combo)
        shape_layout.addWidget(self.tool_line_marker_container)

        # Circle center marker (shown for DRAW_CIRCLE_DRAG only)
        self.tool_circle_marker_container = QWidget()
        cm_layout = QHBoxLayout(self.tool_circle_marker_container)
        cm_layout.setContentsMargins(0, 0, 0, 0)
        cm_layout.addWidget(QLabel("中心点:"))
        self.tool_center_marker_combo = QComboBox()
        self.tool_center_marker_combo.addItems(["なし", "丸", "十字", "バツ"])
        self.tool_center_marker_combo.currentIndexChanged.connect(self._on_tool_center_marker_changed)
        cm_layout.addWidget(self.tool_center_marker_combo)
        shape_layout.addWidget(self.tool_circle_marker_container)

        # Continuous creation checkbox (all shape tools)
        self.tool_shape_continuous_check = QCheckBox("連続作成")
        self.tool_shape_continuous_check.setChecked(False)
        self.tool_shape_continuous_check.setStyleSheet("color: white;")
        self.tool_shape_continuous_check.toggled.connect(self._on_tool_shape_continuous_changed)
        shape_layout.addWidget(self.tool_shape_continuous_check)

        o_layout.addWidget(self.shape_options_widget)
        self.shape_options_widget.hide()

        # --- Text tool options ---
        self.text_options_widget = QWidget()
        text_layout = QHBoxLayout(self.text_options_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        
        text_layout.addWidget(QLabel("フォント:"))
        self.tool_font_combo = QFontComboBox()
        self.tool_font_combo.setCurrentFont(QFont(self.current_text_font))
        self.tool_font_combo.currentFontChanged.connect(self._on_tool_font_changed)
        text_layout.addWidget(self.tool_font_combo)
        
        text_layout.addWidget(QLabel("サイズ:"))
        self.tool_font_size_spin = QSpinBox()
        self.tool_font_size_spin.setRange(1, 200)
        self.tool_font_size_spin.setValue(self.current_text_size)
        self.tool_font_size_spin.valueChanged.connect(self._on_tool_font_size_changed)
        text_layout.addWidget(self.tool_font_size_spin)
        
        text_layout.addWidget(QLabel("色:"))
        self.tool_color_preview = QFrame()
        self.tool_color_preview.setFixedSize(20, 20)
        self.tool_color_preview.setStyleSheet(f"background-color: {self.current_text_color}; border-radius: 4px;")
        text_layout.addWidget(self.tool_color_preview)
        
        self.tool_color_btn = QPushButton("変更")
        self.tool_color_btn.clicked.connect(self._on_tool_color_clicked)
        text_layout.addWidget(self.tool_color_btn)
        
        self.tool_continuous_check = QCheckBox("連続入力")
        self.tool_continuous_check.setChecked(False)
        self.tool_continuous_check.setStyleSheet("color: white;")
        self.tool_continuous_check.toggled.connect(self._on_tool_continuous_changed)
        text_layout.addWidget(self.tool_continuous_check)
        
        o_layout.addWidget(self.text_options_widget)
        self.text_options_widget.hide()
        
        o_layout.addStretch()
        self.main_layout.addWidget(self.options_bar)

    def _on_tool_continuous_changed(self, checked):
        if self.canvas.tool_mode == ToolMode.TEXT:
            self.canvas.set_text_defaults(self.current_text_font, self.current_text_size, self.current_text_color, checked)

    def _on_tool_shape_continuous_changed(self, checked):
        self.canvas.set_shape_continuous(checked)

    def _on_tool_start_marker_changed(self, index):
        self.current_start_marker = self._start_marker_values[index]

    def _on_tool_end_marker_changed(self, index):
        self.current_end_marker = self._end_marker_values[index]

    def _on_tool_center_marker_changed(self, index):
        self.current_center_marker = self._center_marker_values[index]

    def _on_tool_line_width_changed(self, width):
        self.current_line_width = width
        self._update_canvas_shape_defaults()

    def _on_tool_shape_color_clicked(self):
        color = QColorDialog.getColor(QColor(self.current_shape_color))
        if color.isValid():
            self.current_shape_color = color.name()
            self.tool_shape_color_preview.setStyleSheet(f"background-color: {self.current_shape_color}; border-radius: 4px;")
            self._update_fill_preview()  # 塗りが「線と同色」のときプレビューも追従
            self._update_canvas_shape_defaults()

    def _on_tool_fill_color_clicked(self):
        initial = QColor(self.current_fill_color) if self.current_fill_color else QColor(self.current_shape_color)
        color = QColorDialog.getColor(initial)
        if color.isValid():
            self.current_fill_color = color.name()
            if self.tool_fill_opacity_spin.value() == 0:
                self.tool_fill_opacity_spin.setValue(30)
                self.current_fill_opacity = 30
            else:
                self.current_fill_opacity = self.tool_fill_opacity_spin.value()
            self._update_fill_preview()
            self._update_canvas_shape_defaults()

    def _on_tool_fill_color_cleared(self):
        self.current_fill_color = ""
        self.current_fill_opacity = 0
        self.tool_fill_opacity_spin.setValue(0)
        self._update_fill_preview()
        self._update_canvas_shape_defaults()

    def _on_tool_fill_opacity_changed(self, value):
        self.current_fill_opacity = value
        self._update_fill_preview()

    def _update_fill_preview(self):
        if self.current_fill_color:
            self.tool_fill_color_preview.setStyleSheet(f"background-color: {self.current_fill_color}; border: 1px solid #888; border-radius: 4px;")
        elif self.current_fill_opacity > 0:
            self.tool_fill_color_preview.setStyleSheet(f"background-color: {self.current_shape_color}; border: 2px dashed #888; border-radius: 4px;")
        else:
            self.tool_fill_color_preview.setStyleSheet("background-color: transparent; border: 1px solid #888; border-radius: 4px;")

    def _update_canvas_shape_defaults(self):
        self.canvas.set_shape_defaults(self.current_shape_color, self.current_line_width, self.current_fill_color)

    def _on_tool_font_changed(self, font):
        self.current_text_font = font.family()

    def _on_tool_font_size_changed(self, size):
        self.current_text_size = size

    def _on_tool_color_clicked(self):
        color = QColorDialog.getColor(QColor(self.current_text_color))
        if color.isValid():
            self.current_text_color = color.name()
            self.tool_color_preview.setStyleSheet(f"background-color: {self.current_text_color}; border-radius: 4px;")

    # --- 単位フォーマットヘルパー ---
    def _format_distance(self, value_mm):
        if self.model.unit == 'm':
            return f"{value_mm / 1000:.3f} m"
        return f"{value_mm:.1f} mm"

    def _format_area(self, value_mm2):
        if self.model.unit == 'm':
            return f"{value_mm2 / 1_000_000:.2f} m²"
        return f"{value_mm2:.1f} mm²"

    def _format_radius(self, value_mm):
        if self.model.unit == 'm':
            return f"R={value_mm / 1000:.3f} m"
        return f"R={value_mm:.1f} mm"

    def _get_scale_factor_for_page(self, page_num):
        return self.model.get_scale_factor(page_num)

    def _get_current_scale_factor(self):
        return self._get_scale_factor_for_page(self.current_page)

    def _is_page_calibrated(self, page_num):
        return self.model.is_page_calibrated(page_num)

    def _is_current_page_calibrated(self):
        return self._is_page_calibrated(self.current_page)

    def _format_scale_ratio(self, scale_factor):
        """ページの mm/px から「1/N」形式の縮尺文字列を返す（無効値は空文字）。"""
        # PDF描画DPIに対する1pxあたりの実寸(mm)を求める
        # 25.4 mm/inch は 1インチをミリメートルへ変換する係数
        mm_per_pixel_on_pdf = 25.4 / self.PDF_RENDER_DPI
        if scale_factor <= 0 or mm_per_pixel_on_pdf <= 0:
            return ""
        ratio = scale_factor / mm_per_pixel_on_pdf
        rounded = round(ratio)
        if abs(ratio - rounded) < self.SCALE_RATIO_ROUNDING_TOLERANCE:
            return f"1/{rounded}"
        return f"1/{ratio:.1f}"

    def _update_scale_status_label(self):
        if self._is_current_page_calibrated():
            ratio_text = self._format_scale_ratio(self._get_current_scale_factor())
            self.scale_status_label.setText(f"スケール: {ratio_text}" if ratio_text else "スケール: 未キャリブレーション")
        else:
            self.scale_status_label.setText("スケール: 未キャリブレーション")

    def _update_pdf_size_label(self):
        """現在ページのPDFサイズ表示を更新する。"""
        if not self.pdf_handler:
            self.pdf_size_label.setText(PDFHandler.SIZE_LABEL_UNKNOWN)
            return
        self.pdf_size_label.setText(self.pdf_handler.get_page_size_label(self.current_page))

    def _update_zoom_label(self, zoom_percent):
        """キャンバス拡大率(%)を受け取り、右上の表示倍率ラベルを更新する。"""
        prefix = "表示倍率: "
        if zoom_percent <= 0:
            self.zoom_label.setText(f"{prefix}---")
            return
        rounded = round(zoom_percent)
        if abs(zoom_percent - rounded) <= self.ZOOM_LABEL_ROUNDING_TOLERANCE:
            text = f"{rounded}%"
        else:
            text = f"{zoom_percent:.1f}%"
        self.zoom_label.setText(f"{prefix}{text}")

    # --- 単位設定UI ---
    def _on_settings_clicked(self):
        menu = QMenu(self)
        unit_action = menu.addAction("単位設定")
        unit_action.triggered.connect(self._open_unit_dialog)
        menu.exec(self.btn_settings.mapToGlobal(self.btn_settings.rect().bottomLeft()))

    def _open_unit_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("単位設定")
        dialog.setFixedSize(320, 220)
        dialog.setStyleSheet("QDialog { background-color: #1e1e2e; } QLabel { color: #ffffff; border: none; }")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title = QLabel("表示単位を選択してください")
        title.setStyleSheet("font-size: 12px; color: #aaaacc; border: none;")
        layout.addWidget(title)

        selected = [self.model.unit]

        def _card_style(active):
            border = "#7c4dff" if active else "#333355"
            bg = "#2e2e45" if active else "#1e1e2e"
            return (f"QFrame {{ background-color: {bg}; border: 2px solid {border};"
                    f" border-radius: 8px; }}")

        def _make_card(unit_key, label, desc):
            frame = QFrame()
            frame.setStyleSheet(_card_style(self.model.unit == unit_key))
            frame.setCursor(Qt.PointingHandCursor)
            row = QHBoxLayout(frame)
            row.setContentsMargins(14, 10, 14, 10)
            col = QVBoxLayout()
            lbl_main = QLabel(label)
            lbl_main.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff; border: none;")
            lbl_desc = QLabel(desc)
            lbl_desc.setStyleSheet("font-size: 11px; color: #888899; border: none;")
            col.addWidget(lbl_main)
            col.addWidget(lbl_desc)
            row.addLayout(col)
            row.addStretch()
            check = QLabel("✓" if self.model.unit == unit_key else "")
            check.setStyleSheet("font-size: 18px; font-weight: bold; color: #7c4dff; border: none;")
            row.addWidget(check)
            return frame, check

        m_card, m_check = _make_card('m', 'm', 'メートル')
        mm_card, mm_check = _make_card('mm', 'mm', 'ミリメートル')

        def _select(unit_key):
            selected[0] = unit_key
            m_card.setStyleSheet(_card_style(unit_key == 'm'))
            m_check.setText("✓" if unit_key == 'm' else "")
            mm_card.setStyleSheet(_card_style(unit_key == 'mm'))
            mm_check.setText("✓" if unit_key == 'mm' else "")

        m_card.mousePressEvent = lambda e: _select('m')
        mm_card.mousePressEvent = lambda e: _select('mm')

        layout.addWidget(m_card)
        layout.addWidget(mm_card)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setStyleSheet(
            "QPushButton { background-color: #2a2a3d; color: #ffffff; border: 1px solid #555566;"
            " border-radius: 4px; padding: 5px 16px; }"
            "QPushButton:hover { background-color: #7c4dff; border-color: #7c4dff; }"
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.Accepted:
            new_unit = selected[0]
            if new_unit != self.model.unit:
                self._apply_unit_change(new_unit)

    def _apply_unit_change(self, new_unit):
        old_unit = self.model.unit
        self.model.unit = new_unit

        # 半径スピナーの値を単位変換して更新
        current_val = self.tool_radius_spin.value()
        if old_unit == 'mm' and new_unit == 'm':
            new_radius_val = current_val / 1000.0
        elif old_unit == 'm' and new_unit == 'mm':
            new_radius_val = current_val * 1000.0
        else:
            new_radius_val = current_val

        if new_unit == 'm':
            self.tool_radius_spin.setRange(0.001, 1000)
            self.tool_radius_spin.setDecimals(3)
            self.tool_radius_spin.setSuffix(" m")
            self.tool_radius_spin.setValue(new_radius_val)
        else:
            self.tool_radius_spin.setRange(0.1, 1000000)
            self.tool_radius_spin.setDecimals(1)
            self.tool_radius_spin.setSuffix(" mm")
            self.tool_radius_spin.setValue(new_radius_val)

        # 計算済みアノテーションのテキストを再フォーマット
        for ann in self.model.annotations:
            if ann.real_value > 0:
                if ann.type in ("line", "polyline"):
                    ann.text = self._format_distance(ann.real_value)
                    self.canvas.update_item_properties(ann.id, {"text": ann.text})
                elif ann.type == "polygon":
                    ann.text = self._format_area(ann.real_value)
                    self.canvas.update_item_properties(ann.id, {"text": ann.text})
                elif ann.type == "circle" and ann.text != "R=15m":
                    ann.text = self._format_radius(ann.real_value)
                    self.canvas.update_item_properties(ann.id, {"text": ann.text})

    def _setup_status_bar(self):
        status = QFrame()
        status.setFixedHeight(25)
        status.setStyleSheet("background-color: #151521; border-top: 1px solid #333344;")
        s_layout = QHBoxLayout(status)
        s_layout.setContentsMargins(10, 0, 10, 0)
        
        self.coord_label = QLabel("X: 0.0px  Y: 0.0px")
        self.coord_label.setStyleSheet("color: #888899; font-size: 10px;")
        s_layout.addStretch()
        s_layout.addWidget(self.coord_label)
        
        self.main_layout.addWidget(status)

    def apply_styles(self):
        self.setStyleSheet(GLOBAL_STYLE)

    def set_tool(self, mode, active_btn):
        for btn in self.tool_btns:
            btn.setChecked(btn == active_btn)
            btn.setProperty("active", btn == active_btn)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        
        # Only measurement tools (not drawing tools) require calibration
        if mode in [ToolMode.MEASURE_LINE, ToolMode.CIRCLE_FIXED]:
            if not self._is_current_page_calibrated():
                QMessageBox.warning(self, "警告", "先にキャリブレーションを行ってください。")
                active_btn.setChecked(False)
                return

        self.canvas.set_tool_mode(mode)
        
        is_shape_tool = mode in [ToolMode.DRAW_LINE, ToolMode.POLYGON_AREA, ToolMode.DRAW_CIRCLE_DRAG]
        has_fill = mode in [ToolMode.POLYGON_AREA, ToolMode.DRAW_CIRCLE_DRAG]
        has_radius = mode == ToolMode.DRAW_CIRCLE_DRAG and self._is_current_page_calibrated()
        has_line_markers = mode == ToolMode.DRAW_LINE
        has_circle_marker = mode == ToolMode.DRAW_CIRCLE_DRAG

        if mode == ToolMode.TEXT:
            self.default_opt_label.hide()
            self.shape_options_widget.hide()
            self.text_options_widget.show()
            self.canvas.set_text_defaults(self.current_text_font, self.current_text_size, self.current_text_color, self.tool_continuous_check.isChecked())
        elif is_shape_tool:
            self.default_opt_label.hide()
            self.text_options_widget.hide()
            self.tool_fill_container.setVisible(has_fill)
            self.tool_radius_container.setVisible(has_radius)
            self.tool_line_marker_container.setVisible(has_line_markers)
            self.tool_circle_marker_container.setVisible(has_circle_marker)
            self.shape_options_widget.show()
            self._update_canvas_shape_defaults()
            self.canvas.set_shape_continuous(self.tool_shape_continuous_check.isChecked())
        else:
            self.default_opt_label.show()
            self.shape_options_widget.hide()
            self.text_options_widget.hide()

    def go_to_page(self, page_idx):
        self.current_page = page_idx
        self.update_page_view()

    # --- (Delegated Methods from original main.py) ---
    def on_calibration_selected(self, p1, p2):
        unit = self.model.unit
        if unit == 'm':
            label = "実寸法を入力してください (m):"
            default_val, max_val, decimals = 1.0, 1000.0, 3
        else:
            label = "実寸法を入力してください (mm):"
            default_val, max_val, decimals = 1000.0, 1000000.0, 1
        dist_val, ok = QInputDialog.getDouble(self, "キャリブレーション", label, default_val, 0, max_val, decimals)
        if ok:
            dist_mm = dist_val * 1000 if unit == 'm' else dist_val
            if self.model.set_calibration(p1, p2, dist_mm, self.current_page):
                QMessageBox.information(self, "完了", "キャリブレーションが完了しました。")
                self._update_scale_status_label()

    def on_measurement_complete(self, p1, p2):
        # 防御的チェック: ページ切り替え後に未キャリブレーションページへ遷移した場合に備える
        if not self._is_current_page_calibrated():
            QMessageBox.warning(self, "警告", "このページは未キャリブレーションです。")
            return
        dist_mm = self.model.calculate_real_distance(p1, p2, self._get_current_scale_factor())
        text = self._format_distance(dist_mm)
        ann = self._add_to_model("line", [p1, p2], dist_mm, text=text)
        self.canvas.add_line_annotation(p1, p2, text=text, item_id=ann.id, font_family=ann.font_family, font_size=ann.font_size)

    def on_polygon_complete(self, points):
        ann = self._add_to_model("polygon", points, real_value=0.0, text="")
        ann.color = self.current_shape_color
        ann.line_width = self.current_line_width
        ann.fill_color = self.current_fill_color
        ann.fill_opacity = self.current_fill_opacity
        self.canvas.add_polygon_annotation(points, text="", color=ann.color, item_id=ann.id,
                                           font_family=ann.font_family, font_size=ann.font_size,
                                           line_width=ann.line_width, stroke_opacity=ann.stroke_opacity,
                                           fill_opacity=ann.fill_opacity, fill_color=ann.fill_color)

    def on_polyline_complete(self, points):
        ann = self._add_to_model("polyline", points, real_value=0.0, text="")
        ann.color = self.current_shape_color
        ann.line_width = self.current_line_width
        ann.start_marker = self.current_start_marker
        ann.end_marker = self.current_end_marker
        self.canvas.add_polyline_annotation(points, text="", color=ann.color, item_id=ann.id,
                                            font_family=ann.font_family, font_size=ann.font_size,
                                            line_width=ann.line_width,
                                            start_marker=ann.start_marker,
                                            end_marker=ann.end_marker)

    def on_circle_drag_complete(self, center, radius_px):
        import math
        # If radius is ~0 (click without drag) and calibrated, use radius from tool options
        current_scale_factor = self._get_current_scale_factor()
        if radius_px < 3 and self._is_current_page_calibrated() and current_scale_factor > 0:
            if self.model.unit == 'm':
                radius_mm = self.tool_radius_spin.value() * 1000
            else:
                radius_mm = self.tool_radius_spin.value()
            radius_px = radius_mm / current_scale_factor
        ann = self._add_to_model("circle", [center], real_value=0.0, text="")
        ann.color = self.current_shape_color
        ann.line_width = self.current_line_width
        ann.fill_color = self.current_fill_color
        ann.fill_opacity = self.current_fill_opacity
        ann.radius_px = radius_px
        ann.center_marker = self.current_center_marker
        self.canvas.add_circle_annotation(center, radius_px, text="", color=ann.color, item_id=ann.id,
                                          font_family=ann.font_family, font_size=ann.font_size,
                                          line_width=ann.line_width, stroke_opacity=ann.stroke_opacity,
                                          fill_opacity=ann.fill_opacity, fill_color=ann.fill_color,
                                          center_marker=ann.center_marker)

    def on_point_selected(self, pos):
        if self.canvas.tool_mode == ToolMode.CIRCLE_FIXED:
            if not self._is_current_page_calibrated():
                QMessageBox.warning(self, "警告", "このページは未キャリブレーションです。")
                return
            current_scale_factor = self._get_current_scale_factor()
            if current_scale_factor <= 0:
                return
            radius_mm = self.FIXED_CIRCLE_RADIUS_MM
            radius_px = radius_mm / current_scale_factor
            text = "R=15m"
            ann = self._add_to_model("circle", [pos], radius_mm, text=text)
            ann.radius_px = radius_px
            self.canvas.add_circle_annotation(pos, radius_px, text=text, item_id=ann.id, font_family=ann.font_family, font_size=ann.font_size)

    def on_calculate_requested(self, item_id):
        import math
        if not self._is_current_page_calibrated():
            QMessageBox.warning(self, "警告", "キャリブレーションが完了していません。先にキャリブレーションを行ってください。")
            return
        current_scale_factor = self._get_current_scale_factor()
        if current_scale_factor <= 0:
            return
        for ann in self.model.annotations:
            if ann.id == item_id:
                if ann.type == "polyline" and len(ann.points) >= 2:
                    total = sum(
                        math.sqrt((ann.points[i+1].x() - ann.points[i].x())**2 +
                                  (ann.points[i+1].y() - ann.points[i].y())**2)
                        * current_scale_factor
                        for i in range(len(ann.points) - 1)
                    )
                    ann.real_value = total
                    ann.text = self._format_distance(total)
                elif ann.type == "polygon" and len(ann.points) >= 3:
                    area_mm2 = self.model.calculate_real_area(ann.points, current_scale_factor)
                    ann.real_value = area_mm2
                    ann.text = self._format_area(area_mm2)
                elif ann.type == "circle":
                    radius_px = ann.radius_px if ann.radius_px > 0 else (ann.real_value / current_scale_factor if ann.real_value > 0 else 0)
                    radius_mm = radius_px * current_scale_factor
                    ann.real_value = radius_mm
                    ann.text = self._format_radius(radius_mm)
                self.canvas.update_item_properties(item_id, {"text": ann.text})
                # Refresh selection in property panel
                self.prop_panel.set_item_data(ann.id, ann.type, ann.text, ann.color,
                                              ann.font_family, ann.font_size, ann.line_width,
                                              stroke_opacity=ann.stroke_opacity, fill_opacity=ann.fill_opacity,
                                              fill_color=ann.fill_color,
                                              center_marker=ann.center_marker, start_marker=ann.start_marker, end_marker=ann.end_marker)
                break

    def on_request_tool_change(self, mode):
        for btn in self.tool_btns:
            if btn.property("tool_mode") == mode:
                self.set_tool(mode, btn)
                break

    def on_text_editing_finished(self, pos, text, item_id, font_family, font_size, color):
        if not item_id:
            ann = self._add_to_model("text", [pos], text=text)
            ann.font_family = font_family
            ann.font_size = font_size
            ann.color = color
            self.canvas.add_text_annotation(pos, text, item_id=ann.id, font_family=ann.font_family, font_size=ann.font_size, color=ann.color)
        else:
            # Update existing if needed
            pass

    def on_existing_text_edited(self, item_id, new_text):
        for ann in self.model.annotations:
            if ann.id == item_id:
                ann.text = new_text
                break
        
        # If the edited item is currently selected in the property panel, update it there too
        if hasattr(self.prop_panel, 'current_item_id') and self.prop_panel.current_item_id == item_id:
            self.prop_panel._block_signals = True
            if hasattr(self.prop_panel.text_edit, 'setPlainText'):
                self.prop_panel.text_edit.setPlainText(new_text)
            else:
                self.prop_panel.text_edit.setText(new_text)
            self.prop_panel._block_signals = False

    def _add_to_model(self, type, points, real_value=0.0, text=""):
        ann = Annotation(type)
        ann.points = points
        ann.real_value = real_value
        ann.text = text
        ann.page_num = self.current_page
        self.model.annotations.append(ann)
        return ann

    def on_item_selected(self, item_id):
        for ann in self.model.annotations:
            if ann.id == item_id:
                self.prop_panel.set_item_data(ann.id, ann.type, ann.text, ann.color,
                                              ann.font_family, ann.font_size, ann.line_width,
                                              stroke_opacity=ann.stroke_opacity, fill_opacity=ann.fill_opacity,
                                              fill_color=ann.fill_color,
                                              center_marker=ann.center_marker, start_marker=ann.start_marker, end_marker=ann.end_marker)
                break

    def on_selection_cleared(self):
        self.prop_panel.clear_panel()

    def on_property_changed(self, item_id, attrs):
        for ann in self.model.annotations:
            if ann.id == item_id:
                if "text" in attrs: ann.text = attrs["text"]
                if "color" in attrs: ann.color = attrs["color"]
                if "fill_color" in attrs: ann.fill_color = attrs["fill_color"]
                if "font_family" in attrs: ann.font_family = attrs["font_family"]
                if "font_size" in attrs: ann.font_size = attrs["font_size"]
                if "line_width" in attrs: ann.line_width = attrs["line_width"]
                if "stroke_opacity" in attrs: ann.stroke_opacity = attrs["stroke_opacity"]
                if "fill_opacity" in attrs: ann.fill_opacity = attrs["fill_opacity"]
                if "center_marker" in attrs: ann.center_marker = attrs["center_marker"]
                if "start_marker" in attrs: ann.start_marker = attrs["start_marker"]
                if "end_marker" in attrs: ann.end_marker = attrs["end_marker"]
                # When any marker changed, always include ALL current marker values so
                # canvas can redraw both endpoints without losing the unchanged one
                if any(k in attrs for k in ("start_marker", "end_marker", "center_marker")):
                    attrs["start_marker"] = ann.start_marker
                    attrs["end_marker"] = ann.end_marker
                    attrs["center_marker"] = ann.center_marker
                self.canvas.update_item_properties(item_id, attrs)
                break

    def on_item_moved(self, item_id, delta):
        for ann in self.model.annotations:
            if ann.id == item_id:
                ann.points = [p + delta for p in ann.points]
                break

    def on_delete_item(self, item_id):
        self.model.annotations = [a for a in self.model.annotations if a.id != item_id]
        self.update_page_view()

    def open_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "PDF図面を開く", "", "PDF Files (*.pdf)")
        if file_path:
            if self.pdf_handler.open_file(file_path):
                self.model.pdf_path = file_path
                self.current_page = 0
                self._load_thumbnails()
                self.update_page_view()
                self.canvas.reset_view()

    def swap_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "背景PDFを差し替え", "", "PDF Files (*.pdf)")
        if file_path:
            if self.pdf_handler.open_file(file_path):
                self.model.pdf_path = file_path
                self.update_page_view()

    def save_project(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "プロジェクトを保存", "", "JSON Files (*.json)")
        if file_path:
            save_project_file(self.model, file_path)
            QMessageBox.information(self, "保存", "プロジェクトを保存しました。")

    def load_project(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "プロジェクトを読み込み", "", "JSON Files (*.json)")
        if file_path:
            self.model = load_project_file(file_path)
            
            if self.model.pdf_path and os.path.exists(self.model.pdf_path):
                self.pdf_handler.open_file(self.model.pdf_path)
            else:
                QMessageBox.warning(self, "警告", "PDFファイルが見つかりません。再選択してください。")
                self.open_pdf()
            
            self.current_page = 0
            self._load_thumbnails()
            self.update_page_view()
            self.canvas.reset_view()

    def export_pdf(self):
        if not self.pdf_handler.doc or not self.model.pdf_path:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(self, "PDFを書き出し", "", "PDF Files (*.pdf)")
        if not file_path:
            return

        try:
            export_pdf_document(self.model, file_path)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"PDFを書き出せませんでした: {e}")
            return
        QMessageBox.information(self, "書き出し", f"PDFを書き出しました: {file_path}")

    def _load_thumbnails(self):
        pixmaps = []
        count = self.pdf_handler.get_page_count()
        for i in range(count):
            pixmaps.append(self.pdf_handler.get_page_pixmap(i))
        self.navigator.set_page_count(count)
        self.navigator.update_thumbnails(pixmaps)

    def update_page_view(self):
        pixmap = self.pdf_handler.get_page_pixmap(self.current_page)
        if pixmap:
            self.canvas.set_page_image(pixmap)
            for ann in self.model.annotations:
                if ann.page_num == self.current_page:
                    if ann.type == "line":
                        self.canvas.add_line_annotation(ann.points[0], ann.points[1], text=ann.text, color=ann.color, item_id=ann.id, font_family=ann.font_family, font_size=ann.font_size, line_width=ann.line_width, stroke_opacity=ann.stroke_opacity)
                    elif ann.type == "polyline":
                        self.canvas.add_polyline_annotation(ann.points, text=ann.text, color=ann.color, item_id=ann.id, font_family=ann.font_family, font_size=ann.font_size, line_width=ann.line_width, stroke_opacity=ann.stroke_opacity, start_marker=ann.start_marker, end_marker=ann.end_marker)
                    elif ann.type == "polygon":
                        self.canvas.add_polygon_annotation(ann.points, text=ann.text, color=ann.color, item_id=ann.id, font_family=ann.font_family, font_size=ann.font_size, line_width=ann.line_width, stroke_opacity=ann.stroke_opacity, fill_opacity=ann.fill_opacity, fill_color=ann.fill_color)
                    elif ann.type == "circle":
                        current_scale_factor = self._get_current_scale_factor()
                        if ann.radius_px > 0:
                            radius_px = ann.radius_px
                        elif ann.real_value > 0 and current_scale_factor > 0:
                            radius_px = ann.real_value / current_scale_factor
                        else:
                            radius_px = 0
                        self.canvas.add_circle_annotation(ann.points[0], radius_px, text=ann.text, color=ann.color, item_id=ann.id, font_family=ann.font_family, font_size=ann.font_size, line_width=ann.line_width, stroke_opacity=ann.stroke_opacity, fill_opacity=ann.fill_opacity, fill_color=ann.fill_color, center_marker=ann.center_marker)
                    elif ann.type == "text":
                        self.canvas.add_text_annotation(ann.points[0], ann.text, color=ann.color, item_id=ann.id, font_family=ann.font_family, font_size=ann.font_size, stroke_opacity=ann.stroke_opacity)
            self._update_scale_status_label()
            self._update_pdf_size_label()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_O and event.modifiers() & Qt.ControlModifier:
            self.open_pdf()
        elif event.key() == Qt.Key_A and not event.modifiers():
            # 「a」キーで選択ツールに切り替え
            self.on_request_tool_change(ToolMode.SELECT)
