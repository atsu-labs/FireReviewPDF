import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QColor
from firereview.ui.panels.navigator_panel import NavigatorPanel, PageThumbnail
from firereview.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def create_dummy_pixmap(width=100, height=100, color=Qt.white):
    pix = QPixmap(width, height)
    pix.fill(color)
    return pix


class TestPageThumbnailSelection:
    def test_initial_unselected_state(self, qapp):
        pix = create_dummy_pixmap()
        thumb = PageThumbnail(0, pix)
        assert thumb._is_selected is False
        assert "border: 2px solid transparent" in thumb.styleSheet()

    def test_set_selected_toggle(self, qapp):
        pix = create_dummy_pixmap()
        thumb = PageThumbnail(0, pix)

        thumb.set_selected(True)
        assert thumb._is_selected is True
        assert "border: 2px solid #7c4dff" in thumb.styleSheet()

        thumb.set_selected(False)
        assert thumb._is_selected is False
        assert "border: 2px solid transparent" in thumb.styleSheet()


class TestNavigatorPanelPageSelection:
    def test_single_selection_exclusive(self, qapp):
        nav = NavigatorPanel()
        pixmaps = [create_dummy_pixmap() for _ in range(3)]
        nav.update_thumbnails(pixmaps)

        assert len(nav.page_thumbnails) == 3

        # 0ページ目を選択
        nav.set_selected_page(0)
        assert nav.selected_page_index == 0
        assert nav.page_thumbnails[0]._is_selected is True
        assert nav.page_thumbnails[1]._is_selected is False
        assert nav.page_thumbnails[2]._is_selected is False

        # 1ページ目を選択 -> 0ページ目が解除されること
        nav.set_selected_page(1)
        assert nav.selected_page_index == 1
        assert nav.page_thumbnails[0]._is_selected is False
        assert nav.page_thumbnails[1]._is_selected is True
        assert nav.page_thumbnails[2]._is_selected is False

        # 2ページ目を選択 -> 1ページ目が解除されること
        nav.set_selected_page(2)
        assert nav.selected_page_index == 2
        assert nav.page_thumbnails[0]._is_selected is False
        assert nav.page_thumbnails[1]._is_selected is False
        assert nav.page_thumbnails[2]._is_selected is True

    def test_thumbnail_click_triggers_selection_and_signal(self, qapp):
        nav = NavigatorPanel()
        pixmaps = [create_dummy_pixmap() for _ in range(3)]
        nav.update_thumbnails(pixmaps)

        emitted_pages = []
        nav.page_changed.connect(lambda p: emitted_pages.append(p))

        # サムネイル0をクリック
        nav.page_thumbnails[0].clicked.emit(0)
        assert emitted_pages == [0]
        assert nav.selected_page_index == 0
        assert nav.page_thumbnails[0]._is_selected is True
        assert nav.page_thumbnails[1]._is_selected is False

        # 続いてサムネイル1をクリック
        nav.page_thumbnails[1].clicked.emit(1)
        assert emitted_pages == [0, 1]
        assert nav.selected_page_index == 1
        assert nav.page_thumbnails[0]._is_selected is False
        assert nav.page_thumbnails[1]._is_selected is True


class TestMainWindowNavigatorSync:
    def test_main_window_go_to_page_syncs_navigator(self, qapp):
        win = MainWindow()
        pixmaps = [create_dummy_pixmap() for _ in range(2)]
        win.navigator.update_thumbnails(pixmaps)

        win.go_to_page(1)
        assert win.current_page == 1
        assert win.navigator.selected_page_index == 1
        assert win.navigator.page_thumbnails[1]._is_selected is True
        assert win.navigator.page_thumbnails[0]._is_selected is False
        win.close()
