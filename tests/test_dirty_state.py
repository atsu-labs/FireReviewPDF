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
    def test_save_project_default_path_from_pdf(self, window, monkeypatch, tmp_path):
        captured_dir = None

        from PySide6.QtWidgets import QFileDialog
        monkeypatch.setattr(
            QFileDialog,
            "getSaveFileName",
            lambda parent, caption, dir, filter: (str(tmp_path / "out.json"), "")
        )

        def fake_get_save_file_name(parent, caption, dir, filter):
            nonlocal captured_dir
            captured_dir = dir
            return (str(tmp_path / "out.json"), "")

        monkeypatch.setattr(QFileDialog, "getSaveFileName", fake_get_save_file_name)

        window.model.pdf_path = os.path.join("some", "path", "drawing.pdf")
        assert window.save_project() is True
        assert captured_dir == os.path.join("some", "path", "drawing.json")

    def test_save_project_default_path_from_current_project(self, window, monkeypatch, tmp_path):
        captured_dir = None

        from PySide6.QtWidgets import QFileDialog

        def fake_get_save_file_name(parent, caption, dir, filter):
            nonlocal captured_dir
            captured_dir = dir
            return (str(tmp_path / "out.json"), "")

        monkeypatch.setattr(QFileDialog, "getSaveFileName", fake_get_save_file_name)

        window.model.pdf_path = os.path.join("some", "path", "drawing.pdf")
        window.current_project_path = os.path.join("projects", "my_project.json")
        assert window.save_project() is True
        assert captured_dir == os.path.join("projects", "my_project.json")

