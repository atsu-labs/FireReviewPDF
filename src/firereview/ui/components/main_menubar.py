from PySide6.QtWidgets import QMenuBar
from PySide6.QtGui import QAction
from PySide6.QtCore import Signal
import qtawesome as qta


class MainMenuBar(QMenuBar):
    open_pdf_requested = Signal()
    swap_pdf_requested = Signal()
    save_project_requested = Signal()
    save_project_as_requested = Signal()
    load_project_requested = Signal()
    export_pdf_requested = Signal()
    preferences_requested = Signal()

    # 編集操作シグナル
    undo_requested = Signal()
    redo_requested = Signal()

    # ビュー・ページ操作シグナル
    zoom_in_requested = Signal()
    zoom_out_requested = Signal()
    fit_to_page_requested = Signal()
    actual_size_requested = Signal()
    prev_page_requested = Signal()
    next_page_requested = Signal()

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

        save_as_action = QAction("名前を付けて保存...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_project_as_requested.emit)
        file_menu.addAction(save_as_action)

        load_action = QAction("プロジェクトを読み込み", self)
        load_action.setShortcut("Ctrl+L")
        load_action.triggered.connect(self.load_project_requested.emit)
        file_menu.addAction(load_action)

        file_menu.addSeparator()

        export_action = QAction("PDFを書き出し", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_pdf_requested.emit)
        file_menu.addAction(export_action)

        # 編集メニュー
        edit_menu = self.addMenu("編集")

        self.undo_action = QAction("元に戻す", self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.setEnabled(False)
        self.undo_action.triggered.connect(self.undo_requested.emit)
        edit_menu.addAction(self.undo_action)

        self.redo_action = QAction("やり直す", self)
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.setEnabled(False)
        self.redo_action.triggered.connect(self.redo_requested.emit)
        edit_menu.addAction(self.redo_action)

        # 表示メニュー
        view_menu = self.addMenu("表示")

        zoom_in_action = QAction("拡大", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self.zoom_in_requested.emit)
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("縮小", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.zoom_out_requested.emit)
        view_menu.addAction(zoom_out_action)

        view_menu.addSeparator()

        fit_page_action = QAction("ページ全体を表示", self)
        fit_page_action.setShortcut("Ctrl+0")
        fit_page_action.triggered.connect(self.fit_to_page_requested.emit)
        view_menu.addAction(fit_page_action)

        actual_size_action = QAction("100% 実寸大表示", self)
        actual_size_action.setShortcut("Ctrl+1")
        actual_size_action.triggered.connect(self.actual_size_requested.emit)
        view_menu.addAction(actual_size_action)

        view_menu.addSeparator()

        prev_page_action = QAction("前のページ", self)
        prev_page_action.setShortcut("PageUp")
        prev_page_action.triggered.connect(self.prev_page_requested.emit)
        view_menu.addAction(prev_page_action)

        next_page_action = QAction("次のページ", self)
        next_page_action.setShortcut("PageDown")
        next_page_action.triggered.connect(self.next_page_requested.emit)
        view_menu.addAction(next_page_action)

        # 設定メニュー
        settings_menu = self.addMenu("設定")
        pref_action = QAction(qta.icon('fa5s.cog', color='white'), "環境設定...", self)
        pref_action.setShortcut("Ctrl+,")
        pref_action.triggered.connect(self.preferences_requested.emit)
        settings_menu.addAction(pref_action)

    def set_undo_enabled(self, enabled: bool):
        self.undo_action.setEnabled(enabled)

    def set_redo_enabled(self, enabled: bool):
        self.redo_action.setEnabled(enabled)

