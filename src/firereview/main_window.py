import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QFileDialog, 
                             QLabel, QHBoxLayout, QWidget, QVBoxLayout, 
                             QInputDialog, QMessageBox, QPushButton, 
                             QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence
import qtawesome as qta

from .services.pdf_handler import PDFHandler
from .services import DocumentManager, MeasurementService
from .controllers import ToolController, CanvasController
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
        self.setWindowTitle("FireReviewPDF")
        self.resize(1400, 900)

        self.pdf_handler = PDFHandler()
        self.document_manager = DocumentManager(self.pdf_handler, parent=self)
        self.document_manager.dirty_changed.connect(self._on_dirty_changed)
        self.measurement_service = MeasurementService()
        self.tool_controller = ToolController(
            on_marker_updated_cb=lambda: self.update_marker_summary()
        )

        self.current_page = 0  # 内部ページ番号は0始まり
        self._pref_dialog_active = False
        self._calib_all_pages_from_prefs = False

        self.setup_ui()
        self._setup_menus()
        self.apply_styles()
        self._setup_shortcuts()
        self._update_window_title()

    # --- Document & Model Properties ---
    @property
    def model(self) -> DrawingModel:
        return self.document_manager.model

    @model.setter
    def model(self, value: DrawingModel):
        self.document_manager.model = value

    @property
    def is_dirty(self) -> bool:
        return self.document_manager.is_dirty

    @is_dirty.setter
    def is_dirty(self, value: bool):
        self.document_manager.set_dirty(value)

    @property
    def current_project_path(self) -> str:
        return self.document_manager.current_project_path

    @current_project_path.setter
    def current_project_path(self, value: str):
        self.document_manager.current_project_path = value

    # --- Tool Setting Properties (Backward Compatibility) ---
    @property
    def current_shape_color(self) -> str: return self.tool_controller.current_shape_color
    @current_shape_color.setter
    def current_shape_color(self, v: str): self.tool_controller.current_shape_color = v

    @property
    def current_fill_color(self) -> str: return self.tool_controller.current_fill_color
    @current_fill_color.setter
    def current_fill_color(self, v: str): self.tool_controller.current_fill_color = v

    @property
    def current_fill_opacity(self) -> int: return self.tool_controller.current_fill_opacity
    @current_fill_opacity.setter
    def current_fill_opacity(self, v: int): self.tool_controller.current_fill_opacity = v

    @property
    def current_line_width(self) -> int: return self.tool_controller.current_line_width
    @current_line_width.setter
    def current_line_width(self, v: int): self.tool_controller.current_line_width = v

    @property
    def current_start_marker(self) -> str: return self.tool_controller.current_start_marker
    @current_start_marker.setter
    def current_start_marker(self, v: str): self.tool_controller.current_start_marker = v

    @property
    def current_end_marker(self) -> str: return self.tool_controller.current_end_marker
    @current_end_marker.setter
    def current_end_marker(self, v: str): self.tool_controller.current_end_marker = v

    @property
    def current_center_marker(self) -> str: return self.tool_controller.current_center_marker
    @current_center_marker.setter
    def current_center_marker(self, v: str): self.tool_controller.current_center_marker = v

    @property
    def current_arc_span(self) -> float: return self.tool_controller.current_arc_span
    @current_arc_span.setter
    def current_arc_span(self, v: float): self.tool_controller.current_arc_span = v

    @property
    def current_arc_show_radial_line(self) -> bool: return self.tool_controller.current_arc_show_radial_line
    @current_arc_show_radial_line.setter
    def current_arc_show_radial_line(self, v: bool): self.tool_controller.current_arc_show_radial_line = v

    @property
    def current_marker_style(self) -> str: return self.tool_controller.current_marker_style
    @current_marker_style.setter
    def current_marker_style(self, v: str): self.tool_controller.current_marker_style = v

    @property
    def current_marker_color(self) -> str: return self.tool_controller.current_marker_color
    @current_marker_color.setter
    def current_marker_color(self, v: str): self.tool_controller.current_marker_color = v

    @property
    def current_marker_opacity(self) -> int: return self.tool_controller.current_marker_opacity
    @current_marker_opacity.setter
    def current_marker_opacity(self, v: int): self.tool_controller.current_marker_opacity = v

    @property
    def current_text_font(self) -> str: return self.tool_controller.current_text_font
    @current_text_font.setter
    def current_text_font(self, v: str): self.tool_controller.current_text_font = v

    @property
    def current_text_size(self) -> int: return self.tool_controller.current_text_size
    @current_text_size.setter
    def current_text_size(self, v: int): self.tool_controller.current_text_size = v

    @property
    def current_text_color(self) -> str: return self.tool_controller.current_text_color
    @current_text_color.setter
    def current_text_color(self, v: str): self.tool_controller.current_text_color = v

    def set_dirty(self, dirty: bool = True):
        """ダーティ状態を設定し、タイトルバーの表示を更新する。"""
        self.document_manager.set_dirty(dirty)

    def _on_dirty_changed(self, is_dirty: bool):
        self._update_window_title()

    def _update_window_title(self):
        """プロジェクト/PDFファイル名および未保存マーク（*）を反映してウィンドウタイトルを更新する。"""
        base_title = "FireReviewPDF"
        file_name = self.document_manager.get_active_document_name()

        if file_name:
            title = f"{base_title} - {file_name}"
        else:
            title = base_title

        if self.document_manager.is_dirty:
            title += " *"
        self.setWindowTitle(title)

    def maybe_save_changes(self) -> bool:
        """未保存の変更がある場合に保存確認ダイアログを表示する。

        Returns:
            bool: 処理を継続してよい場合は True、キャンセルされた場合は False。
        """
        if not self.is_dirty:
            return True

        reply = QMessageBox.question(
            self,
            "未保存の変更",
            "プロジェクトへの変更が保存されていません。\n保存しますか？",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save
        )

        if reply == QMessageBox.Save:
            return self.save_project()
        elif reply == QMessageBox.Discard:
            return True
        else:
            return False

    def closeEvent(self, event):
        if self.maybe_save_changes():
            event.accept()
        else:
            event.ignore()

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
        self.options_bar.marker_style_changed.connect(self._on_options_marker_style_changed)
        self.options_bar.marker_continuous_changed.connect(self._on_options_marker_continuous_changed)
        self.options_bar.marker_opacity_changed.connect(self._on_options_marker_opacity_changed)
        self.options_bar.marker_color_changed.connect(self._on_options_marker_color_changed)
        
        self.options_bar.font_changed.connect(self._on_options_font_changed)
        self.options_bar.font_size_changed.connect(self._on_options_font_size_changed)
        self.options_bar.text_color_changed.connect(self._on_options_text_color_changed)
        self.options_bar.text_continuous_changed.connect(self._on_options_text_continuous_changed)
        self.options_bar.arc_span_changed.connect(self._on_options_arc_span_changed)
        self.options_bar.arc_radial_line_changed.connect(self._on_options_arc_radial_line_changed)
        
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
        self.navigator.color_name_changed.connect(self.on_color_name_changed)
        content_area.addWidget(self.navigator)

        # Canvas (Center)
        self.canvas = PDFCanvas()
        self.canvas.setStyleSheet("background-color: #0f0f1a; border: none;")
        self.canvas.calibration_points_selected.connect(self.on_calibration_selected)
        self.canvas.polygon_complete.connect(self.on_polygon_complete)
        self.canvas.polyline_complete.connect(self.on_polyline_complete)
        self.canvas.circle_drag_complete.connect(self.on_circle_drag_complete)
        self.canvas.arc_drag_complete.connect(self.on_arc_drag_complete)
        self.canvas.marker_complete.connect(self.on_marker_complete)
        self.canvas.legend_complete.connect(self.on_legend_complete)
        self.canvas.item_selected.connect(self.on_item_selected)
        self.canvas.selection_cleared.connect(self.on_selection_cleared)
        self.canvas.item_moved.connect(self.on_item_moved)
        self.canvas.label_moved.connect(self.on_label_moved)
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

        # Wire up ToolController
        self.tool_controller.canvas = self.canvas
        self.tool_controller.options_bar = self.options_bar
        self.tool_controller.toolbar = self.toolbar

        # Canvas Controller
        self.canvas_controller = CanvasController(
            canvas=self.canvas,
            document_manager=self.document_manager,
            measurement_service=self.measurement_service,
            tool_controller=self.tool_controller,
            prop_panel=self.prop_panel,
            navigator=self.navigator,
            get_current_page_fn=lambda: self.current_page,
            get_current_scale_factor_fn=self._get_current_scale_factor,
            is_current_page_calibrated_fn=self._is_current_page_calibrated,
            set_tool_fn=self.set_tool,
            parent_widget=self,
        )

        # 5. Status Bar
        self._setup_status_bar()

    def _setup_header(self):
        header = QFrame()
        header.setObjectName("MainHeader")
        header.setFixedHeight(50)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(15, 0, 15, 0)

        title = QLabel("FireReviewPDF")
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
        self.tool_controller.set_tool(mode, self._is_current_page_calibrated())

    def _on_options_line_width_changed(self, width):
        self.tool_controller.on_options_line_width_changed(width)

    def _on_options_shape_color_changed(self, color):
        self.tool_controller.on_options_shape_color_changed(color)

    def _on_options_fill_color_changed(self, color):
        self.tool_controller.on_options_fill_color_changed(color)

    def _on_options_fill_opacity_changed(self, opacity):
        self.tool_controller.on_options_fill_opacity_changed(opacity)

    def _on_options_start_marker_changed(self, index):
        self.tool_controller.on_options_start_marker_changed(index)

    def _on_options_end_marker_changed(self, index):
        self.tool_controller.on_options_end_marker_changed(index)

    def _on_options_center_marker_changed(self, index):
        self.tool_controller.on_options_center_marker_changed(index)

    def _on_options_shape_continuous_changed(self, checked):
        self.tool_controller.on_options_shape_continuous_changed(checked)

    def _on_options_marker_style_changed(self, style):
        self.tool_controller.on_options_marker_style_changed(style)

    def _on_options_marker_continuous_changed(self, checked):
        self.tool_controller.on_options_marker_continuous_changed(checked)

    def _on_options_marker_opacity_changed(self, value):
        self.tool_controller.on_options_marker_opacity_changed(value)

    def _on_options_marker_color_changed(self, color):
        self.tool_controller.on_options_marker_color_changed(color)

    def _on_options_radius_changed(self, radius):
        pass

    def _on_options_font_changed(self, family):
        self.tool_controller.on_options_font_changed(family)

    def _on_options_font_size_changed(self, size):
        self.tool_controller.on_options_font_size_changed(size)

    def _on_options_text_color_changed(self, color):
        self.tool_controller.on_options_text_color_changed(color)

    def _on_options_text_continuous_changed(self, checked):
        self.tool_controller.on_options_text_continuous_changed(checked)

    def _on_options_arc_span_changed(self, value):
        self.tool_controller.on_options_arc_span_changed(value)

    def _on_options_arc_radial_line_changed(self, checked):
        self.tool_controller.on_options_arc_radial_line_changed(checked)

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
        self.tool_controller.update_canvas_shape_defaults()

    def _calculate_annotation_values(self, ann, sf):
        self.measurement_service.calculate_annotation_values(ann, sf, self.model)

    def _recalculate_all_annotations(self):
        self.measurement_service.recalculate_all_annotations(self.model)

    # --- 単位フォーマットヘルパー ---
    def _format_distance(self, value_mm):
        return self.measurement_service.format_distance(value_mm, self.model.unit)

    def _format_area(self, value_mm2):
        return self.measurement_service.format_area(value_mm2, self.model.unit)

    def _format_radius(self, value_mm):
        return self.measurement_service.format_radius(value_mm, self.model.unit)

    def _get_scale_factor_for_page(self, page_num):
        return self.model.get_scale_factor(page_num)

    def _get_current_scale_factor(self):
        return self._get_scale_factor_for_page(self.current_page)

    def _is_page_calibrated(self, page_num):
        return self.model.is_page_calibrated(page_num)

    def _is_current_page_calibrated(self):
        return self._is_page_calibrated(self.current_page)

    def _format_scale_ratio(self, scale_factor):
        return self.measurement_service.format_scale_ratio(
            scale_factor, self.PDF_RENDER_DPI, self.SCALE_RATIO_ROUNDING_TOLERANCE
        )

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
        self._recalculate_all_annotations()
        self._update_scale_status_label()
        self.update_page_view()
        self.set_dirty(True)

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
                elif ann.type in ("circle", "arc") and ann.text != "R=15m":
                    ann.text = self._format_radius(ann.real_value)
                    self.canvas.update_item_properties(ann.id, {"text": ann.text})
        self.set_dirty(True)

    def go_to_page(self, page_idx):
        self.current_page = page_idx
        self.update_page_view()
        self.canvas.reset_view()

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
                self._recalculate_all_annotations()
                QMessageBox.information(self, "完了", "キャリブレーションが完了しました。")
                self._update_scale_status_label()
                self.update_page_view()
                self.set_dirty(True)

        if getattr(self, "_pref_dialog_active", False):
            if hasattr(self, "pref_dialog") and self.pref_dialog:
                self.pref_dialog.update_status_display()
                self.pref_dialog.show()
            self._calib_all_pages_from_prefs = False

    def on_polygon_complete(self, points):
        self.canvas_controller.on_polygon_complete(points)

    def on_polyline_complete(self, points):
        self.canvas_controller.on_polyline_complete(points)

    def on_circle_drag_complete(self, center, radius_px):
        self.canvas_controller.on_circle_drag_complete(center, radius_px)

    def on_arc_drag_complete(self, center, radius_px, drag_angle):
        self.canvas_controller.on_arc_drag_complete(center, radius_px, drag_angle)

    def on_marker_complete(self, pos):
        self.canvas_controller.on_marker_complete(pos)

    def on_legend_complete(self, pos):
        self.canvas_controller.on_legend_complete(pos)

    def on_color_name_changed(self, page_num, color_hex, new_name):
        self.canvas_controller.on_color_name_changed(page_num, color_hex, new_name)

    def update_marker_summary(self):
        self.canvas_controller.update_marker_summary()

    def on_calculate_requested(self, item_id):
        self.canvas_controller.on_calculate_requested(item_id)

    def on_request_tool_change(self, mode):
        self.set_tool(mode, None)

    def on_text_editing_finished(self, pos, text, item_id, font_family, font_size, color):
        self.canvas_controller.on_text_editing_finished(pos, text, item_id, font_family, font_size, color)

    def on_existing_text_edited(self, item_id, new_text):
        self.canvas_controller.on_existing_text_edited(item_id, new_text)

    def _add_to_model(self, type, points, real_value=0.0, text=""):
        return self.canvas_controller.add_to_model(type, points, real_value=real_value, text=text)

    def on_item_selected(self, item_id):
        self.canvas_controller.on_item_selected(item_id)

    def on_selection_cleared(self):
        self.canvas_controller.on_selection_cleared()

    def on_property_changed(self, item_id, attrs):
        self.canvas_controller.on_property_changed(item_id, attrs)

    def on_item_moved(self, item_id, delta):
        self.canvas_controller.on_item_moved(item_id, delta)

    def on_label_moved(self, item_id, delta):
        self.canvas_controller.on_label_moved(item_id, delta)

    def on_node_edit_toggled(self, item_id, active):
        self.canvas_controller.on_node_edit_toggled(item_id, active)

    def on_canvas_node_edit_ended(self, item_id):
        self.canvas_controller.on_canvas_node_edit_ended(item_id)

    def on_canvas_item_points_updated(self, item_id, points):
        self.canvas_controller.on_canvas_item_points_updated(item_id, points)

    def on_delete_item(self, item_id):
        self.canvas_controller.on_delete_item(item_id)

    def open_pdf(self):
        if not self.maybe_save_changes():
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "PDF図面を開く", "", "PDF Files (*.pdf)")
        if file_path:
            if self.document_manager.open_pdf(file_path):
                self.current_page = 0
                self._load_thumbnails()
                self.update_page_view()
                self.canvas.reset_view()
            else:
                QMessageBox.critical(
                    self,
                    "エラー",
                    f"PDFファイルを開けませんでした:\n{file_path}\n\nファイルが破損しているか、アクセス権限がない可能性があります。"
                )

    def swap_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "背景PDFを差し替え", "", "PDF Files (*.pdf)")
        if file_path:
            if self.document_manager.swap_pdf(file_path):
                self.update_page_view()
            else:
                QMessageBox.critical(
                    self,
                    "エラー",
                    f"差し替え用PDFファイルを開けませんでした:\n{file_path}\n\nファイルが破損しているか、アクセス権限がない可能性があります。"
                )

    def save_project(self) -> bool:
        default_path = self.document_manager.get_suggested_save_path()
        file_path, _ = QFileDialog.getSaveFileName(self, "プロジェクトを保存", default_path, "JSON Files (*.json)")
        if not file_path:
            return False
        try:
            self.document_manager.save_project(file_path)
            QMessageBox.information(self, "保存", "プロジェクトを保存しました。")
            return True
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"プロジェクトの保存に失敗しました:\n{e}")
            return False

    def load_project(self):
        if not self.maybe_save_changes():
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "プロジェクトを読み込み", "", "JSON Files (*.json)")
        if not file_path:
            return

        try:
            loaded_model = self.document_manager.load_project(file_path)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"プロジェクトファイルの読み込みに失敗しました:\n{e}")
            return

        pdf_loaded = False
        pdf_path = loaded_model.pdf_path
        if pdf_path and os.path.exists(pdf_path):
            if self.pdf_handler.open_file(pdf_path):
                pdf_loaded = True
            else:
                QMessageBox.warning(
                    self,
                    "警告",
                    f"プロジェクトに設定されていた背景PDFを開けませんでした:\n{pdf_path}\n\nファイルが破損している可能性があります。別のPDFを選択してください。"
                )
        else:
            QMessageBox.warning(self, "警告", "プロジェクトに設定されていた背景PDFが見つかりません。再選択してください。")

        if not pdf_loaded:
            alt_path, _ = QFileDialog.getOpenFileName(self, "背景PDFを選択", "", "PDF Files (*.pdf)")
            if not alt_path:
                QMessageBox.warning(self, "キャンセル", "背景PDFが選択されなかったため、プロジェクトの読み込みを中止しました。")
                return
            if not self.pdf_handler.open_file(alt_path):
                QMessageBox.critical(
                    self,
                    "エラー",
                    f"選択されたPDFファイルを開けませんでした:\n{alt_path}\n\nファイルが破損しているか、アクセス権限がない可能性があります。"
                )
                return
            loaded_model.pdf_path = alt_path

        self.document_manager.apply_loaded_project(loaded_model, file_path)
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
            self.document_manager.export_pdf(file_path)
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "エラー", f"PDFを書き出せませんでした: {e}")
            return
        QMessageBox.information(self, "書き出し", f"PDFを書き出しました: {file_path}")

    def _load_thumbnails(self):
        pixmaps = []
        count = self.pdf_handler.get_page_count()
        for i in range(count):
            pixmaps.append(self.pdf_handler.get_page_pixmap(i, dpi=30))
        self.navigator.set_page_count(count)
        self.navigator.update_thumbnails(pixmaps)

    def update_page_view(self):
        pixmap = self.pdf_handler.get_page_pixmap(self.current_page)
        if pixmap:
            self.canvas.set_page_image(pixmap)
            self.canvas_controller.render_page_annotations(
                self.current_page, self._get_current_scale_factor()
            )
            self._update_scale_status_label()
            self._update_pdf_size_label()
            self.update_object_panel()
            self.update_marker_summary()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_O and event.modifiers() & Qt.ControlModifier:
            self.open_pdf()
        elif event.key() == Qt.Key_A and not event.modifiers():
            self.on_request_tool_change(ToolMode.SELECT)

    def update_object_panel(self):
        self.canvas_controller.update_object_panel()

    def on_object_selected_from_panel(self, item_id):
        self.canvas_controller.on_object_selected_from_panel(item_id)

    def on_object_edit_toggled_from_panel(self, item_id, active):
        self.canvas_controller.on_object_edit_toggled_from_panel(item_id, active)
