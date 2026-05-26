import os
import math
from PySide6.QtWidgets import (QApplication, QMainWindow, QFileDialog, 
                             QLabel, QHBoxLayout, QWidget, QVBoxLayout, 
                             QInputDialog, QMessageBox, QPushButton, 
                             QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QShortcut, QKeySequence
import qtawesome as qta

from .services.pdf_exporter import export_pdf_document
from .services.pdf_handler import PDFHandler
from .services.project_store import load_project as load_project_file, save_project as save_project_file
from .ui.canvas import PDFCanvas, ToolMode
from .ui.preferences_dialog import PreferencesDialog
from .models import DrawingModel, Annotation
from .ui.panels.property_panel import PropertyPanel
from .ui.panels.navigator_panel import NavigatorPanel
from .ui.styles import GLOBAL_STYLE
from .ui.components import MainMenuBar, MainToolBar, ToolOptionsBar

class MainWindow(QMainWindow):
    # PDF描画解像度
    PDF_RENDER_DPI = 150
    # PDF座標系の基準DPI
    PDF_BASE_DPI = 72
    # 縮尺比率を整数表示に丸める際の許容差
    SCALE_RATIO_ROUNDING_TOLERANCE = 0.05
    # 表示倍率を整数表示に丸める際の許容差
    ZOOM_LABEL_ROUNDING_TOLERANCE_PP = 0.5

    def __init__(self):
        super().__init__()
        self.setWindowTitle("FirePreview")
        self.resize(1400, 900)

        self.pdf_handler = PDFHandler()
        self.model = DrawingModel()
        self.current_page = 0  # 内部ページ番号は0始まり
        self._pref_dialog_active = False
        self._calib_all_pages_from_prefs = False
        
        self.current_text_font = "Arial"
        self.current_text_size = 12
        self.current_text_color = "#ff0000"

        # Shape tool defaults
        self.current_shape_color = "#7c4dff"
        self.current_fill_color = "#7c4dff"
        self.current_fill_opacity = 30
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
        self._setup_shortcuts()

    def _setup_menus(self):
        self.menubar = MainMenuBar(self)
        self.setMenuBar(self.menubar)
        
        self.menubar.open_pdf_requested.connect(self.open_pdf)
        self.menubar.swap_pdf_requested.connect(self.swap_pdf)
        self.menubar.save_project_requested.connect(self.save_project)
        self.menubar.load_project_requested.connect(self.load_project)
        self.menubar.export_pdf_requested.connect(self.export_pdf)

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
        self.toolbar = MainToolBar()
        self.zoom_combo = self.toolbar.zoom_combo
        self.scale_status_label = self.toolbar.scale_status_label
        self.pdf_size_label = self.toolbar.pdf_size_label
        self.tool_btns = self.toolbar.tool_btns
        
        self.toolbar.tool_changed.connect(self.set_tool)
        self.toolbar.zoom_changed.connect(self._on_zoom_combo_changed_from_toolbar)
        self.main_layout.addWidget(self.toolbar)

        # 3. Tool Options Bar
        self.options_bar = ToolOptionsBar()
        
        self.options_bar.line_width_changed.connect(self._on_options_line_width_changed)
        self.options_bar.shape_color_changed.connect(self._on_options_shape_color_changed)
        self.options_bar.fill_color_changed.connect(self._on_options_fill_color_changed)
        self.options_bar.fill_opacity_changed.connect(self._on_options_fill_opacity_changed)
        self.options_bar.start_marker_changed.connect(self._on_options_start_marker_changed)
        self.options_bar.end_marker_changed.connect(self._on_options_end_marker_changed)
        self.options_bar.center_marker_changed.connect(self._on_options_center_marker_changed)
        self.options_bar.shape_continuous_changed.connect(self._on_options_shape_continuous_changed)
        
        self.options_bar.font_changed.connect(self._on_options_font_changed)
        self.options_bar.font_size_changed.connect(self._on_options_font_size_changed)
        self.options_bar.text_color_changed.connect(self._on_options_text_color_changed)
        self.options_bar.text_continuous_changed.connect(self._on_options_text_continuous_changed)
        
        self.main_layout.addWidget(self.options_bar)

        # 4. Content Area (Navigator | Canvas | Property)
        content_area = QHBoxLayout()
        content_area.setSpacing(0)

        # Navigator (Left)
        self.navigator = NavigatorPanel()
        self.navigator.setFixedWidth(220)
        self.navigator.page_changed.connect(self.go_to_page)
        self.navigator.object_selected.connect(self.on_object_selected_from_panel)
        self.navigator.object_edit_toggled.connect(self.on_object_edit_toggled_from_panel)
        content_area.addWidget(self.navigator)

        # Canvas (Center)
        self.canvas = PDFCanvas()
        self.canvas.setStyleSheet("background-color: #0f0f1a; border: none;")
        self.canvas.calibration_points_selected.connect(self.on_calibration_selected)
        self.canvas.polygon_complete.connect(self.on_polygon_complete)
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
        
        # Node editing connections
        self.prop_panel.node_edit_toggled.connect(self.on_node_edit_toggled)
        self.canvas.item_points_updated.connect(self.on_canvas_item_points_updated)
        self.canvas.node_edit_ended.connect(self.on_canvas_node_edit_ended)
        
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

    # --- Toolbar & Optionsbar callbacks ---
    def set_tool(self, mode, active_btn=None):
        self.toolbar.set_tool_mode(mode)
        self.canvas.set_tool_mode(mode)
        self.options_bar.update_options_visibility(mode, self._is_current_page_calibrated())

        is_shape_tool = mode in [ToolMode.DRAW_LINE, ToolMode.POLYGON_AREA, ToolMode.DRAW_CIRCLE_DRAG]
        if mode == ToolMode.TEXT:
            self.canvas.set_text_defaults(self.current_text_font, self.current_text_size, self.current_text_color, self.options_bar.tool_continuous_check.isChecked())
        elif is_shape_tool:
            self._update_canvas_shape_defaults()
            self.canvas.set_shape_continuous(self.options_bar.tool_shape_continuous_check.isChecked())

    def _on_options_line_width_changed(self, width):
        self.current_line_width = width
        self._update_canvas_shape_defaults()

    def _on_options_shape_color_changed(self, color):
        self.current_shape_color = color
        self._update_canvas_shape_defaults()

    def _on_options_fill_color_changed(self, color):
        self.current_fill_color = color
        self._update_canvas_shape_defaults()

    def _on_options_fill_opacity_changed(self, opacity):
        self.current_fill_opacity = opacity
        if self.canvas.editing_item_id:
            self.canvas.update_item_properties(self.canvas.editing_item_id, {"fill_opacity": opacity})

    def _on_options_start_marker_changed(self, index):
        self.current_start_marker = self._start_marker_values[index]
        if self.canvas.editing_item_id:
            self.canvas.update_item_properties(self.canvas.editing_item_id, {"start_marker": self.current_start_marker})

    def _on_options_end_marker_changed(self, index):
        self.current_end_marker = self._end_marker_values[index]
        if self.canvas.editing_item_id:
            self.canvas.update_item_properties(self.canvas.editing_item_id, {"end_marker": self.current_end_marker})

    def _on_options_center_marker_changed(self, index):
        self.current_center_marker = self._center_marker_values[index]
        if self.canvas.editing_item_id:
            self.canvas.update_item_properties(self.canvas.editing_item_id, {"center_marker": self.current_center_marker})

    def _on_options_shape_continuous_changed(self, checked):
        self.canvas.set_shape_continuous(checked)

    def _on_options_radius_changed(self, radius):
        pass

    def _on_options_font_changed(self, family):
        self.current_text_font = family
        self.canvas.set_text_defaults(self.current_text_font, self.current_text_size, self.current_text_color, self.options_bar.tool_continuous_check.isChecked())
        if self.canvas.editing_item_id:
            self.canvas.update_item_properties(self.canvas.editing_item_id, {"font_family": family})

    def _on_options_font_size_changed(self, size):
        self.current_text_size = size
        self.canvas.set_text_defaults(self.current_text_font, self.current_text_size, self.current_text_color, self.options_bar.tool_continuous_check.isChecked())
        if self.canvas.editing_item_id:
            self.canvas.update_item_properties(self.canvas.editing_item_id, {"font_size": size})

    def _on_options_text_color_changed(self, color):
        self.current_text_color = color
        self.canvas.set_text_defaults(self.current_text_font, self.current_text_size, self.current_text_color, self.options_bar.tool_continuous_check.isChecked())
        if self.canvas.editing_item_id:
            self.canvas.update_item_properties(self.canvas.editing_item_id, {"color": color})

    def _on_options_text_continuous_changed(self, checked):
        self.canvas.set_text_defaults(self.current_text_font, self.current_text_size, self.current_text_color, checked)

    def _on_zoom_combo_changed_from_toolbar(self, text):
        clean_text = text.replace("%", "").strip()
        try:
            zoom_percent = float(clean_text)
        except ValueError:
            if hasattr(self, "canvas") and self.canvas is not None:
                self._update_zoom_label(self.canvas.transform().m11())
            return

        if zoom_percent <= 0:
            if hasattr(self, "canvas") and self.canvas is not None:
                self._update_zoom_label(self.canvas.transform().m11())
            return

        physical_dpi = self._get_physical_dpi()
        if physical_dpi <= 0:
            return

        target_canvas_scale = (zoom_percent / 100.0) * physical_dpi / self.PDF_RENDER_DPI
        self.canvas.set_zoom_scale(target_canvas_scale)

    def _update_canvas_shape_defaults(self):
        self.canvas.set_shape_defaults(self.current_shape_color, self.current_line_width, self.current_fill_color)

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
        if not self.pdf_handler:
            self.pdf_size_label.setText(PDFHandler.SIZE_LABEL_UNKNOWN)
            return
        self.pdf_size_label.setText(self.pdf_handler.get_page_size_label(self.current_page))

    def _update_zoom_label(self, canvas_scale):
        if canvas_scale <= 0:
            self.zoom_combo.blockSignals(True)
            self.zoom_combo.setCurrentText("---")
            self.zoom_combo.blockSignals(False)
            return
        physical_dpi = self._get_physical_dpi()
        if physical_dpi <= 0:
            self.zoom_combo.blockSignals(True)
            self.zoom_combo.setCurrentText("---")
            self.zoom_combo.blockSignals(False)
            return
        zoom_percent = (canvas_scale * self.PDF_RENDER_DPI / physical_dpi) * 100.0
        rounded = round(zoom_percent)
        if abs(zoom_percent - rounded) <= self.ZOOM_LABEL_ROUNDING_TOLERANCE_PP:
            text = f"{rounded}%"
        else:
            text = f"{zoom_percent:.1f}%"
        
        self.zoom_combo.blockSignals(True)
        self.zoom_combo.setCurrentText(text)
        self.zoom_combo.blockSignals(False)

    def _setup_shortcuts(self):
        self.shortcut_zoom_reset = QShortcut(QKeySequence("Ctrl+0"), self)
        self.shortcut_zoom_reset.activated.connect(self._reset_zoom_to_100)

    def _reset_zoom_to_100(self):
        physical_dpi = self._get_physical_dpi()
        if physical_dpi <= 0:
            return
        target_canvas_scale = physical_dpi / self.PDF_RENDER_DPI
        self.canvas.set_zoom_scale(target_canvas_scale)

    def showEvent(self, event):
        super().showEvent(event)
        window = self.windowHandle()
        if window is not None and not hasattr(self, "_screen_changed_connected"):
            window.screenChanged.connect(self._on_screen_changed)
            self._screen_changed_connected = True

    def _on_screen_changed(self, screen):
        if hasattr(self, "canvas") and self.canvas is not None:
            current_scale = self.canvas.transform().m11()
            self._update_zoom_label(current_scale)

    def _get_physical_dpi(self):
        screen = None
        window = self.windowHandle()
        if window is not None:
            screen = window.screen()
        if screen is None:
            app = QApplication.instance()
            if app is not None:
                screen = app.primaryScreen()
        fallback_dpi = 96.0
        try:
            physical_dpi = screen.physicalDotsPerInch() if screen else fallback_dpi
        except (AttributeError, RuntimeError, TypeError):
            physical_dpi = fallback_dpi
        return physical_dpi if physical_dpi > 0 else fallback_dpi

    # --- 環境設定UI ---
    def _on_settings_clicked(self):
        self._open_preferences_dialog()

    def _open_preferences_dialog(self):
        total_pages = self.pdf_handler.get_page_count() if self.pdf_handler else 1
        self.pref_dialog = PreferencesDialog(
            self,
            self.model,
            self.current_page,
            total_pages,
            dpi=self.PDF_RENDER_DPI
        )
        self.pref_dialog.trigger_canvas_calibration.connect(self._on_pref_canvas_calibration_triggered)
        self.pref_dialog.settings_updated.connect(self._on_pref_settings_updated)
        
        self._pref_dialog_active = True
        self.pref_dialog.exec()
        self._pref_dialog_active = False

    def _on_pref_canvas_calibration_triggered(self, all_pages):
        self._calib_all_pages_from_prefs = all_pages
        if hasattr(self, "pref_dialog") and self.pref_dialog:
            self.pref_dialog.hide()
        self.set_tool(ToolMode.CALIBRATE, None)

    def _on_pref_settings_updated(self):
        self._update_scale_status_label()
        self.update_page_view()

    def apply_unit_change(self, new_unit):
        old_unit = self.model.unit
        self.model.unit = new_unit
        self.options_bar.apply_unit_change(new_unit, old_unit)

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
            all_pages = getattr(self, "_calib_all_pages_from_prefs", False)
            total_pages = self.pdf_handler.get_page_count() if self.pdf_handler else 1
            
            if self.model.set_calibration(p1, p2, dist_mm, self.current_page, all_pages=all_pages, total_pages=total_pages):
                QMessageBox.information(self, "完了", "キャリブレーションが完了しました。")
                self._update_scale_status_label()
                self.update_page_view()

        if getattr(self, "_pref_dialog_active", False):
            if hasattr(self, "pref_dialog") and self.pref_dialog:
                self.pref_dialog.update_status_display()
                self.pref_dialog.show()
            self._calib_all_pages_from_prefs = False

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
        current_scale_factor = self._get_current_scale_factor()
        if radius_px < 3:
            if self._is_current_page_calibrated() and current_scale_factor > 0:
                if self.model.unit == 'm':
                    radius_mm = self.options_bar.tool_radius_spin.value() * 1000
                else:
                    radius_mm = self.options_bar.tool_radius_spin.value()
                radius_px = radius_mm / current_scale_factor
            else:
                QMessageBox.warning(self, "警告", "半径を指定して円を描画するには、先にキャリブレーションを行ってください。")
                return

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

    def on_calculate_requested(self, item_id):
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
                self.prop_panel.set_item_data(ann.id, ann.type, ann.text, ann.color,
                                              ann.font_family, ann.font_size, ann.line_width,
                                              stroke_opacity=ann.stroke_opacity, fill_opacity=ann.fill_opacity,
                                              fill_color=ann.fill_color,
                                              center_marker=ann.center_marker, start_marker=ann.start_marker, end_marker=ann.end_marker)
                
                if self.canvas.editing_node_item_id == ann.id:
                    self.prop_panel.set_node_edit_active(True)
                self.update_object_panel()
                break

    def on_request_tool_change(self, mode):
        self.set_tool(mode, None)

    def on_text_editing_finished(self, pos, text, item_id, font_family, font_size, color):
        if not item_id:
            ann = self._add_to_model("text", [pos], text=text)
            ann.font_family = font_family
            ann.font_size = font_size
            ann.color = color
            self.canvas.add_text_annotation(pos, text, item_id=ann.id, font_family=ann.font_family, font_size=ann.font_size, color=ann.color)

    def on_existing_text_edited(self, item_id, new_text):
        for ann in self.model.annotations:
            if ann.id == item_id:
                ann.text = new_text
                break
        
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
        self.update_object_panel()
        return ann

    def on_item_selected(self, item_id):
        for ann in self.model.annotations:
            if ann.id == item_id:
                self.prop_panel.set_item_data(ann.id, ann.type, ann.text, ann.color,
                                              ann.font_family, ann.font_size, ann.line_width,
                                              stroke_opacity=ann.stroke_opacity, fill_opacity=ann.fill_opacity,
                                              fill_color=ann.fill_color,
                                              center_marker=ann.center_marker, start_marker=ann.start_marker, end_marker=ann.end_marker,
                                              has_border=getattr(ann, "has_border", False),
                                              border_color=getattr(ann, "border_color", "#ff0000"),
                                              border_width=getattr(ann, "border_width", 2),
                                              has_leader=getattr(ann, "has_leader", False))
                self.navigator.set_selected_object(item_id)
                break

    def on_selection_cleared(self):
        self.prop_panel.clear_panel()
        self.navigator.set_selected_object(None)

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
                
                # Border & Leader settings
                if "has_border" in attrs: ann.has_border = attrs["has_border"]
                if "border_color" in attrs: ann.border_color = attrs["border_color"]
                if "border_width" in attrs: ann.border_width = attrs["border_width"]
                
                if "has_leader" in attrs:
                    if attrs["has_leader"] and not getattr(ann, "has_leader", False):
                        from PySide6.QtCore import QPointF
                        if len(ann.points) == 0:
                            ann.points = [QPointF(0, 0), QPointF(50, 50)]
                        elif len(ann.points) == 1:
                            end_pt = ann.points[0] + QPointF(50, 50)
                            ann.points.append(end_pt)
                        
                        if len(ann.points) >= 2:
                            attrs["leader_end_point"] = ann.points[1]
                    elif not attrs["has_leader"] and getattr(ann, "has_leader", False):
                        if len(ann.points) >= 1:
                            ann.points = [ann.points[0]]
                    ann.has_leader = attrs["has_leader"]
                    
                if any(k in attrs for k in ("start_marker", "end_marker", "center_marker")):
                    attrs["start_marker"] = ann.start_marker
                    attrs["end_marker"] = ann.end_marker
                    attrs["center_marker"] = ann.center_marker
                if "color" in attrs:
                    attrs["fill_color"] = ann.fill_color
                self.canvas.update_item_properties(item_id, attrs)
                self.update_object_panel()
                break

    def on_item_moved(self, item_id, delta):
        for ann in self.model.annotations:
            if ann.id == item_id:
                if ann.type == "text":
                    if len(ann.points) >= 1:
                        ann.points[0] = ann.points[0] + delta
                else:
                    ann.points = [p + delta for p in ann.points]
                
                attrs = {}
                if hasattr(ann, 'start_marker') and ann.start_marker is not None:
                    attrs['start_marker'] = ann.start_marker
                if hasattr(ann, 'end_marker') and ann.end_marker is not None:
                    attrs['end_marker'] = ann.end_marker
                if hasattr(ann, 'center_marker') and ann.center_marker is not None:
                    attrs['center_marker'] = ann.center_marker
                
                if attrs:
                    self.canvas.update_item_properties(item_id, attrs)
                break

    def on_node_edit_toggled(self, item_id, active):
        if active:
            self.canvas.start_node_editing(item_id)
        else:
            self.canvas.end_node_editing()

    def on_canvas_node_edit_ended(self, item_id):
        self.prop_panel.set_node_edit_active(False)

    def on_canvas_item_points_updated(self, item_id, points):
        for ann in self.model.annotations:
            if ann.id == item_id:
                ann.points = points
                
                if self._is_current_page_calibrated():
                    self.on_calculate_requested(item_id)
                
                if ann.type == "polyline":
                    self.canvas.update_item_properties(item_id, {"start_marker": ann.start_marker, "end_marker": ann.end_marker})
                self.update_object_panel()
                break

    def on_delete_item(self, item_id):
        if hasattr(self.canvas, 'active_edit_mode') and self.canvas.active_edit_mode and self.canvas.editing_item_id == item_id:
            self.on_object_edit_toggled_from_panel(item_id, False)
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
                        leader_end = ann.points[1] if len(ann.points) >= 2 else None
                        self.canvas.add_text_annotation(ann.points[0], ann.text, color=ann.color, item_id=ann.id, font_family=ann.font_family, font_size=ann.font_size, stroke_opacity=ann.stroke_opacity,
                                                        has_border=getattr(ann, "has_border", False),
                                                        border_color=getattr(ann, "border_color", "#ff0000"),
                                                        border_width=getattr(ann, "border_width", 2),
                                                        has_leader=getattr(ann, "has_leader", False),
                                                        leader_end_point=leader_end)
            self._update_scale_status_label()
            self._update_pdf_size_label()
            self.update_object_panel()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_O and event.modifiers() & Qt.ControlModifier:
            self.open_pdf()
        elif event.key() == Qt.Key_A and not event.modifiers():
            self.on_request_tool_change(ToolMode.SELECT)

    def update_object_panel(self):
        page_anns = [ann for ann in self.model.annotations if ann.page_num == self.current_page]
        self.navigator.update_objects(page_anns)

    def on_object_selected_from_panel(self, item_id):
        self.canvas.scene.clearSelection()
        target_item = None
        for item in self.canvas.scene.items():
            if item.data(0) == item_id:
                target_item = item
                break
        if target_item:
            target_item.setSelected(True)
            self.on_item_selected(item_id)

    def on_object_edit_toggled_from_panel(self, item_id, active):
        self.canvas.set_active_edit_item(item_id, active)
        self.navigator.set_editing_object(item_id, active)
        
        if active:
            self.on_request_tool_change(ToolMode.SELECT)
            
        for btn in self.tool_btns:
            mode = btn.property("tool_mode")
            if mode != ToolMode.SELECT:
                btn.setEnabled(not active)
                
        if hasattr(self.prop_panel, 'node_edit_btn'):
            self.prop_panel.node_edit_btn.setEnabled(not active)
