from PySide6.QtWidgets import QMenuBar
from PySide6.QtGui import QAction
from PySide6.QtCore import Signal

class MainMenuBar(QMenuBar):
    open_pdf_requested = Signal()
    swap_pdf_requested = Signal()
    save_project_requested = Signal()
    load_project_requested = Signal()
    export_pdf_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QMenuBar { background-color: #151521; color: #ffffff; border-bottom: 1px solid #333344; } "
            "QMenuBar::item:selected { background-color: #2a2a3d; }"
        )
        self._setup_menus()

    def _setup_menus(self):
        file_menu = self.addMenu("ファイル")
        
        open_action = QAction("PDF図面を開く", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_pdf_requested.emit)
        file_menu.addAction(open_action)

        swap_action = QAction("背景PDFを差し替え", self)
        swap_action.triggered.connect(self.swap_pdf_requested.emit)
        file_menu.addAction(swap_action)

        file_menu.addSeparator()

        save_action = QAction("プロジェクトを保存", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_project_requested.emit)
        file_menu.addAction(save_action)

        load_action = QAction("プロジェクトを読み込み", self)
        load_action.setShortcut("Ctrl+L")
        load_action.triggered.connect(self.load_project_requested.emit)
        file_menu.addAction(load_action)

        file_menu.addSeparator()

        export_action = QAction("PDFを書き出し", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_pdf_requested.emit)
        file_menu.addAction(export_action)
