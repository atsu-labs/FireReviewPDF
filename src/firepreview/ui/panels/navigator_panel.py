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
        
        tab_layout.addWidget(self.page_tab_btn)
        tab_layout.addWidget(self.obj_tab_btn)
        layout.addLayout(tab_layout)
        
        # Connect tab buttons
        self.page_tab_btn.clicked.connect(self.show_page_tab)
        self.obj_tab_btn.clicked.connect(self.show_obj_tab)

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

    def show_page_tab(self):
        self.page_tab_btn.setChecked(True)
        self.page_tab_btn.setStyleSheet(
            "QPushButton { background-color: #7c4dff; color: white; border-radius: 4px; padding: 5px; font-weight: bold; border: none; }"
        )
        self.obj_tab_btn.setChecked(False)
        self.obj_tab_btn.setStyleSheet(
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
        self.stacked_widget.setCurrentIndex(1)

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
        # Clear existing
        for i in reversed(range(self.obj_layout.count())): 
            widget = self.obj_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        
        self.obj_count_label.setText(str(len(annotations)))
        
        self.rows = {}
        for ann in annotations:
            is_editing = (self.active_edit_id == ann.id)
            row = ObjectItemRow(ann, is_editing=is_editing)
            row.clicked.connect(self.object_selected.emit)
            row.edit_toggled.connect(self.object_edit_toggled.emit)
            self.obj_layout.addWidget(row)
            self.rows[ann.id] = row

    def set_selected_object(self, item_id):
        # Clear all selections
        for rid, row in self.rows.items():
            row.apply_styles(rid == item_id)

    def set_editing_object(self, item_id, is_editing):
        if is_editing:
            self.active_edit_id = item_id
        else:
            if self.active_edit_id == item_id:
                self.active_edit_id = None
                
        # Re-apply styles/state to all rows
        for rid, row in self.rows.items():
            if rid == item_id:
                row.is_editing = is_editing
                if is_editing:
                    row.edit_btn.setIcon(qta.icon('fa5s.check', color='#ffffff'))
                    row.edit_btn.setStyleSheet(
                        "QPushButton { background-color: #2e7d32; border: none; border-radius: 4px; }"
                        "QPushButton:hover { background-color: #388e3c; }"
                    )
                    row.edit_btn.setToolTip("編集完了")
                else:
                    row.edit_btn.setIcon(qta.icon('fa5s.pencil-alt', color='#ffffff'))
                    row.edit_btn.setStyleSheet(
                        "QPushButton { background-color: #2a2a3d; border: 1px solid #555566; border-radius: 4px; }"
                        "QPushButton:hover { background-color: #7c4dff; border-color: #7c4dff; }"
                    )
                    row.edit_btn.setToolTip("オブジェクトを編集")
            else:
                row.is_editing = False
                row.edit_btn.setIcon(qta.icon('fa5s.pencil-alt', color='#ffffff'))
                row.edit_btn.setStyleSheet(
                    "QPushButton { background-color: #2a2a3d; border: 1px solid #555566; border-radius: 4px; }"
                    "QPushButton:hover { background-color: #7c4dff; border-color: #7c4dff; }"
                )
                row.edit_btn.setToolTip("オブジェクトを編集")
            row.apply_styles(rid == item_id)

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
        icon_label = QLabel()
        icon = self.get_icon_for_type(ann.type, ann.color)
        icon_label.setPixmap(icon.pixmap(16, 16))
        layout.addWidget(icon_label)
        
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
            
        self.edit_btn.clicked.connect(self.on_edit_clicked)
        layout.addWidget(self.edit_btn)

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
        return qta.icon('fa5s.question', color=color)

    def get_display_text(self, ann):
        type_ja = {
            'line': '計測ライン',
            'polyline': '直線',
            'polygon': '多角形',
            'circle': '円',
            'text': 'テキスト'
        }.get(ann.type, 'オブジェクト')
        
        if ann.type == 'text':
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
