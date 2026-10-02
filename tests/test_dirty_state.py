import os
import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMessageBox
from firereview.main_window import MainWindow


@pytest.fixture(autouse=True)
def prevent_modal_dialogs(monkeypatch):
    """テスト終了時や処理中のモーダルダイアログ表示によるハングを防止する"""
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Discard)
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: QMessageBox.Ok)


@pytest.fixture
def window(qtbot):
    win = MainWindow()
    qtbot.addWidget(win)
    yield win
    win.set_dirty(False)


class TestDirtyState:
    def test_initial_dirty_state(self, window):
        assert window.is_dirty is False
        assert window.windowTitle() == "FireReviewPDF"
        assert window.current_project_path == ""

    def test_set_dirty_updates_title(self, window):
        window.set_dirty(True)
        assert window.is_dirty is True
        assert window.windowTitle().endswith(" *")

        window.set_dirty(False)
        assert window.is_dirty is False
        assert not window.windowTitle().endswith(" *")

    def test_window_title_with_pdf_and_project_path(self, window):
        window.model.pdf_path = os.path.join("some", "dir", "floor_plan.pdf")
        window._update_window_title()
        assert window.windowTitle() == "FireReviewPDF - floor_plan.pdf"

        window.set_dirty(True)
        assert window.windowTitle() == "FireReviewPDF - floor_plan.pdf *"

        # プロジェクトパスが設定されたらプロジェクト名が優先される
        window.current_project_path = os.path.join("some", "dir", "review.json")
        window._update_window_title()
        assert window.windowTitle() == "FireReviewPDF - review.json *"

        window.set_dirty(False)
        assert window.windowTitle() == "FireReviewPDF - review.json"

    def test_add_to_model_marks_dirty(self, window):
        assert window.is_dirty is False
        window._add_to_model("line", [QPointF(0, 0), QPointF(10, 10)])
        assert window.is_dirty is True

    def test_delete_item_marks_dirty(self, window):
        ann = window._add_to_model("line", [QPointF(0, 0), QPointF(10, 10)])
        window.set_dirty(False)
        assert window.is_dirty is False

        window.on_delete_item(ann.id)
        assert window.is_dirty is True

    def test_item_moved_marks_dirty(self, window):
        ann = window._add_to_model("line", [QPointF(0, 0), QPointF(10, 10)])
        window.set_dirty(False)
        assert window.is_dirty is False

        window.on_item_moved(ann.id, QPointF(5, 5))
        assert window.is_dirty is True

    def test_label_moved_marks_dirty(self, window):
        ann = window._add_to_model("line", [QPointF(0, 0), QPointF(10, 10)])
        window.set_dirty(False)
        assert window.is_dirty is False

        window.on_label_moved(ann.id, QPointF(2, 3))
        assert window.is_dirty is True

    def test_apply_unit_change_marks_dirty(self, window):
        window.set_dirty(False)
        assert window.is_dirty is False
        window.apply_unit_change("mm")
        assert window.is_dirty is True

    def test_existing_text_edited_marks_dirty(self, window):
        ann = window._add_to_model("text", [QPointF(0, 0)], text="Hello")
        window.set_dirty(False)
        assert window.is_dirty is False

        window.on_existing_text_edited(ann.id, "World")
        assert window.is_dirty is True

    def test_color_name_changed_marks_dirty(self, window):
        window.set_dirty(False)
        assert window.is_dirty is False

        window.on_color_name_changed(0, "#ff0000", "消火栓")
        assert window.is_dirty is True


class TestMaybeSaveChanges:
    def test_clean_state_proceeds_without_prompt(self, window, monkeypatch):
        prompt_shown = False

        def fake_question(*args, **kwargs):
            nonlocal prompt_shown
            prompt_shown = True
            return QMessageBox.Cancel

        monkeypatch.setattr(QMessageBox, "question", fake_question)

        window.set_dirty(False)
        assert window.maybe_save_changes() is True
        assert prompt_shown is False

    def test_dirty_state_discard_proceeds(self, window, monkeypatch):
        monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Discard)

        window.set_dirty(True)
        assert window.maybe_save_changes() is True

    def test_dirty_state_cancel_stops(self, window, monkeypatch):
        monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Cancel)

        window.set_dirty(True)
        assert window.maybe_save_changes() is False

    def test_dirty_state_save_success_proceeds(self, window, monkeypatch):
        monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Save)
        monkeypatch.setattr(window, "save_project", lambda: True)

        window.set_dirty(True)
        assert window.maybe_save_changes() is True

    def test_dirty_state_save_cancelled_stops(self, window, monkeypatch):
        monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Save)
        monkeypatch.setattr(window, "save_project", lambda: False)

        window.set_dirty(True)
        assert window.maybe_save_changes() is False


class TestCloseEvent:
    def test_close_when_clean_accepted(self, window):
        window.set_dirty(False)
        event = QCloseEvent()
        window.closeEvent(event)
        assert event.isAccepted() is True

    def test_close_when_dirty_and_cancelled_ignored(self, window, monkeypatch):
        monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Cancel)
        window.set_dirty(True)

        event = QCloseEvent()
        window.closeEvent(event)
        assert event.isAccepted() is False

    def test_close_when_dirty_and_discarded_accepted(self, window, monkeypatch):
        monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Discard)
        window.set_dirty(True)

        event = QCloseEvent()
        window.closeEvent(event)
        assert event.isAccepted() is True


class TestSaveProject:
    def test_save_project_when_no_path_prompts_save_as(self, window, monkeypatch, tmp_path):
        """プロジェクトパス未設定の場合、save_projectはsave_project_asへフォールバックしてダイアログを表示する"""
        captured_dir = None
        target_file = str(tmp_path / "out.json")

        from PySide6.QtWidgets import QFileDialog

        def fake_get_save_file_name(parent, caption, dir, filter):
            nonlocal captured_dir
            captured_dir = dir
            return (target_file, "")

        monkeypatch.setattr(QFileDialog, "getSaveFileName", fake_get_save_file_name)

        window.model.pdf_path = os.path.join("some", "path", "drawing.pdf")
        window.current_project_path = ""
        window.set_dirty(True)

        assert window.save_project() is True
        assert captured_dir == os.path.join("some", "path", "drawing.json")
        assert window.current_project_path == target_file
        assert window.is_dirty is False
        assert os.path.exists(target_file)

    def test_save_project_overwrites_existing_path_without_dialog(self, window, monkeypatch, tmp_path):
        """プロジェクトパスが設定済みの場合は、ダイアログを開かずに既存パスへ上書き保存する"""
        from PySide6.QtWidgets import QFileDialog

        def unexpected_dialog(*args, **kwargs):
            raise AssertionError("QFileDialog.getSaveFileName should not be called on overwrite save")

        monkeypatch.setattr(QFileDialog, "getSaveFileName", unexpected_dialog)

        existing_file = str(tmp_path / "existing_project.json")
        window.current_project_path = existing_file
        window.set_dirty(True)

        assert window.save_project() is True
        assert window.is_dirty is False
        assert os.path.exists(existing_file)

    def test_save_project_as_always_prompts_file_dialog(self, window, monkeypatch, tmp_path):
        """save_project_asは常にダイアログを表示し、既存パスがあっても新しいパスへ保存・更新する"""
        captured_dir = None
        captured_caption = None
        new_file = str(tmp_path / "new_project.json")

        from PySide6.QtWidgets import QFileDialog

        def fake_get_save_file_name(parent, caption, dir, filter):
            nonlocal captured_dir, captured_caption
            captured_dir = dir
            captured_caption = caption
            return (new_file, "")

        monkeypatch.setattr(QFileDialog, "getSaveFileName", fake_get_save_file_name)

        initial_file = str(tmp_path / "initial.json")
        window.current_project_path = initial_file
        window.set_dirty(True)

        assert window.save_project_as() is True
        assert captured_caption == "名前を付けて保存"
        assert captured_dir == initial_file
        assert window.current_project_path == new_file
        assert window.is_dirty is False
        assert os.path.exists(new_file)

    def test_save_project_as_cancelled_keeps_dirty(self, window, monkeypatch, tmp_path):
        """ダイアログでキャンセルされた場合は保存せず、ダーティ状態とパスを維持する"""
        from PySide6.QtWidgets import QFileDialog

        monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: ("", ""))

        initial_file = str(tmp_path / "initial.json")
        window.current_project_path = initial_file
        window.set_dirty(True)

        assert window.save_project_as() is False
        assert window.current_project_path == initial_file
        assert window.is_dirty is True

    def test_save_project_error_handling(self, window, monkeypatch):
        """保存処理で例外が発生した場合はエラーダイアログを表示しFalseを返す"""
        window.current_project_path = "/invalid_dir/forbidden/project.json"
        window.set_dirty(True)

        assert window.save_project() is False
        assert window.is_dirty is True

    def test_menubar_save_actions_and_shortcuts(self, window):
        """メニューバーに上書き保存(Ctrl+S)と名前を付けて保存(Ctrl+Shift+S)が存在することを確認"""
        actions = window.menubar.actions()
        file_menu = None
        for action in actions:
            if action.menu() and action.text() == "ファイル":
                file_menu = action.menu()
                break

        assert file_menu is not None
        menu_actions = file_menu.actions()
        action_map = {a.text(): a for a in menu_actions}

        assert "プロジェクトを保存" in action_map
        assert action_map["プロジェクトを保存"].shortcut().toString() == "Ctrl+S"

        assert "名前を付けて保存..." in action_map
        assert action_map["名前を付けて保存..."].shortcut().toString() == "Ctrl+Shift+S"


