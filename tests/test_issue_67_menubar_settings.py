import pytest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QKeySequence
from firereview.ui.components.main_menubar import MainMenuBar
from firereview.ui.components.main_toolbar import MainToolBar
from firereview.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestMainMenuBarSettings:
    def test_settings_menu_and_preferences_action(self, qapp):
        menubar = MainMenuBar()

        # 「設定」メニューの存在確認
        menus = [action.text() for action in menubar.actions()]
        assert "設定" in menus

        # 設定メニュー内の「環境設定...」アクション確認
        settings_menu = None
        for action in menubar.actions():
            if action.text() == "設定":
                settings_menu = action.menu()
                break
        assert settings_menu is not None

        pref_action = None
        for act in settings_menu.actions():
            if act.text() == "環境設定...":
                pref_action = act
                break
        assert pref_action is not None

        # ショートカット Ctrl+, の確認
        assert pref_action.shortcut() == QKeySequence("Ctrl+,")
        # アイコンが設定されていること
        assert not pref_action.icon().isNull()

        # シグナル発行の確認
        emitted = []
        menubar.preferences_requested.connect(lambda: emitted.append(True))
        pref_action.trigger()
        assert len(emitted) == 1


class TestMainToolBarQuickActions:
    def test_quick_action_buttons_exist_and_emit_signals(self, qapp):
        toolbar = MainToolBar()
        assert len(toolbar.quick_action_btns) == 3

        open_emitted = []
        save_emitted = []
        export_emitted = []

        toolbar.open_pdf_requested.connect(lambda: open_emitted.append(True))
        toolbar.save_project_requested.connect(lambda: save_emitted.append(True))
        toolbar.export_pdf_requested.connect(lambda: export_emitted.append(True))

        # 0: Open, 1: Save, 2: Export
        toolbar.quick_action_btns[0].click()
        assert len(open_emitted) == 1

        toolbar.quick_action_btns[1].click()
        assert len(save_emitted) == 1

        toolbar.quick_action_btns[2].click()
        assert len(export_emitted) == 1


class TestMainWindowLayoutAndConnections:
    def test_header_removed_and_toolbar_at_top(self, qapp):
        win = MainWindow()

        # メニューバーが存在すること
        assert isinstance(win.menuBar(), MainMenuBar)

        # central_widget のレイアウトの1番目のウィジェットが MainToolBar であること（ヘッダーなし）
        first_widget = win.main_layout.itemAt(0).widget()
        assert isinstance(first_widget, MainToolBar)
        assert first_widget == win.toolbar

        # ヘッダーオブジェクト (MainHeader) が存在しないこと
        for i in range(win.main_layout.count()):
            item = win.main_layout.itemAt(i)
            if item.widget():
                assert item.widget().objectName() != "MainHeader"

        # メニューバーの preferences_requested が接続されていること
        open_pref_mock = MagicMock()
        win._open_preferences_dialog = open_pref_mock
        win.menubar.preferences_requested.emit()
        assert open_pref_mock.called is True

        # ツールバーのクイックアクションが MainWindow の対応スロットに接続されていること
        open_pdf_mock = MagicMock()
        save_proj_mock = MagicMock()
        export_pdf_mock = MagicMock()

        win.open_pdf = open_pdf_mock
        win.save_project = save_proj_mock
        win.export_pdf = export_pdf_mock

        win.toolbar.open_pdf_requested.emit()
        assert open_pdf_mock.called is True

        win.toolbar.save_project_requested.emit()
        assert save_proj_mock.called is True

        win.toolbar.export_pdf_requested.emit()
        assert export_pdf_mock.called is True

        win.close()
