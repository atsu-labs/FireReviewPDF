import sys
import os
import json
import fitz # PyMuPDF
from PySide6.QtWidgets import (QApplication, QMainWindow, QFileDialog, 
                             QLabel, QHBoxLayout, QWidget, QVBoxLayout, 
                             QInputDialog, QMessageBox, QDockWidget, QPushButton, 
                             QFrame, QSpacerItem, QSizePolicy, QFontComboBox, QSpinBox, QColorDialog, QCheckBox)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QAction, QFont, QColor
import qtawesome as qta

from pdf_handler import PDFHandler
from canvas import PDFCanvas, ToolMode
from models import DrawingModel, Annotation
from property_panel import PropertyPanel
from navigator_panel import NavigatorPanel
from styles import GLOBAL_STYLE

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FirePreview")
        self.resize(1400, 900)

        self.pdf_handler = PDFHandler()
        self.model = DrawingModel()
        self.current_page = 0
        
        self.current_text_font = "Arial"
        self.current_text_size = 12
        self.current_text_color = "#ff0000"

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
        self.canvas.item_selected.connect(self.on_item_selected)
        self.canvas.selection_cleared.connect(self.on_selection_cleared)
        self.canvas.item_moved.connect(self.on_item_moved)
        self.canvas.text_editing_finished.connect(self.on_text_editing_finished)
        self.canvas.request_tool_change.connect(self.on_request_tool_change)
        self.canvas.existing_text_edited.connect(self.on_existing_text_edited)
        content_area.addWidget(self.canvas)

        # Property Panel (Right)
        self.prop_panel = PropertyPanel()
        self.prop_panel.setFixedWidth(280)
        self.prop_panel.attribute_changed.connect(self.on_property_changed)
        self.prop_panel.delete_requested.connect(self.on_delete_item)
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
        btn_settings = QPushButton()
        btn_settings.setIcon(qta.icon('fa5s.cog', color='white'))
        user_info = QLabel(" 👤 ユーザー名")
        h_layout.addWidget(btn_share)
        h_layout.addWidget(btn_settings)
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
            ('fa5s.square', "矩形", ToolMode.POLYGON_AREA),
            ('fa5s.font', "テキスト", ToolMode.TEXT),
            ('fa5s.pen', "ペン", ToolMode.MEASURE_LINE),
            ('fa5s.circle', "15m円", ToolMode.CIRCLE_FIXED),
            ('fa5s.ruler', "計測", ToolMode.CALIBRATE),
            ('fa5s.comment', "コメント", ToolMode.TEXT)
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

        self.main_layout.addWidget(toolbar)

    def _setup_options_bar(self):
        self.options_bar = QFrame()
        self.options_bar.setObjectName("ToolOptionsBar")
        self.options_bar.setFixedHeight(40)
        o_layout = QHBoxLayout(self.options_bar)
        o_layout.setContentsMargins(15, 0, 15, 0)

        self.default_opt_label = QLabel("ツールプロパティ: 未選択")
        o_layout.addWidget(self.default_opt_label)
        
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

    def _on_tool_font_changed(self, font):
        self.current_text_font = font.family()

    def _on_tool_font_size_changed(self, size):
        self.current_text_size = size

    def _on_tool_color_clicked(self):
        color = QColorDialog.getColor(QColor(self.current_text_color))
        if color.isValid():
            self.current_text_color = color.name()
            self.tool_color_preview.setStyleSheet(f"background-color: {self.current_text_color}; border-radius: 4px;")

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
        
        if mode in [ToolMode.MEASURE_LINE, ToolMode.POLYGON_AREA, ToolMode.CIRCLE_FIXED]:
            if not self.model.is_calibrated and mode != ToolMode.CALIBRATE:
                QMessageBox.warning(self, "警告", "先にキャリブレーションを行ってください。")
                active_btn.setChecked(False)
                return

        self.canvas.set_tool_mode(mode)
        
        if mode == ToolMode.TEXT:
            self.default_opt_label.hide()
            self.text_options_widget.show()
            self.canvas.set_text_defaults(self.current_text_font, self.current_text_size, self.current_text_color, self.tool_continuous_check.isChecked())
        else:
            self.default_opt_label.show()
            self.text_options_widget.hide()

    def go_to_page(self, page_idx):
        self.current_page = page_idx
        self.update_page_view()

    # --- (Delegated Methods from original main.py) ---
    def on_calibration_selected(self, p1, p2):
        dist_mm, ok = QInputDialog.getDouble(self, "キャリブレーション", "実寸法を入力してください (mm):", 1000, 0, 1000000, 1)
        if ok:
            if self.model.set_calibration(p1, p2, dist_mm):
                QMessageBox.information(self, "完了", "キャリブレーションが完了しました。")

    def on_measurement_complete(self, p1, p2):
        dist_mm = self.model.calculate_real_distance(p1, p2)
        text = f"{dist_mm:.1f} mm"
        ann = self._add_to_model("line", [p1, p2], dist_mm, text=text)
        self.canvas.add_line_annotation(p1, p2, text=text, item_id=ann.id, font_family=ann.font_family, font_size=ann.font_size)

    def on_polygon_complete(self, points):
        area_mm2 = self.model.calculate_real_area(points)
        area_m2 = area_mm2 / 1_000_000.0
        text = f"{area_m2:.2f} m²"
        ann = self._add_to_model("polygon", points, area_mm2, text=text)
        self.canvas.add_polygon_annotation(points, text=text, item_id=ann.id, font_family=ann.font_family, font_size=ann.font_size)

    def on_point_selected(self, pos):
        if self.canvas.tool_mode == ToolMode.CIRCLE_FIXED:
            radius_mm = 15000 
            radius_px = radius_mm / self.model.scale_factor
            text = "R=15m"
            ann = self._add_to_model("circle", [pos], radius_mm, text=text)
            self.canvas.add_circle_annotation(pos, radius_px, text=text, item_id=ann.id, font_family=ann.font_family, font_size=ann.font_size)

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
                self.prop_panel.set_item_data(ann.id, ann.type, ann.text, ann.color, ann.font_family, ann.font_size, ann.line_width, ann.opacity)
                break

    def on_selection_cleared(self):
        self.prop_panel.clear_panel()

    def on_property_changed(self, item_id, attrs):
        for ann in self.model.annotations:
            if ann.id == item_id:
                if "text" in attrs: ann.text = attrs["text"]
                if "color" in attrs: ann.color = attrs["color"]
                if "font_family" in attrs: ann.font_family = attrs["font_family"]
                if "font_size" in attrs: ann.font_size = attrs["font_size"]
                if "line_width" in attrs: ann.line_width = attrs["line_width"]
                if "opacity" in attrs: ann.opacity = attrs["opacity"]
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
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.model.to_dict(), f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "保存", "プロジェクトを保存しました。")

    def load_project(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "プロジェクトを読み込み", "", "JSON Files (*.json)")
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.model = DrawingModel.from_dict(data)
            
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

        dpi_factor = 72.0 / 150.0
        try:
            export_doc = fitz.open(self.model.pdf_path)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"元のPDFファイルを開けませんでした: {e}")
            return
        
        for ann in self.model.annotations:
            if ann.page_num >= len(export_doc):
                continue
                
            page = export_doc[ann.page_num]
            from PySide6.QtGui import QColor
            c = QColor(ann.color)
            color = (c.red()/255.0, c.green()/255.0, c.blue()/255.0)
            fill_opacity = ann.opacity / 100.0
            
            def to_pdf_pt(qp):
                return fitz.Point(qp.x() * dpi_factor, qp.y() * dpi_factor)

            if ann.type == "line":
                p1 = to_pdf_pt(ann.points[0])
                p2 = to_pdf_pt(ann.points[1])
                page.draw_line(p1, p2, color=color, width=ann.line_width, stroke_opacity=fill_opacity)
                if ann.text:
                    mid = (p1 + p2) / 2
                    page.insert_text(mid, ann.text, color=color, fontsize=ann.font_size, fontname="helv", fill_opacity=fill_opacity)
            
            elif ann.type == "polygon":
                pts = [to_pdf_pt(p) for p in ann.points]
                page.draw_polyline(pts + [pts[0]], color=color, width=ann.line_width, stroke_opacity=fill_opacity)
                if ann.text:
                    avg_x = sum(p.x for p in pts) / len(pts)
                    avg_y = sum(p.y for p in pts) / len(pts)
                    page.insert_text((avg_x, avg_y), ann.text, color=color, fontsize=ann.font_size, fontname="helv", fill_opacity=fill_opacity)
            
            elif ann.type == "circle":
                center = to_pdf_pt(ann.points[0])
                radius = (ann.real_value / self.model.scale_factor) * dpi_factor
                page.draw_circle(center, radius, color=color, width=ann.line_width, stroke_opacity=fill_opacity)
                if ann.text:
                    page.insert_text((center.x, center.y - radius - 5), ann.text, color=color, fontsize=ann.font_size, fontname="helv", fill_opacity=fill_opacity)
            
            elif ann.type == "text":
                pos = to_pdf_pt(ann.points[0])
                page.insert_text(pos, ann.text, color=color, fontsize=ann.font_size, fontname="helv", fill_opacity=fill_opacity)

        export_doc.save(file_path)
        export_doc.close()
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
                        self.canvas.add_line_annotation(ann.points[0], ann.points[1], text=ann.text, color=ann.color, item_id=ann.id, font_family=ann.font_family, font_size=ann.font_size, line_width=ann.line_width, opacity=ann.opacity)
                    elif ann.type == "polygon":
                        self.canvas.add_polygon_annotation(ann.points, text=ann.text, color=ann.color, item_id=ann.id, font_family=ann.font_family, font_size=ann.font_size, line_width=ann.line_width, opacity=ann.opacity)
                    elif ann.type == "circle":
                        radius_px = ann.real_value / self.model.scale_factor
                        self.canvas.add_circle_annotation(ann.points[0], radius_px, text=ann.text, color=ann.color, item_id=ann.id, font_family=ann.font_family, font_size=ann.font_size, line_width=ann.line_width, opacity=ann.opacity)
                    elif ann.type == "text":
                        self.canvas.add_text_annotation(ann.points[0], ann.text, color=ann.color, item_id=ann.id, font_family=ann.font_family, font_size=ann.font_size, opacity=ann.opacity)
            
            if not self.model.pdf_path:
                pass 

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_O and event.modifiers() & Qt.ControlModifier:
            self.open_pdf()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
