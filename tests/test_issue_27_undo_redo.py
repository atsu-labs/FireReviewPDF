import pytest
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QKeyEvent, QKeySequence, QPixmap
from PySide6.QtWidgets import QLineEdit, QMessageBox

from firereview.main_window import MainWindow
from firereview.models import DrawingModel
from firereview.controllers import (
    AddCommand,
    RemoveCommand,
    MoveCommand,
    PropertyChangeCommand,
)
from firereview.ui.components.main_menubar import MainMenuBar


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
    pix = QPixmap(400, 400)
    pix.fill(Qt.white)
    win.canvas.set_page_image(pix)
    yield win
    win.set_dirty(False)


def send_key(widget, key, modifiers=Qt.NoModifier):
    ev = QKeyEvent(QKeyEvent.Type.KeyPress, key, modifiers)
    widget.keyPressEvent(ev)


class TestEditMenuAndShortcuts:
    def test_edit_menu_actions_and_shortcuts(self, window):
        menubar: MainMenuBar = window.menubar
        edit_menu = None
        for act in menubar.actions():
            if act.text() == "編集":
                edit_menu = act.menu()
                break
        assert edit_menu is not None

        actions = {act.text(): act for act in edit_menu.actions() if act.text()}
        assert "元に戻す" in actions
        assert actions["元に戻す"].shortcut() == QKeySequence("Ctrl+Z")
        assert actions["元に戻す"].isEnabled() is False

        assert "やり直す" in actions
        assert actions["やり直す"].shortcut() == QKeySequence("Ctrl+Y")
        assert actions["やり直す"].isEnabled() is False

    def test_menu_enabled_state_tracks_undo_stack(self, window):
        assert window.menubar.undo_action.isEnabled() is False
        assert window.menubar.redo_action.isEnabled() is False

        window.on_marker_complete(QPointF(50, 50))
        assert window.menubar.undo_action.isEnabled() is True
        assert window.menubar.redo_action.isEnabled() is False

        window.undo()
        assert window.menubar.undo_action.isEnabled() is False
        assert window.menubar.redo_action.isEnabled() is True

        window.redo()
        assert window.menubar.undo_action.isEnabled() is True
        assert window.menubar.redo_action.isEnabled() is False

    def test_ctrl_z_and_ctrl_y_and_ctrl_shift_z_shortcuts(self, window):
        window.on_polyline_complete([QPointF(10, 10), QPointF(100, 100)])
        assert len(window.model.annotations) == 1

        send_key(window, Qt.Key_Z, Qt.ControlModifier)
        assert len(window.model.annotations) == 0

        send_key(window, Qt.Key_Y, Qt.ControlModifier)
        assert len(window.model.annotations) == 1

        send_key(window, Qt.Key_Z, Qt.ControlModifier)
        assert len(window.model.annotations) == 0

        send_key(window, Qt.Key_Z, Qt.ControlModifier | Qt.ShiftModifier)
        assert len(window.model.annotations) == 1

    def test_qlineedit_focus_uses_local_undo_instead_of_global_stack(self, window):
        window.on_marker_complete(QPointF(20, 20))
        assert len(window.model.annotations) == 1

        line_edit = QLineEdit(window)
        line_edit.show()
        line_edit.setFocus()
        line_edit.setText("初期")
        line_edit.insert("追加")
        assert line_edit.isUndoAvailable() is True

        # QLineEditにフォーカスがある場合はQLineEditのUndoが優先され、注釈は消えない
        window.undo()
        assert len(window.model.annotations) == 1


class TestAddAndRemoveCommands:
    def test_add_and_undo_redo_all_annotation_types(self, window):
        # 1. Polyline
        window.on_polyline_complete([QPointF(0, 0), QPointF(50, 50)])
        # 2. Polygon
        window.on_polygon_complete([QPointF(0, 0), QPointF(50, 0), QPointF(50, 50)])
        # 3. Cloud
        window.on_cloud_complete([QPointF(10, 10), QPointF(60, 10), QPointF(60, 60), QPointF(10, 60)])
        # 4. Circle
        window.on_circle_drag_complete(QPointF(100, 100), 30.0)
        # 5. Arc
        window.on_arc_drag_complete(QPointF(120, 120), 40.0, 45.0)
        # 6. Marker
        window.on_marker_complete(QPointF(150, 150))
        # 7. Legend
        window.on_legend_complete(QPointF(200, 200))
        # 8. Text
        window.on_text_editing_finished(QPointF(250, 250), "テスト注釈", "", "BIZ UDゴシック", 14, "#ff0000")

        assert len(window.model.annotations) == 8
        assert len(window.canvas.annotation_items) == 8

        # 8回すべてUndo
        for expected_count in range(7, -1, -1):
            window.undo()
            assert len(window.model.annotations) == expected_count
            assert len(window.canvas.annotation_items) == expected_count

        # 8回すべてRedo
        for expected_count in range(1, 9):
            window.redo()
            assert len(window.model.annotations) == expected_count
            assert len(window.canvas.annotation_items) == expected_count

    def test_remove_command_preserves_index_and_canvas_item(self, window):
        window.on_marker_complete(QPointF(10, 10))
        window.on_polyline_complete([QPointF(20, 20), QPointF(80, 80)])
        window.on_marker_complete(QPointF(30, 30))

        ids_before = [a.id for a in window.model.annotations]
        middle_id = ids_before[1]

        window.on_delete_item(middle_id)
        assert [a.id for a in window.model.annotations] == [ids_before[0], ids_before[2]]
        assert middle_id not in window.canvas.annotation_items

        # Undoで元のインデックス位置およびキャンバス上に復元されること
        window.undo()
        assert [a.id for a in window.model.annotations] == ids_before
        assert middle_id in window.canvas.annotation_items

        # Redoで再度削除されること
        window.redo()
        assert [a.id for a in window.model.annotations] == [ids_before[0], ids_before[2]]
        assert middle_id not in window.canvas.annotation_items


class TestMoveCommands:
    def test_item_move_undo_redo(self, window):
        window.on_polygon_complete([QPointF(10, 10), QPointF(30, 10), QPointF(30, 30)])
        ann = window.model.annotations[0]

        window.on_item_moved(ann.id, QPointF(15, 25))
        assert ann.points == [QPointF(25, 35), QPointF(45, 35), QPointF(45, 55)]

        window.undo()
        assert ann.points == [QPointF(10, 10), QPointF(30, 10), QPointF(30, 30)]
        poly_item = window.canvas.annotation_items[ann.id]
        assert list(poly_item.polygon()) == [QPointF(10, 10), QPointF(30, 10), QPointF(30, 30)]

        window.redo()
        assert ann.points == [QPointF(25, 35), QPointF(45, 35), QPointF(45, 55)]
        assert list(poly_item.polygon()) == [QPointF(25, 35), QPointF(45, 35), QPointF(45, 55)]

    def test_circle_and_text_move_undo_redo(self, window):
        window.on_circle_drag_complete(QPointF(100, 100), 20.0)
        circle_ann = window.model.annotations[0]
        window.on_item_moved(circle_ann.id, QPointF(20, -10))
        assert circle_ann.points[0] == QPointF(120, 90)

        window.undo()
        assert circle_ann.points[0] == QPointF(100, 100)
        circle_item = window.canvas.annotation_items[circle_ann.id]
        assert circle_item.pos() == QPointF(0, 0)

        window.redo()
        assert circle_ann.points[0] == QPointF(120, 90)
        assert circle_item.pos() == QPointF(20, -10)

    def test_vertex_edit_and_recalculation_undo_redo(self, window):
        window.model.set_calibration(QPointF(0, 0), QPointF(100, 0), 1000.0, page_num=0)
        window.on_polyline_complete([QPointF(0, 0), QPointF(100, 0)])
        ann = window.model.annotations[0]

        # 計測を実行 (1.00 m)
        window.on_calculate_requested(ann.id)
        initial_text = ann.text
        initial_val = ann.real_value
        assert ann.is_calculated is True
        assert initial_val == pytest.approx(1000.0)

        # 頂点編集で長さを2倍 (200px = 2000mm) に変更
        window.on_canvas_item_points_updated(ann.id, [QPointF(0, 0), QPointF(200, 0)])
        assert ann.points == [QPointF(0, 0), QPointF(200, 0)]
        assert ann.real_value == pytest.approx(2000.0)
        assert ann.text != initial_text

        # Undoで頂点座標と計算値・ラベル文字列が元に戻る
        window.undo()
        assert ann.points == [QPointF(0, 0), QPointF(100, 0)]
        assert ann.real_value == pytest.approx(initial_val)
        assert ann.text == initial_text

        # Redoで編集後の頂点座標と計算値に戻る
        window.redo()
        assert ann.points == [QPointF(0, 0), QPointF(200, 0)]
        assert ann.real_value == pytest.approx(2000.0)

    def test_label_move_undo_redo(self, window):
        window.model.set_calibration(QPointF(0, 0), QPointF(100, 0), 1000.0, page_num=0)
        window.on_polyline_complete([QPointF(0, 0), QPointF(100, 0)])
        ann = window.model.annotations[0]
        window.on_calculate_requested(ann.id)

        window.on_label_moved(ann.id, QPointF(12.0, -8.0))
        assert ann.label_offset == [12.0, -8.0]

        window.undo()
        assert ann.label_offset == [0.0, 0.0]

        window.redo()
        assert ann.label_offset == [12.0, -8.0]


class TestPropertyChangeAndMerging:
    def test_property_change_undo_redo(self, window):
        window.on_polygon_complete([QPointF(0, 0), QPointF(50, 0), QPointF(50, 50)])
        ann = window.model.annotations[0]
        orig_color = ann.color

        window.on_property_changed(ann.id, {"color": "#00ff00"})
        assert ann.color == "#00ff00"

        window.undo()
        assert ann.color == orig_color

        window.redo()
        assert ann.color == "#00ff00"

    def test_consecutive_same_attribute_changes_are_merged(self, window):
        window.on_polygon_complete([QPointF(0, 0), QPointF(50, 0), QPointF(50, 50)])
        ann = window.model.annotations[0]
        orig_opacity = ann.stroke_opacity  # 100

        # スライダーを連続ドラッグしたケースをシミュレート
        window.on_property_changed(ann.id, {"stroke_opacity": 80})
        window.on_property_changed(ann.id, {"stroke_opacity": 55})
        window.on_property_changed(ann.id, {"stroke_opacity": 25})
        assert ann.stroke_opacity == 25

        # 1回のUndoで操作前の100%に戻ること
        window.undo()
        assert ann.stroke_opacity == orig_opacity

        # 1回のRedoで最終値の25%に戻ること
        window.redo()
        assert ann.stroke_opacity == 25

    def test_different_attributes_are_not_merged(self, window):
        window.on_polygon_complete([QPointF(0, 0), QPointF(50, 0), QPointF(50, 50)])
        ann = window.model.annotations[0]
        orig_width = ann.line_width
        orig_opacity = ann.stroke_opacity

        window.on_property_changed(ann.id, {"line_width": 6})
        window.on_property_changed(ann.id, {"stroke_opacity": 40})

        # 1回目のUndoではstroke_opacityのみ戻る
        window.undo()
        assert ann.stroke_opacity == orig_opacity
        assert ann.line_width == 6

        # 2回目のUndoでline_widthも戻る
        window.undo()
        assert ann.line_width == orig_width

    def test_inline_text_edit_and_calculate_undo_redo(self, window):
        window.on_text_editing_finished(QPointF(30, 40), "変更前", "", "BIZ UDゴシック", 12, "#ff0000")
        ann = window.model.annotations[0]

        window.on_existing_text_edited(ann.id, "変更後")
        assert ann.text == "変更後"

        window.undo()
        assert ann.text == "変更前"

        window.redo()
        assert ann.text == "変更後"

    def test_calculate_button_undo_redo(self, window):
        window.model.set_calibration(QPointF(0, 0), QPointF(100, 0), 1000.0, page_num=0)
        window.on_polyline_complete([QPointF(0, 0), QPointF(100, 0)])
        ann = window.model.annotations[0]
        assert ann.is_calculated is False
        assert ann.text == ""

        window.on_calculate_requested(ann.id)
        assert ann.is_calculated is True
        assert ann.text != ""

        window.undo()
        assert ann.is_calculated is False
        assert ann.text == ""
        assert ann.real_value == 0.0

        window.redo()
        assert ann.is_calculated is True
        assert ann.text != ""


class TestCrossPageAndLifecycle:
    def test_cross_page_undo_redo_switches_to_target_page(self, window):
        # ページ0で注釈を作成
        window.current_page = 0
        window.on_marker_complete(QPointF(40, 40))
        ann_p0 = window.model.annotations[0]
        assert ann_p0.page_num == 0

        # ページ1へ移動
        window.go_to_page(1)
        assert window.current_page == 1

        # Undoを実行するとページ0の操作を取り消すため自動的にページ0へ遷移する
        window.undo()
        assert window.current_page == 0
        assert len(window.model.annotations) == 0

        # 再びページ1へ移動してからRedoを実行すると自動的にページ0へ遷移して復元される
        window.go_to_page(1)
        assert window.current_page == 1
        window.redo()
        assert window.current_page == 0
        assert len(window.model.annotations) == 1

    def test_undo_stack_cleared_on_project_load_and_kept_on_swap(self, window, monkeypatch):
        window.on_marker_complete(QPointF(50, 50))
        assert window.undo_stack.canUndo() is True

        # swap_pdf ではモデルインスタンスが維持されるためUndo履歴も残る
        monkeypatch.setattr(window.pdf_handler, "open_file", lambda p: True)
        window.document_manager.swap_pdf("swapped.pdf")
        assert window.undo_stack.canUndo() is True

        # apply_loaded_project では新しいモデルに置き換わるためUndo履歴がクリアされる
        new_model = DrawingModel()
        window.document_manager.apply_loaded_project(new_model, "project.json")
        assert window.undo_stack.canUndo() is False
        assert window.undo_stack.canRedo() is False
