import pytest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication, QLineEdit
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QKeyEvent, QKeySequence, QPixmap
from firereview.ui.canvas.view import PDFCanvas, ToolMode
from firereview.ui.components.main_menubar import MainMenuBar
from firereview.ui.components.main_toolbar import MainToolBar
from firereview.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def send_key(widget, key, modifiers=Qt.NoModifier, key_type=QKeyEvent.Type.KeyPress):
    ev = QKeyEvent(key_type, key, modifiers)
    if key_type == QKeyEvent.Type.KeyPress:
        widget.keyPressEvent(ev)
    else:
        widget.keyReleaseEvent(ev)


class TestCanvasKeyboardShortcuts:
    def test_delete_key_removes_selected_item(self, qapp):
        canvas = PDFCanvas()
        canvas.set_tool_mode(ToolMode.SELECT)
        pix = QPixmap(200, 200)
        pix.fill(Qt.white)
        canvas.set_page_image(pix)

        canvas.add_line_annotation(QPointF(10, 10), QPointF(50, 50), item_id="line_1")
        canvas.set_tool_mode(ToolMode.SELECT)
        item = canvas.annotation_items["line_1"]
        item.setSelected(True)

        emitted_ids = []
        canvas.request_delete.connect(lambda iid: emitted_ids.append(iid))

        send_key(canvas, Qt.Key_Delete)
        assert emitted_ids == ["line_1"]

    def test_delete_key_backspace_removes_selected_item(self, qapp):
        canvas = PDFCanvas()
        canvas.set_tool_mode(ToolMode.SELECT)
        pix = QPixmap(200, 200)
        pix.fill(Qt.white)
        canvas.set_page_image(pix)

        canvas.add_marker_annotation(QPointF(30, 30), item_id="marker_1")
        canvas.set_tool_mode(ToolMode.SELECT)
        item = canvas.annotation_items["marker_1"]
        item.setSelected(True)

        emitted_ids = []
        canvas.request_delete.connect(lambda iid: emitted_ids.append(iid))

        send_key(canvas, Qt.Key_Backspace)
        assert emitted_ids == ["marker_1"]

    def test_escape_multi_stage_cancel(self, qapp):
        canvas = PDFCanvas()
        pix = QPixmap(200, 200)
        pix.fill(Qt.white)
        canvas.set_page_image(pix)

        # 1. 描画ツール中の作図キャンセル (temp_points あり)
        canvas.set_tool_mode(ToolMode.DRAW_LINE)
        canvas.temp_points = [QPointF(10, 10)]
        send_key(canvas, Qt.Key_Escape)
        assert len(canvas.temp_points) == 0
        assert canvas.tool_mode == ToolMode.DRAW_LINE

        # 2. 描画ツールから選択ツールへの復帰
        tool_changed = []
        canvas.request_tool_change.connect(lambda m: tool_changed.append(m))
        send_key(canvas, Qt.Key_Escape)
        assert tool_changed == [ToolMode.SELECT]

        # 3. オブジェクト選択中の選択解除
        canvas.add_line_annotation(QPointF(10, 10), QPointF(50, 50), item_id="line_2")
        canvas.set_tool_mode(ToolMode.SELECT)
        canvas.annotation_items["line_2"].setSelected(True)
        assert len(canvas.scene.selectedItems()) > 0

        selection_cleared = []
        canvas.selection_cleared.connect(lambda: selection_cleared.append(True))
        send_key(canvas, Qt.Key_Escape)
        assert len(canvas.scene.selectedItems()) == 0
        assert len(selection_cleared) == 1

    def test_space_temporary_pan(self, qapp):
        canvas = PDFCanvas()
        canvas.set_tool_mode(ToolMode.DRAW_LINE)
        assert canvas.cursor().shape() == Qt.CrossCursor

        # Space キー押下
        send_key(canvas, Qt.Key_Space, key_type=QKeyEvent.Type.KeyPress)
        assert canvas._space_held is True
        assert canvas.cursor().shape() == Qt.OpenHandCursor

        # Space キー離下
        send_key(canvas, Qt.Key_Space, key_type=QKeyEvent.Type.KeyRelease)
        assert canvas._space_held is False
        assert canvas.cursor().shape() == Qt.CrossCursor

    def test_single_key_tool_switch(self, qapp):
        canvas = PDFCanvas()
        canvas.set_tool_mode(ToolMode.SELECT)

        tool_requests = []
        canvas.request_tool_change.connect(lambda m: tool_requests.append(m))

        key_cases = [
            (Qt.Key_H, ToolMode.NONE),
            (Qt.Key_L, ToolMode.DRAW_LINE),
            (Qt.Key_R, ToolMode.POLYGON_AREA),
            (Qt.Key_C, ToolMode.DRAW_CIRCLE_DRAG),
            (Qt.Key_T, ToolMode.TEXT),
            (Qt.Key_M, ToolMode.DRAW_MARKER),
            (Qt.Key_V, ToolMode.SELECT),
        ]

        for key, expected_mode in key_cases:
            send_key(canvas, key)
            assert tool_requests[-1] == expected_mode


class TestMainWindowNavigationAndShortcuts:
    def test_view_menu_actions_and_shortcuts(self, qapp):
        menubar = MainMenuBar()
        view_menu = None
        for act in menubar.actions():
            if act.text() == "表示":
                view_menu = act.menu()
                break
        assert view_menu is not None

        actions = {act.text(): act for act in view_menu.actions() if act.text()}
        assert "拡大" in actions
        assert actions["拡大"].shortcut() == QKeySequence("Ctrl++")

        assert "縮小" in actions
        assert actions["縮小"].shortcut() == QKeySequence("Ctrl+-")

        assert "ページ全体を表示" in actions
        assert actions["ページ全体を表示"].shortcut() == QKeySequence("Ctrl+0")

        assert "100% 実寸大表示" in actions
        assert actions["100% 実寸大表示"].shortcut() == QKeySequence("Ctrl+1")

        assert "前のページ" in actions
        assert actions["前のページ"].shortcut() == QKeySequence("PageUp")

        assert "次のページ" in actions
        assert actions["次のページ"].shortcut() == QKeySequence("PageDown")

    def test_toolbar_tooltips_contain_shortcuts(self, qapp):
        toolbar = MainToolBar()
        tips = [btn.toolTip() for btn in toolbar.tool_btns]
        assert "選択 (V)" in tips
        assert "パン (H)" in tips
        assert "直線（折れ線） (L)" in tips
        assert "矩形 (R)" in tips
        assert "円 (C)" in tips
        assert "テキスト (T)" in tips
        assert "マーカー (M)" in tips

    def test_main_window_shortcuts_and_guard(self, qapp):
        win = MainWindow()
        zoom_in_mock = MagicMock()
        zoom_out_mock = MagicMock()
        fit_page_mock = MagicMock()
        reset_zoom_mock = MagicMock()
        prev_page_mock = MagicMock()
        next_page_mock = MagicMock()

        win.zoom_in = zoom_in_mock
        win.zoom_out = zoom_out_mock
        win.fit_to_page = fit_page_mock
        win.reset_zoom_to_100 = reset_zoom_mock
        win.go_to_prev_page = prev_page_mock
        win.go_to_next_page = next_page_mock

        # メニューバーシグナル接続の確認
        win.menubar.zoom_in_requested.emit()
        assert zoom_in_mock.called is True

        win.menubar.zoom_out_requested.emit()
        assert zoom_out_mock.called is True

        win.menubar.fit_to_page_requested.emit()
        assert fit_page_mock.called is True

        win.menubar.actual_size_requested.emit()
        assert reset_zoom_mock.called is True

        win.menubar.prev_page_requested.emit()
        assert prev_page_mock.called is True

        win.menubar.next_page_requested.emit()
        assert next_page_mock.called is True

        # シングルキーガードの確認（QLineEdit にフォーカスがある場合はツール切替が動かない）
        edit = QLineEdit(win)
        win.set_tool(ToolMode.SELECT)
        edit.setFocus()
        initial_tool = win.canvas.tool_mode
        send_key(win, Qt.Key_L)
        assert win.canvas.tool_mode == initial_tool

        win.close()
