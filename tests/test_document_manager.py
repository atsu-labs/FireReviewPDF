import os
import pytest
from PySide6.QtCore import QPointF
from firereview.models import DrawingModel, Annotation
from firereview.services.document_manager import DocumentManager
from firereview.services.pdf_handler import PDFHandler


class TestDocumentManager:
    def test_initial_state(self):
        dm = DocumentManager()
        assert dm.is_dirty is False
        assert dm.current_project_path == ""
        assert isinstance(dm.model, DrawingModel)
        assert dm.get_suggested_save_path() == ""
        assert dm.get_active_document_name() == ""

    def test_dirty_changed_signal(self, qtbot):
        dm = DocumentManager()
        with qtbot.waitSignal(dm.dirty_changed, timeout=1000) as blocker:
            dm.set_dirty(True)
        assert blocker.args == [True]
        assert dm.is_dirty is True

        # 再度同じ値を設定した場合はシグナルを発行しない
        with qtbot.assertNotEmitted(dm.dirty_changed):
            dm.set_dirty(True)

        with qtbot.waitSignal(dm.dirty_changed, timeout=1000) as blocker:
            dm.set_dirty(False)
        assert blocker.args == [False]
        assert dm.is_dirty is False

    def test_get_suggested_save_path(self):
        dm = DocumentManager()
        # プロジェクトパス優先
        dm.current_project_path = os.path.join("path", "to", "project.json")
        dm.model.pdf_path = os.path.join("path", "to", "drawing.pdf")
        assert dm.get_suggested_save_path() == os.path.join("path", "to", "project.json")

        # プロジェクトパス未指定時はPDFパスの拡張子を.jsonにしたもの
        dm.current_project_path = ""
        assert dm.get_suggested_save_path() == os.path.join("path", "to", "drawing.json")

    def test_get_active_document_name(self):
        dm = DocumentManager()
        dm.model.pdf_path = "/path/to/floorplan.pdf"
        assert dm.get_active_document_name() == "floorplan.pdf"

        dm.current_project_path = "/path/to/review.json"
        assert dm.get_active_document_name() == "review.json"

    def test_save_and_load_project(self, tmp_path):
        dm = DocumentManager()
        dm.model.pdf_path = str(tmp_path / "plan.pdf")
        dm.model.scale_factor = 2.5
        line = Annotation("line")
        line.points = [QPointF(0, 0), QPointF(100, 100)]
        dm.model.annotations.append(line)
        dm.set_dirty(True)

        save_path = str(tmp_path / "test_project.json")
        dm.save_project(save_path)

        assert os.path.exists(save_path)
        assert dm.is_dirty is False
        assert dm.current_project_path == save_path

        # 読み込み
        dm2 = DocumentManager()
        loaded = dm2.load_project(save_path)
        assert loaded.scale_factor == 2.5
        assert len(loaded.annotations) == 1

        dm2.apply_loaded_project(loaded, save_path)
        assert dm2.current_project_path == save_path
        assert dm2.is_dirty is False
        assert dm2.model.scale_factor == 2.5
