from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, 
                              QFrame, QHBoxLayout, QPushButton, QStackedWidget)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QColor
import qtawesome as qta

class NavigatorPanel(QWidget):
    page_changed = Signal(int)
    object_selected = Signal(str)  # item_id
    object_edit_toggled = Signal(str, bool)  # item_id, active

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_edit_id = None
        self.selected_id = None
        self.rows = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("PanelHeader")
        h_layout = QHBoxLayout(header)
        title = QLabel("ナビゲーター")
        title.setStyleSheet("font-weight: bold; color: #ffffff;")
        h_layout.addWidget(title)
        layout.addWidget(header)

        # Project Info
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        proj_name = QLabel("FirePreview Project")
        proj_name.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        proj_date = QLabel("更新: 2023/10/24 14:20")
        proj_date.setStyleSheet("color: #888899; font-size: 11px;")
        info_layout.addWidget(proj_name)
        info_layout.addWidget(proj_date)
        layout.addWidget(info_widget)

        # Tabs (Page vs Object)
        tab_layout = QHBoxLayout()
        tab_layout.setContentsMargins(10, 5, 10, 5)
        
        self.page_tab_btn = QPushButton("ページ")
        self.page_tab_btn.setCheckable(True)
        self.page_tab_btn.setChecked(True)
        self.page_tab_btn.setStyleSheet(
            "QPushButton { background-color: #7c4dff; color: white; border-radius: 4px; padding: 5px; font-weight: bold; border: none; }"
        )
        
        self.obj_tab_btn = QPushButton("オブジェクト")
        self.obj_tab_btn.setCheckable(True)
        self.obj_tab_btn.setStyleSheet(
            "QPushButton { background-color: #2a2a3d; color: #888899; border-radius: 4px; padding: 5px; border: none; }"
        )

        self.summary_tab_btn = QPushButton("集計")
        self.summary_tab_btn.setCheckable(True)
        self.summary_tab_btn.setStyleSheet(
            "QPushButton { background-color: #2a2a3d; color: #888899; border-radius: 4px; padding: 5px; border: none; }"
        )
        
        tab_layout.addWidget(self.page_tab_btn)
        tab_layout.addWidget(self.obj_tab_btn)
        tab_layout.addWidget(self.summary_tab_btn)
        layout.addLayout(tab_layout)
        
        # Connect tab buttons
        self.page_tab_btn.clicked.connect(self.show_page_tab)
        self.obj_tab_btn.clicked.connect(self.show_obj_tab)
        self.summary_tab_btn.clicked.connect(self.show_summary_tab)

        # Stacked Widget for Page thumbnails vs Object list
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)
        
        # --- TAB 1: Pages Thumbnail Area ---
        pages_widget = QWidget()
        pages_layout = QVBoxLayout(pages_widget)
        pages_layout.setContentsMargins(0, 0, 0, 0)
        pages_layout.setSpacing(0)
        
        # Pages Header
        pages_header = QHBoxLayout()
        pages_header.setContentsMargins(10, 10, 10, 5)
        pages_label = QLabel("PAGES")
        pages_label.setStyleSheet("color: #888899; font-size: 10px; font-weight: bold;")
        page_count = QLabel("0")
        page_count.setObjectName("pageCountLabel")
        page_count.setStyleSheet("color: #888899; font-size: 10px;")
        pages_header.addWidget(pages_label)
        pages_header.addStretch()
        pages_header.addWidget(page_count)
        pages_layout.addLayout(pages_header)

        # Thumbnail Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_content = QWidget()
        self.thumbnails_layout = QVBoxLayout(self.scroll_content)
        self.thumbnails_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.scroll_content)
        pages_layout.addWidget(self.scroll_area)
        
        self.stacked_widget.addWidget(pages_widget)
        
        # --- TAB 2: Object List Area ---
        obj_widget = QWidget()
        obj_layout = QVBoxLayout(obj_widget)
        obj_layout.setContentsMargins(0, 0, 0, 0)
        obj_layout.setSpacing(0)
        
        # Object Header
        obj_header = QHBoxLayout()
        obj_header.setContentsMargins(10, 10, 10, 5)
        obj_label = QLabel("OBJECTS")
        obj_label.setStyleSheet("color: #888899; font-size: 10px; font-weight: bold;")
        self.obj_count_label = QLabel("0")
        self.obj_count_label.setStyleSheet("color: #888899; font-size: 10px;")
        obj_header.addWidget(obj_label)
        obj_header.addStretch()
        obj_header.addWidget(self.obj_count_label)
        obj_layout.addLayout(obj_header)
        
        # Object Scroll Area
        self.obj_scroll = QScrollArea()
        self.obj_scroll.setWidgetResizable(True)
        self.obj_scroll.setFrameShape(QFrame.NoFrame)
        self.obj_scroll_content = QWidget()
        self.obj_layout = QVBoxLayout(self.obj_scroll_content)
        self.obj_layout.setAlignment(Qt.AlignTop)
        self.obj_layout.setContentsMargins(5, 5, 5, 5)
        self.obj_layout.setSpacing(4)
        self.obj_scroll.setWidget(self.obj_scroll_content)
        obj_layout.addWidget(self.obj_scroll)
        
        self.stacked_widget.addWidget(obj_widget)

        # --- TAB 3: Summary Area ---
        summary_widget = QWidget()
        summary_layout = QVBoxLayout(summary_widget)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(0)
        
        # Summary Header
        sum_header = QHBoxLayout()
        sum_header.setContentsMargins(10, 10, 10, 5)
        sum_label = QLabel("集計（ページ内）")
        sum_label.setStyleSheet("color: #888899; font-size: 10px; font-weight: bold;")
        self.sum_count_label = QLabel("0")
        self.sum_count_label.setStyleSheet("color: #888899; font-size: 10px;")
        sum_header.addWidget(sum_label)
        sum_header.addStretch()
        sum_header.addWidget(self.sum_count_label)
        summary_layout.addLayout(sum_header)
        
        # Scroll Area
        self.sum_scroll = QScrollArea()
        self.sum_scroll.setWidgetResizable(True)
        self.sum_scroll.setFrameShape(QFrame.NoFrame)
        self.sum_scroll_content = QWidget()
        self.sum_layout = QVBoxLayout(self.sum_scroll_content)
        self.sum_layout.setAlignment(Qt.AlignTop)
        self.sum_layout.setContentsMargins(10, 5, 10, 5)
        self.sum_layout.setSpacing(8)
        self.sum_scroll.setWidget(self.sum_scroll_content)
        summary_layout.addWidget(self.sum_scroll)
        
        self.stacked_widget.addWidget(summary_widget)

    def show_page_tab(self):
        self.page_tab_btn.setChecked(True)
        self.page_tab_btn.setStyleSheet(
            "QPushButton { background-color: #7c4dff; color: white; border-radius: 4px; padding: 5px; font-weight: bold; border: none; }"
        )
        self.obj_tab_btn.setChecked(False)
        self.obj_tab_btn.setStyleSheet(
            "QPushButton { background-color: #2a2a3d; color: #888899; border-radius: 4px; padding: 5px; border: none; }"
        )
        self.summary_tab_btn.setChecked(False)
        self.summary_tab_btn.setStyleSheet(
            "QPushButton { background-color: #2a2a3d; color: #888899; border-radius: 4px; padding: 5px; border: none; }"
        )
        self.stacked_widget.setCurrentIndex(0)

    def show_obj_tab(self):
        self.page_tab_btn.setChecked(False)
        self.page_tab_btn.setStyleSheet(
            "QPushButton { background-color: #2a2a3d; color: #888899; border-radius: 4px; padding: 5px; border: none; }"
        )
        self.obj_tab_btn.setChecked(True)
        self.obj_tab_btn.setStyleSheet(
            "QPushButton { background-color: #7c4dff; color: white; border-radius: 4px; padding: 5px; font-weight: bold; border: none; }"
        )
        self.summary_tab_btn.setChecked(False)
        self.summary_tab_btn.setStyleSheet(
            "QPushButton { background-color: #2a2a3d; color: #888899; border-radius: 4px; padding: 5px; border: none; }"
        )
        self.stacked_widget.setCurrentIndex(1)

    def show_summary_tab(self):
        self.page_tab_btn.setChecked(False)
        self.page_tab_btn.setStyleSheet(
            "QPushButton { background-color: #2a2a3d; color: #888899; border-radius: 4px; padding: 5px; border: none; }"
        )
        self.obj_tab_btn.setChecked(False)
        self.obj_tab_btn.setStyleSheet(
            "QPushButton { background-color: #2a2a3d; color: #888899; border-radius: 4px; padding: 5px; border: none; }"
        )
        self.summary_tab_btn.setChecked(True)
        self.summary_tab_btn.setStyleSheet(
            "QPushButton { background-color: #7c4dff; color: white; border-radius: 4px; padding: 5px; font-weight: bold; border: none; }"
        )
        self.stacked_widget.setCurrentIndex(2)

    def update_marker_summary(self, annotations, current_page):
        # 1. Clear existing summary items
        for i in reversed(range(self.sum_layout.count())):
            widget = self.sum_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
                
        # 2. Count markers by type and color (only for current_page)
        marker_counts = {} # {(marker_style, color): count}
        total_markers = 0
        
        for ann in annotations:
            if ann.type == 'marker' and ann.page_num == current_page:
                style = getattr(ann, 'marker_style', 'square')
                color = (ann.color or "#7c4dff").lower()
                key = (style, color)
                marker_counts[key] = marker_counts.get(key, 0) + 1
                total_markers += 1
                
        self.sum_count_label.setText(str(total_markers))
        
        if total_markers == 0:
            empty_lbl = QLabel("このページにマーカーは\n配置されていません。")
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setStyleSheet("color: #888899; font-size: 12px; margin-top: 50px; line-height: 1.5;")
            self.sum_layout.addWidget(empty_lbl)
            return
            
        # 3. Categorize and render
        styles_ja = {"square": "四角形マーカー", "check": "チェックマーク"}
        palette_color_names = {
            "#ff1744": "赤", "#2979ff": "青", "#00e676": "緑", "#ffd600": "黄", 
            "#ff9100": "橙", "#f50057": "桃", "#d500f9": "紫", "#8d6e63": "茶", 
            "#00e5ff": "水色", "#aeea00": "黄緑", "#7c4dff": "紫"
        }
        
        for style_key in ["square", "check"]:
            style_markers = {k: v for k, v in marker_counts.items() if k[0] == style_key}
            if not style_markers:
                continue
                
            # Section header
            sec_header = QLabel(styles_ja[style_key])
            sec_header.setStyleSheet("color: #7c4dff; font-weight: bold; font-size: 11px; margin-top: 10px; border-bottom: 1px solid #334;")
            self.sum_layout.addWidget(sec_header)
            
            # Sort by count (descending)
            for (st, col), count in sorted(style_markers.items(), key=lambda x: x[1], reverse=True):
                row = QFrame()
                row.setStyleSheet("background-color: #2a2a3d; border-radius: 4px; padding: 4px;")
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(6, 4, 6, 4)
                
                # Color indicator
                color_dot = QFrame()
                color_dot.setFixedSize(12, 12)
                color_dot.setStyleSheet(f"background-color: {col}; border-radius: 6px;")
                row_layout.addWidget(color_dot)
                
                # Color name / Hex
                c_name = palette_color_names.get(col.lower(), col.upper())
                lbl_text = QLabel(f"{c_name}")
                lbl_text.setStyleSheet("color: #ffffff; font-size: 12px;")
                row_layout.addWidget(lbl_text)
                
                row_layout.addStretch()
                
                # Count label
                lbl_count = QLabel(f"{count} 個")
                lbl_count.setStyleSheet("color: #00e676; font-weight: bold; font-size: 12px;")
                row_layout.addWidget(lbl_count)
                
                self.sum_layout.addWidget(row)

    def set_page_count(self, count):
        label = self.findChild(QLabel, "pageCountLabel")
        if label:
            label.setText(str(count))

    def update_thumbnails(self, pixmaps):
        # Clear existing
        for i in reversed(range(self.thumbnails_layout.count())): 
            self.thumbnails_layout.itemAt(i).widget().setParent(None)
        
        for i, pix in enumerate(pixmaps):
            thumb = PageThumbnail(i, pix)
            thumb.clicked.connect(self.page_changed.emit)
            self.thumbnails_layout.addWidget(thumb)

    def update_objects(self, annotations):
        # 1. Update the objects count label
        self.obj_count_label.setText(str(len(annotations)))
        
        # 2. Get the new set of IDs
        new_ids = {ann.id for ann in annotations}
        
        # 3. Identify and remove rows that are no longer present
        removed_ids = set(self.rows.keys()) - new_ids
        for rid in removed_ids:
            row = self.rows.pop(rid)
            self.obj_layout.removeWidget(row)
            row.setParent(None)
            row.deleteLater()
            
        # 4. Update existing or add new rows, ensuring correct order in the layout
        for index, ann in enumerate(annotations):
            is_editing = (self.active_edit_id == ann.id)
            is_selected = (self.selected_id == ann.id)
            
            if ann.id in self.rows:
                # Existing row
                row = self.rows[ann.id]
                # Update display values on existing row if they changed
                row.update_properties(ann, is_editing=is_editing, selected=is_selected)
                # Reposition row widget to preserve exact ordering (very fast in Qt)
                self.obj_layout.insertWidget(index, row)
            else:
                # New row
                row = ObjectItemRow(ann, is_editing=is_editing)
                row.clicked.connect(self.object_selected.emit)
                row.edit_toggled.connect(self.object_edit_toggled.emit)
                self.obj_layout.insertWidget(index, row)
                self.rows[ann.id] = row

    def set_selected_object(self, item_id):
        # O(1) selection update: only repaint previously selected and newly selected rows
        previous_selected_id = self.selected_id
        self.selected_id = item_id
        
        affected_ids = set()
        if previous_selected_id:
            affected_ids.add(previous_selected_id)
        if item_id:
            affected_ids.add(item_id)
            
        for rid in affected_ids:
            row = self.rows.get(rid)
            if row:
                row.apply_styles(rid == item_id)

    def set_editing_object(self, item_id, is_editing):
        previous_edit_id = self.active_edit_id
        
        if is_editing:
            self.active_edit_id = item_id
        else:
            if self.active_edit_id == item_id:
                self.active_edit_id = None
                
        # O(1) edit state update: only repaint previously editing and newly editing rows
        affected_ids = set()
        if previous_edit_id:
            affected_ids.add(previous_edit_id)
        if item_id:
            affected_ids.add(item_id)
            
        for rid in affected_ids:
            row = self.rows.get(rid)
            if row:
                row_is_editing = (self.active_edit_id == rid)
                row_is_selected = (rid == self.selected_id) or (rid == item_id and is_editing)
                row.set_editing_state(row_is_editing, row_is_selected)

class PageThumbnail(QFrame):
    clicked = Signal(int)

    def __init__(self, index, pixmap, parent=None):
        super().__init__(parent)
        self.index = index
        self.setFixedSize(180, 140)
        self.setStyleSheet("QFrame { background-color: #2a2a3d; border: 2px solid transparent; border-radius: 4px; }")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        img_label = QLabel()
        scaled_pix = pixmap.scaled(170, 110, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        img_label.setPixmap(scaled_pix)
        img_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(img_label)
        
        footer = QHBoxLayout()
        idx_label = QLabel(str(index + 1))
        idx_label.setStyleSheet("background-color: #7c4dff; color: white; border-radius: 2px; padding: 0 4px; font-size: 10px;")
        footer.addStretch()
        footer.addWidget(idx_label)
        layout.addLayout(footer)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.index)
            self.setStyleSheet("QFrame { background-color: #2a2a3d; border: 2px solid #7c4dff; border-radius: 4px; }")

class ObjectItemRow(QFrame):
    clicked = Signal(str)  # item_id
    edit_toggled = Signal(str, bool)  # item_id, is_active

    def __init__(self, annotation, is_editing=False, parent=None):
        super().__init__(parent)
        self.annotation_id = annotation.id
        self.is_editing = is_editing
        
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        self.setup_ui(annotation)
        self.apply_styles(False)

    def setup_ui(self, ann):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # 1. Icon according to type
        self.icon_label = QLabel()
        self.current_type = ann.type
        self.current_color = ann.color
        icon = self.get_icon_for_type(ann.type, ann.color)
        self.icon_label.setPixmap(icon.pixmap(16, 16))
        layout.addWidget(self.icon_label)
        
        # 2. Text (Type & value)
        display_text = self.get_display_text(ann)
        self.text_label = QLabel(display_text)
        self.text_label.setStyleSheet("color: #ffffff; font-size: 12px;")
        layout.addWidget(self.text_label)
        layout.addStretch()
        
        # 3. Edit/Done Button
        self.edit_btn = QPushButton()
        self.edit_btn.setFixedSize(24, 24)
        self.edit_btn.setCursor(Qt.PointingHandCursor)
        self.update_edit_button_state()
            
        self.edit_btn.clicked.connect(self.on_edit_clicked)
        layout.addWidget(self.edit_btn)

    def update_edit_button_state(self):
        if self.is_editing:
            # Done state
            self.edit_btn.setIcon(qta.icon('fa5s.check', color='#ffffff'))
            self.edit_btn.setStyleSheet(
                "QPushButton { background-color: #2e7d32; border: none; border-radius: 4px; }"
                "QPushButton:hover { background-color: #388e3c; }"
            )
            self.edit_btn.setToolTip("編集完了")
        else:
            # Edit state
            self.edit_btn.setIcon(qta.icon('fa5s.pencil-alt', color='#ffffff'))
            self.edit_btn.setStyleSheet(
                "QPushButton { background-color: #2a2a3d; border: 1px solid #555566; border-radius: 4px; }"
                "QPushButton:hover { background-color: #7c4dff; border-color: #7c4dff; }"
            )
            self.edit_btn.setToolTip("オブジェクトを編集")

    def set_editing_state(self, is_editing, selected):
        self.is_editing = is_editing
        self.update_edit_button_state()
        self.apply_styles(selected)

    def update_properties(self, ann, is_editing=False, selected=False):
        # 1. Type or color changed -> update icon
        if self.current_type != ann.type or self.current_color != ann.color:
            self.current_type = ann.type
            self.current_color = ann.color
            icon = self.get_icon_for_type(ann.type, ann.color)
            self.icon_label.setPixmap(icon.pixmap(16, 16))
            
        # 2. Display text changed -> update text label
        display_text = self.get_display_text(ann)
        if self.text_label.text() != display_text:
            self.text_label.setText(display_text)
            
        # 3. Editing/Selection state changed
        self.set_editing_state(is_editing, selected)

    def get_icon_for_type(self, type_str, color_hex):
        color = QColor(color_hex)
        if type_str == 'line':
            return qta.icon('fa5s.ruler', color=color)
        elif type_str == 'polyline':
            return qta.icon('fa5s.pencil-alt', color=color)
        elif type_str == 'polygon':
            return qta.icon('fa5s.square', color=color)
        elif type_str == 'circle':
            return qta.icon('fa5s.circle', color=color)
        elif type_str == 'text':
            return qta.icon('fa5s.font', color=color)
        elif type_str == 'marker':
            return qta.icon('fa5s.map-marker-alt', color=color)
        return qta.icon('fa5s.question', color=color)

    def get_display_text(self, ann):
        type_ja = {
            'line': '計測ライン',
            'polyline': '直線',
            'polygon': '多角形',
            'circle': '円',
            'text': 'テキスト',
            'marker': 'マーカー'
        }.get(ann.type, 'オブジェクト')
        
        if ann.type == 'marker':
            styles_ja = {"square": "四角形", "check": "チェック"}
            style_name = styles_ja.get(getattr(ann, 'marker_style', 'square'), "マーカー")
            palette_color_names = {
                "#ff1744": "赤", "#2979ff": "青", "#00e676": "緑", "#ffd600": "黄", 
                "#ff9100": "橙", "#f50057": "桃", "#d500f9": "紫", "#8d6e63": "茶", 
                "#00e5ff": "水色", "#aeea00": "黄緑", "#7c4dff": "紫"
            }
            color_str = ann.color or "#7c4dff"
            c_name = palette_color_names.get(color_str.lower(), color_str.upper())
            return f"マーカー ({style_name} - {c_name})"
        elif ann.type == 'text':
            content = ann.text.strip()
            if len(content) > 10:
                content = content[:10] + "..."
            return f"{type_ja}: '{content}'" if content else type_ja
        elif ann.text:
            return f"{type_ja} ({ann.text})"
        return type_ja

    def apply_styles(self, selected):
        if selected:
            self.setStyleSheet(
                "QFrame { background-color: #3d2b6b; border: 1px solid #7c4dff; border-radius: 4px; }"
            )
        elif self.is_editing:
            self.setStyleSheet(
                "QFrame { background-color: #1b3d22; border: 1px solid #2e7d32; border-radius: 4px; }"
            )
        else:
            self.setStyleSheet(
                "QFrame { background-color: #2a2a3d; border: 1px solid transparent; border-radius: 4px; }"
                "QFrame:hover { background-color: #383854; border-color: #555566; }"
            )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.annotation_id)

    def on_edit_clicked(self):
        # Toggle edit state
        self.edit_toggled.emit(self.annotation_id, not self.is_editing)
