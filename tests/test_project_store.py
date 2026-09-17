import os
import json
import pytest
from PySide6.QtCore import QPointF
from firereview.models import DrawingModel, Annotation
from firereview.services.project_store import save_project, load_project


class TestProjectStore:
    def test_save_and_load_roundtrip(self, tmp_path):
        model = DrawingModel()
        model.scale_factor = 2.5
        model.is_calibrated = True
        model.unit = "mm"
        model.pdf_path = str(tmp_path / "sample.pdf")
        model.page_calibrations = {0: 2.5, 1: 5.0}
        model.page_color_names = {0: {"#ff0000": "消火栓", "#00ff00": "避難誘導灯"}}

        ann_line = Annotation("polyline")
        ann_line.points = [QPointF(10, 20), QPointF(30, 40), QPointF(50, 60)]
        ann_line.color = "#ff0000"
        ann_line.line_width = 3
        ann_line.start_marker = "circle"
        ann_line.end_marker = "arrow"

        ann_circle = Annotation("circle")
        ann_circle.points = [QPointF(100, 100)]
        ann_circle.radius_px = 50.0
        ann_circle.center_marker = "cross"

        model.annotations = [ann_line, ann_circle]

        file_path = str(tmp_path / "test_project.json")
        save_project(model, file_path)

        assert os.path.exists(file_path)

        # ファイルが正しくUTF-8で保存されていることを直接確認
        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            assert raw_data["page_color_names"]["0"]["#ff0000"] == "消火栓"

        loaded = load_project(file_path)
        assert loaded.scale_factor == 2.5
        assert loaded.is_calibrated is True
        assert loaded.unit == "mm"
        assert loaded.page_calibrations == {0: 2.5, 1: 5.0}
        assert loaded.page_color_names == {0: {"#ff0000": "消火栓", "#00ff00": "避難誘導灯"}}
        assert len(loaded.annotations) == 2

        l_line = loaded.annotations[0]
        assert l_line.type == "polyline"
        assert len(l_line.points) == 3
        assert l_line.points[0].x() == 10
        assert l_line.points[0].y() == 20
        assert l_line.start_marker == "circle"
        assert l_line.end_marker == "arrow"

        l_circle = loaded.annotations[1]
        assert l_circle.type == "circle"
        assert l_circle.radius_px == 50.0
        assert l_circle.center_marker == "cross"

    def test_load_non_existent_file(self, tmp_path):
        non_existent = str(tmp_path / "does_not_exist.json")
        with pytest.raises(OSError) as exc_info:
            load_project(non_existent)
        assert "プロジェクトファイルの読み込みに失敗しました" in str(exc_info.value)

    def test_load_broken_json(self, tmp_path):
        broken_file = tmp_path / "broken.json"
        broken_file.write_text("{ unclosed json content ...", encoding="utf-8")
        with pytest.raises(ValueError) as exc_info:
            load_project(str(broken_file))
        assert "プロジェクトファイルのJSON解析に失敗しました" in str(exc_info.value)

    def test_load_invalid_model_structure(self, tmp_path):
        invalid_file = tmp_path / "invalid_struct.json"
        # annotations がリストではなく不正な値
        invalid_file.write_text(json.dumps({"annotations": "invalid_not_list"}), encoding="utf-8")
        with pytest.raises(ValueError) as exc_info:
            load_project(str(invalid_file))
        assert "プロジェクトデータの復元に失敗しました" in str(exc_info.value)

    def test_save_to_invalid_directory(self):
        # 存在しないディレクトリ配下への書き込み
        invalid_path = "/non_existent_directory_xyz/project.json"
        with pytest.raises(OSError) as exc_info:
            save_project(DrawingModel(), invalid_path)
        assert "プロジェクトファイルの書き込みに失敗しました" in str(exc_info.value)
