import pytest
from PySide6.QtCore import Qt, QPointF, QEvent
from PySide6.QtGui import QMouseEvent, QKeyEvent, QPixmap
from PySide6.QtWidgets import QMessageBox

from firereview.main_window import MainWindow
from firereview.ui.canvas.enums import ToolMode
from firereview.controllers import BatchMoveCommand, BatchRemoveCommand


@pytest.fixture(autouse=True)
def prevent_modal_dialogs(monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Discard)
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: QMessageBox.Ok)


@pytest.fixture
def window(qtbot):
    win = MainWindow()
    qtbot.addWidget(win)
    win.resize(800, 600)
    pix = QPixmap(600, 600)
    pix.fill(Qt.white)
    win.canvas.set_page_image(pix)
    win.set_tool(ToolMode.SELECT)
    yield win
    win.set_dirty(False)


def mouse_event(canvas, event_type, scene_pt: QPointF, button=Qt.LeftButton, buttons=Qt.LeftButton, modifiers=Qt.NoModifier):
    vp_pt = canvas.mapFromScene(scene_pt)
    ev = QMouseEvent(
        event_type,
        QPointF(vp_pt),
        QPointF(canvas.viewport().mapToGlobal(vp_pt)),
        button,
        buttons,
        modifiers,
    )
    if event_type == QEvent.Type.MouseButtonPress:
        canvas.mousePressEvent(ev)
    elif event_type == QEvent.Type.MouseMove:
        canvas.mouseMoveEvent(ev)
    elif event_type == QEvent.Type.MouseButtonRelease:
        canvas.mouseReleaseEvent(ev)


def click_scene(canvas, scene_pt: QPointF, button=Qt.LeftButton, modifiers=Qt.NoModifier):
    mouse_event(canvas, QEvent.Type.MouseButtonPress, scene_pt, button=button, buttons=button, modifiers=modifiers)
    mouse_event(canvas, QEvent.Type.MouseButtonRelease, scene_pt, button=button, buttons=Qt.NoButton, modifiers=modifiers)


def drag_scene(canvas, start_pt: QPointF, end_pt: QPointF, modifiers=Qt.NoModifier):
    mouse_event(canvas, QEvent.Type.MouseButtonPress, start_pt, button=Qt.LeftButton, buttons=Qt.LeftButton, modifiers=modifiers)
    mid_pt = QPointF((start_pt.x() + end_pt.x()) / 2.0, (start_pt.y() + end_pt.y()) / 2.0)
    mouse_event(canvas, QEvent.Type.MouseMove, mid_pt, button=Qt.NoButton, buttons=Qt.LeftButton, modifiers=modifiers)
    mouse_event(canvas, QEvent.Type.MouseMove, end_pt, button=Qt.NoButton, buttons=Qt.LeftButton, modifiers=modifiers)
    mouse_event(canvas, QEvent.Type.MouseButtonRelease, end_pt, button=Qt.LeftButton, buttons=Qt.NoButton, modifiers=modifiers)


def send_key(widget, key, modifiers=Qt.NoModifier):
    ev = QKeyEvent(QKeyEvent.Type.KeyPress, key, modifiers)
    widget.keyPressEvent(ev)


class TestMultiSelectionOperations:
    def test_shift_and_ctrl_click_toggle_selection(self, window):
        """Shift / Ctrl + クリックによる追加選択・選択解除（トグル）とパネル表示同期"""
        window.on_marker_complete(QPointF(100, 100))
        window.on_marker_complete(QPointF(200, 100))
        window.on_marker_complete(QPointF(300, 100))
        window.set_tool(ToolMode.SELECT)

        m1, m2, m3 = window.model.annotations
        canvas = window.canvas

        # 1. m1 を通常クリック -> 単一選択
        click_scene(canvas, QPointF(100, 100))
        assert canvas.get_selected_annotation_ids() == [m1.id]
        assert window.prop_panel.current_item_id == m1.id
        assert window.navigator.selected_ids == {m1.id}

        # 2. m2 を Shift + クリック -> 追加選択 (2件)
        click_scene(canvas, QPointF(200, 100), modifiers=Qt.ShiftModifier)
        assert canvas.get_selected_annotation_ids() == [m1.id, m2.id]
        assert window.prop_panel.current_item_id is None
        assert window.prop_panel.type_title.text() == "複数選択中 (2件)"
        assert window.prop_panel.delete_btn.isHidden() is False
        assert window.prop_panel.appearance_container.isHidden() is True
        assert window.navigator.selected_ids == {m1.id, m2.id}

        # 3. m3 を Ctrl + クリック -> 追加選択 (3件)
        click_scene(canvas, QPointF(300, 100), modifiers=Qt.ControlModifier)
        assert canvas.get_selected_annotation_ids() == [m1.id, m2.id, m3.id]
        assert window.prop_panel.type_title.text() == "複数選択中 (3件)"
        assert window.navigator.selected_ids == {m1.id, m2.id, m3.id}

        # 4. 選択中の m2 を Shift + クリック -> 除外 (2件)
        click_scene(canvas, QPointF(200, 100), modifiers=Qt.ShiftModifier)
        assert canvas.get_selected_annotation_ids() == [m1.id, m3.id]
        assert window.prop_panel.type_title.text() == "複数選択中 (2件)"
        assert window.navigator.selected_ids == {m1.id, m3.id}

        # 5. 選択中の m3 を Ctrl + クリック -> 残り1件になり単一選択表示へ戻る
        click_scene(canvas, QPointF(300, 100), modifiers=Qt.ControlModifier)
        assert canvas.get_selected_annotation_ids() == [m1.id]
        assert window.prop_panel.current_item_id == m1.id
        assert window.navigator.selected_ids == {m1.id}

    def test_rubberband_replace_add_and_exclude(self, window):
        """背景ドラッグによる矩形範囲選択（通常・Shift追加・Alt除外）と背景解除"""
        window.on_marker_complete(QPointF(100, 100))
        window.on_marker_complete(QPointF(200, 100))
        window.on_marker_complete(QPointF(350, 100))
        window.set_tool(ToolMode.SELECT)

        m1, m2, m3 = window.model.annotations
        canvas = window.canvas

        # 1. 背景通常ドラッグで m1, m2 を囲む -> [m1, m2] が選択される（背景PDFは含まれない）
        drag_scene(canvas, QPointF(50, 50), QPointF(250, 150), modifiers=Qt.NoModifier)
        assert canvas.get_selected_annotation_ids() == [m1.id, m2.id]
        assert canvas.background_item.isSelected() is False

        # 2. Shift + ドラッグで m3 を囲む -> [m1, m2, m3] に追加選択
        drag_scene(canvas, QPointF(300, 50), QPointF(400, 150), modifiers=Qt.ShiftModifier)
        assert canvas.get_selected_annotation_ids() == [m1.id, m2.id, m3.id]

        # 3. Alt + ドラッグで m1, m2 を囲む -> [m1, m2] が除外され [m3] のみ残る
        drag_scene(canvas, QPointF(50, 50), QPointF(250, 150), modifiers=Qt.AltModifier)
        assert canvas.get_selected_annotation_ids() == [m3.id]
        assert window.prop_panel.current_item_id == m3.id

        # 4. 何もない背景をクリック -> 全選択解除
        click_scene(canvas, QPointF(500, 500))
        assert canvas.get_selected_annotation_ids() == []
        assert window.prop_panel.current_item_id is None
        assert window.navigator.selected_ids == set()

    def test_esc_key_clears_multi_selection(self, window):
        """複数選択中に Esc キーで全選択が解除されること"""
        window.on_marker_complete(QPointF(100, 100))
        window.on_marker_complete(QPointF(200, 100))
        window.set_tool(ToolMode.SELECT)

        canvas = window.canvas
        drag_scene(canvas, QPointF(50, 50), QPointF(250, 150))
        assert len(canvas.get_selected_annotation_ids()) == 2

        send_key(canvas, Qt.Key_Escape)
        assert canvas.get_selected_annotation_ids() == []
        assert window.navigator.selected_ids == set()

    def test_click_without_drag_on_multi_selected_item_collapses_to_single(self, window):
        """複数選択中に選択済みアイテムをドラッグせずクリックした場合はその1件の単一選択に切り替わること"""
        window.on_marker_complete(QPointF(100, 100))
        window.on_marker_complete(QPointF(200, 100))
        window.set_tool(ToolMode.SELECT)

        m1, m2 = window.model.annotations
        canvas = window.canvas
        drag_scene(canvas, QPointF(50, 50), QPointF(250, 150))
        assert canvas.get_selected_annotation_ids() == [m1.id, m2.id]

        # m1 上でドラッグせずクリック
        click_scene(canvas, QPointF(100, 100))
        assert canvas.get_selected_annotation_ids() == [m1.id]
        assert window.prop_panel.current_item_id == m1.id


class TestMultiMoveAndDeleteWithUndoRedo:
    def test_multi_drag_move_and_single_transaction_undo_redo(self, window):
        """複数オブジェクトの一括ドラッグ移動と 1回のUndo/Redoによる一括復元"""
        window.on_polyline_complete([QPointF(100, 100), QPointF(150, 100)])
        window.on_polygon_complete([QPointF(100, 200), QPointF(160, 200), QPointF(130, 250)])
        window.on_marker_complete(QPointF(200, 150))
        window.set_tool(ToolMode.SELECT)

        poly_line, polygon, marker = window.model.annotations
        canvas = window.canvas

        # 全オブジェクトを範囲選択
        drag_scene(canvas, QPointF(50, 50), QPointF(300, 300))
        assert canvas.get_selected_annotation_ids() == [poly_line.id, polygon.id, marker.id]

        initial_stack_count = window.undo_stack.count()

        # marker (200, 150) を掴んで (+30, +40) へドラッグ移動
        drag_scene(canvas, QPointF(200, 150), QPointF(230, 190))

        # 1つの BatchMoveCommand として記録されていること
        assert window.undo_stack.count() == initial_stack_count + 1
        cmd = window.undo_stack.command(window.undo_stack.count() - 1)
        assert isinstance(cmd, BatchMoveCommand)

        # 全オブジェクトのモデル座標が (+30, +40) 平行移動していること
        assert poly_line.points[0] == QPointF(130, 140)
        assert poly_line.points[1] == QPointF(180, 140)
        assert polygon.points[0] == QPointF(130, 240)
        assert marker.points[0] == QPointF(230, 190)

        # Undo 1回で全オブジェクトが元の位置に戻ること
        window.undo()
        assert poly_line.points[0] == QPointF(100, 100)
        assert poly_line.points[1] == QPointF(150, 100)
        assert polygon.points[0] == QPointF(100, 200)
        assert marker.points[0] == QPointF(200, 150)
        assert canvas.annotation_items[marker.id].pos() == QPointF(200, 150)

        # Redo 1回で再び移動後の位置になること
        window.redo()
        assert poly_line.points[0] == QPointF(130, 140)
        assert polygon.points[0] == QPointF(130, 240)
        assert marker.points[0] == QPointF(230, 190)
        assert canvas.annotation_items[marker.id].pos() == QPointF(230, 190)

    def test_multi_delete_via_key_and_undo_redo(self, window):
        """複数選択時の Delete キーによる一括削除と 1回のUndo/Redoによる一括復元"""
        window.on_marker_complete(QPointF(100, 100))
        window.on_marker_complete(QPointF(200, 100))
        window.on_marker_complete(QPointF(300, 100))
        window.set_tool(ToolMode.SELECT)

        m1, m2, m3 = window.model.annotations
        canvas = window.canvas

        # m1 と m3 を Shift 選択
        click_scene(canvas, QPointF(100, 100))
        click_scene(canvas, QPointF(300, 100), modifiers=Qt.ShiftModifier)
        assert canvas.get_selected_annotation_ids() == [m1.id, m3.id]

        initial_stack_count = window.undo_stack.count()

        # Delete キーで一括削除
        send_key(canvas, Qt.Key_Delete)

        assert window.undo_stack.count() == initial_stack_count + 1
        cmd = window.undo_stack.command(window.undo_stack.count() - 1)
        assert isinstance(cmd, BatchRemoveCommand)

        assert [a.id for a in window.model.annotations] == [m2.id]
        assert m1.id not in canvas.annotation_items
        assert m3.id not in canvas.annotation_items
        assert m2.id in canvas.annotation_items

        # Undo 1回で元の順序 [m1, m2, m3] で一括復元されること
        window.undo()
        assert [a.id for a in window.model.annotations] == [m1.id, m2.id, m3.id]
        assert m1.id in canvas.annotation_items
        assert m3.id in canvas.annotation_items

        # Redo 1回で再度一括削除されること
        window.redo()
        assert [a.id for a in window.model.annotations] == [m2.id]

    def test_multi_delete_via_property_panel_button(self, window):
        """複数選択時のプロパティパネル削除ボタンによる一括削除"""
        window.on_marker_complete(QPointF(100, 100))
        window.on_marker_complete(QPointF(200, 100))
        window.set_tool(ToolMode.SELECT)

        canvas = window.canvas
        drag_scene(canvas, QPointF(50, 50), QPointF(250, 150))
        assert len(canvas.get_selected_annotation_ids()) == 2
        assert window.prop_panel.delete_btn.isHidden() is False

        window.prop_panel.delete_btn.click()
        assert len(window.model.annotations) == 0

        window.undo()
        assert len(window.model.annotations) == 2

    def test_right_click_context_menu_on_multi_selection(self, window, monkeypatch):
        """複数選択時、選択中オブジェクト上の右クリックは複数削除メニュー、未選択オブジェクト上の右クリックは単一選択メニューになること"""
        window.on_marker_complete(QPointF(100, 100))
        window.on_marker_complete(QPointF(200, 100))
        window.on_marker_complete(QPointF(350, 100))
        window.set_tool(ToolMode.SELECT)

        m1, m2, m3 = window.model.annotations
        canvas = window.canvas

        multi_menu_calls = []
        single_menu_calls = []
        monkeypatch.setattr(
            canvas,
            "_show_multi_object_context_menu",
            lambda pos, ids: multi_menu_calls.append(list(ids)),
        )
        monkeypatch.setattr(
            canvas,
            "_show_object_context_menu",
            lambda pos, iid: single_menu_calls.append(iid),
        )

        # m1, m2 を範囲選択
        drag_scene(canvas, QPointF(50, 50), QPointF(250, 150))
        assert canvas.get_selected_annotation_ids() == [m1.id, m2.id]

        # 1. 選択中の m1 上で右クリック -> 複数選択を維持したまま _show_multi_object_context_menu が呼ばれる
        mouse_event(
            canvas,
            QEvent.Type.MouseButtonPress,
            QPointF(100, 100),
            button=Qt.RightButton,
            buttons=Qt.RightButton,
        )
        assert multi_menu_calls == [[m1.id, m2.id]]
        assert single_menu_calls == []
        assert canvas.get_selected_annotation_ids() == [m1.id, m2.id]

        # 2. 未選択の m3 上で右クリック -> m3 単一選択に切り替わり _show_object_context_menu が呼ばれる
        mouse_event(
            canvas,
            QEvent.Type.MouseButtonPress,
            QPointF(350, 100),
            button=Qt.RightButton,
            buttons=Qt.RightButton,
        )
        assert single_menu_calls == [m3.id]
        assert canvas.get_selected_annotation_ids() == [m3.id]
