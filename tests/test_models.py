import math
import pytest
from PySide6.QtCore import QPointF
from firereview.models import DrawingModel, Annotation


class TestDrawingModelCalibration:
    def test_default_initialization(self):
        model = DrawingModel()
        assert model.scale_factor == 1.0
        assert not model.is_calibrated
        assert model.unit == "m"
        assert model.annotations == []
        assert model.page_calibrations == {}
        assert model.page_color_names == {}

    def test_set_calibration_success(self):
        model = DrawingModel()
        p1 = QPointF(0, 0)
        p2 = QPointF(100, 0)
        # 100 px = 1000 mm -> scale_factor = 10.0 mm/px
        success = model.set_calibration(p1, p2, 1000.0, page_num=0)
        assert success is True
        assert model.is_calibrated is True
        assert pytest.approx(model.scale_factor, abs=1e-6) == 10.0
        assert model.page_calibrations.get(0) == 10.0

    def test_set_calibration_zero_distance(self):
        model = DrawingModel()
        p1 = QPointF(50, 50)
        p2 = QPointF(50, 50)
        success = model.set_calibration(p1, p2, 1000.0)
        assert success is False
        assert model.is_calibrated is False
        assert model.scale_factor == 1.0

    def test_set_calibration_all_pages(self):
        model = DrawingModel()
        p1 = QPointF(0, 0)
        p2 = QPointF(0, 200)
        # 200 px = 2000 mm -> scale_factor = 10.0
        success = model.set_calibration(p1, p2, 2000.0, all_pages=True, total_pages=3)
        assert success is True
        assert len(model.page_calibrations) == 3
        for page in range(3):
            assert model.get_scale_factor(page) == 10.0
            assert model.is_page_calibrated(page) is True

    def test_set_calibration_by_ratio(self):
        model = DrawingModel()
        # 1/100, 150 DPI
        # mm_per_pixel = 25.4 / 150
        # scale_factor = (25.4 / 150) * 100
        expected = (25.4 / 150.0) * 100.0
        success = model.set_calibration_by_ratio(100, dpi=150.0, page_num=1)
        assert success is True
        assert model.is_calibrated is True
        assert pytest.approx(model.get_scale_factor(1), abs=1e-6) == expected

    def test_set_calibration_by_ratio_invalid(self):
        model = DrawingModel()
        assert model.set_calibration_by_ratio(0) is False
        assert model.set_calibration_by_ratio(-50) is False
        assert model.is_calibrated is False


class TestDrawingModelCalculations:
    def test_calculate_real_distance(self):
        model = DrawingModel()
        model.scale_factor = 2.0  # 2 mm/px
        p1 = QPointF(0, 0)
        p2 = QPointF(30, 40)  # 50 px
        dist = model.calculate_real_distance(p1, p2)
        assert pytest.approx(dist, abs=1e-6) == 100.0

    def test_calculate_real_distance_override_scale(self):
        model = DrawingModel()
        model.scale_factor = 2.0
        p1 = QPointF(0, 0)
        p2 = QPointF(10, 0)  # 10 px
        dist = model.calculate_real_distance(p1, p2, scale_factor=5.0)
        assert pytest.approx(dist, abs=1e-6) == 50.0

    def test_calculate_real_area_less_than_3_points(self):
        model = DrawingModel()
        assert model.calculate_real_area([]) == 0.0
        assert model.calculate_real_area([QPointF(0, 0)]) == 0.0
        assert model.calculate_real_area([QPointF(0, 0), QPointF(10, 10)]) == 0.0

    def test_calculate_real_area_rectangle(self):
        model = DrawingModel()
        model.scale_factor = 1.0
        pts = [
            QPointF(0, 0),
            QPointF(100, 0),
            QPointF(100, 50),
            QPointF(0, 50)
        ]
        # 100 * 50 = 5000 px^2
        area = model.calculate_real_area(pts)
        assert pytest.approx(area, abs=1e-6) == 5000.0

    def test_calculate_real_area_with_scale_factor(self):
        model = DrawingModel()
        model.scale_factor = 3.0  # 3 mm/px -> area factor = 9.0
        pts = [
            QPointF(0, 0),
            QPointF(40, 0),
            QPointF(0, 30)
        ]
        # 直角三角形: 40 * 30 / 2 = 600 px^2
        # 実面積: 600 * 3^2 = 5400
        area = model.calculate_real_area(pts)
        assert pytest.approx(area, abs=1e-6) == 5400.0

    def test_calculate_real_area_vertex_order(self):
        model = DrawingModel()
        model.scale_factor = 2.0
        # 反時計回り
        ccw_pts = [QPointF(0, 0), QPointF(10, 0), QPointF(10, 10), QPointF(0, 10)]
        # 時計回り（逆順）
        cw_pts = [QPointF(0, 0), QPointF(0, 10), QPointF(10, 10), QPointF(10, 0)]

        area_ccw = model.calculate_real_area(ccw_pts)
        area_cw = model.calculate_real_area(cw_pts)

        expected = 100.0 * (2.0 ** 2)  # 400.0
        assert pytest.approx(area_ccw, abs=1e-6) == expected
        assert pytest.approx(area_cw, abs=1e-6) == expected


class TestAnnotation:
    def test_annotation_defaults(self):
        ann = Annotation("circle")
        assert ann.type == "circle"
        assert ann.color == "#7c4dff"
        assert ann.stroke_opacity == 100
        assert ann.fill_opacity == 30
        assert ann.line_width == 2
        assert ann.page_num == 0
        assert ann.points == []

    def test_annotation_to_dict_and_from_dict(self):
        ann = Annotation("arc")
        ann.points = [QPointF(10.5, 20.25)]
        ann.color = "#00ff00"
        ann.fill_color = "#0000ff"
        ann.radius_px = 75.5
        ann.arc_span = 45.0
        ann.drag_angle = 90.0
        ann.show_radial_line = True
        ann.marker_style = "check"
        ann.label_offset = [5.0, -10.0]
        ann.page_num = 2

        data = ann.to_dict()
        assert data["type"] == "arc"
        assert data["points"] == [(10.5, 20.25)]
        assert data["radius_px"] == 75.5
        assert data["arc_span"] == 45.0
        assert data["drag_angle"] == 90.0
        assert data["show_radial_line"] is True

        restored = Annotation.from_dict(data)
        assert restored.id == ann.id
        assert restored.type == "arc"
        assert len(restored.points) == 1
        assert restored.points[0].x() == 10.5
        assert restored.points[0].y() == 20.25
        assert restored.color == "#00ff00"
        assert restored.fill_color == "#0000ff"
        assert restored.radius_px == 75.5
        assert restored.arc_span == 45.0
        assert restored.drag_angle == 90.0
        assert restored.show_radial_line is True
        assert restored.marker_style == "check"
        assert restored.label_offset == [5.0, -10.0]
        assert restored.page_num == 2

    def test_annotation_legacy_opacity_compatibility(self):
        data = {
            "type": "line",
            "points": [(0, 0), (10, 10)],
            "opacity": 60  # 旧形式のキー
        }
        restored = Annotation.from_dict(data)
        assert restored.stroke_opacity == 60


class TestDrawingModelSerialization:
    def test_model_to_dict_and_from_dict(self):
        model = DrawingModel()
        model.scale_factor = 1.25
        model.is_calibrated = True
        model.unit = "mm"
        model.pdf_path = "/path/to/sample.pdf"
        model.page_calibrations = {0: 1.25, 1: 2.5}
        model.page_color_names = {0: {"#ff0000": "赤ライン"}}

        ann1 = Annotation("line")
        ann1.points = [QPointF(0, 0), QPointF(50, 50)]
        model.annotations.append(ann1)

        data = model.to_dict()
        assert data["scale_factor"] == 1.25
        assert data["is_calibrated"] is True
        assert data["unit"] == "mm"
        assert data["pdf_path"] == "/path/to/sample.pdf"
        assert len(data["annotations"]) == 1

        restored = DrawingModel.from_dict(data)
        assert restored.scale_factor == 1.25
        assert restored.is_calibrated is True
        assert restored.unit == "mm"
        assert restored.pdf_path == "/path/to/sample.pdf"
        assert restored.page_calibrations == {0: 1.25, 1: 2.5}
        assert restored.page_color_names == {0: {"#ff0000": "赤ライン"}}
        assert len(restored.annotations) == 1
        assert restored.annotations[0].type == "line"
        assert len(restored.annotations[0].points) == 2
