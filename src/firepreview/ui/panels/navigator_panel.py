from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, 
                             QFrame, QHBoxLayout)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap

class NavigatorPanel(QWidget):
    page_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
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

        # Tabs
        tab_layout = QHBoxLayout()
        tab_layout.setContentsMargins(10, 5, 10, 5)
        page_tab = QLabel("ページ")
        page_tab.setAlignment(Qt.AlignCenter)
        page_tab.setStyleSheet("background-color: #7c4dff; color: white; border-radius: 4px; padding: 5px;")
        hist_tab = QLabel("履歴")
        hist_tab.setAlignment(Qt.AlignCenter)
        hist_tab.setStyleSheet("background-color: #2a2a3d; color: #888899; border-radius: 4px; padding: 5px;")
        tab_layout.addWidget(page_tab)
        tab_layout.addWidget(hist_tab)
        layout.addLayout(tab_layout)

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
        layout.addLayout(pages_header)

        # Thumbnail Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_content = QWidget()
        self.thumbnails_layout = QVBoxLayout(self.scroll_content)
        self.thumbnails_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)

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
