import pytest
from PySide6.QtCore import QPointF
from firereview.models import DrawingModel, Annotation
from firereview.services.measurement_service import MeasurementService


class TestMeasurementService:
    def test_calculate_distance_mm(self):
        pts = [QPointF(0, 0), QPointF(30, 40)]  # 50 px
        scale_factor = 2.0  # 2 mm/px
        dist = MeasurementService.calculate_distance_mm(pts, scale_factor)
        assert pytest.approx(dist, abs=1e-6) == 100.0

    def test_calculate_distance_mm_empty_or_single(self):
        assert MeasurementService.calculate_distance_mm([], 2.0) == 0.0
        assert MeasurementService.calculate_distance_mm([QPointF(0, 0)], 2.0) == 0.0
        assert MeasurementService.calculate_distance_mm([QPointF(0, 0), QPointF(10, 10)], 0.0) == 0.0

    def test_calculate_circle_radius_mm(self):
        # ピクセル半径から計算
        r1 = MeasurementService.calculate_circle_radius_mm(radius_px=50.0, real_value=0.0, scale_factor=3.0)
        assert pytest.approx(r1, abs=1e-6) == 150.0

        # real_valueから復元計算
        r2 = MeasurementService.calculate_circle_radius_mm(radius_px=0.0, real_value=120.0, scale_factor=3.0)
        assert pytest.approx(r2, abs=1e-6) == 120.0

    def test_calculate_arc_radius_mm(self):
        r1 = MeasurementService.calculate_arc_radius_mm(radius_px=40.0, real_value=0.0, scale_factor=2.5)
        assert pytest.approx(r1, abs=1e-6) == 100.0

    def test_calculate_annotation_values_line(self):
        model = DrawingModel()
        model.unit = "m"
        line = Annotation("line")
        line.points = [QPointF(0, 0), QPointF(100, 0)]
        MeasurementService.calculate_annotation_values(line, scale_factor=10.0, model=model)

        # 100 px * 10 mm/px = 1000 mm = 1.000 m
        assert pytest.approx(line.real_value, abs=1e-6) == 1000.0
        assert line.text == "1.000 m"

    def test_calculate_annotation_values_polygon(self):
        model = DrawingModel()
        model.unit = "m"
        poly = Annotation("polygon")
        poly.points = [QPointF(0, 0), QPointF(100, 0), QPointF(100, 100), QPointF(0, 100)]
        # 10,000 px^2 * (10 mm/px)^2 = 1,000,000 mm^2 = 1.00 m^2
        MeasurementService.calculate_annotation_values(poly, scale_factor=10.0, model=model)
        assert pytest.approx(poly.real_value, abs=1e-6) == 1_000_000.0
        assert poly.text == "1.00 m²"

    def test_recalculate_all_annotations(self):
        model = DrawingModel()
        model.unit = "mm"
        model.scale_factor = 5.0
        model.is_calibrated = True

        line = Annotation("line")
        line.points = [QPointF(0, 0), QPointF(20, 0)]
        line.is_calculated = True
        model.annotations.append(line)

        MeasurementService.recalculate_all_annotations(model)
        # 20 px * 5 mm/px = 100 mm
        assert pytest.approx(line.real_value, abs=1e-6) == 100.0
        assert line.text == "100.0 mm"

    def test_format_helpers(self):
        # 距離
        assert MeasurementService.format_distance(1500.0, "m") == "1.500 m"
        assert MeasurementService.format_distance(1500.0, "mm") == "1500.0 mm"

        # 面積
        assert MeasurementService.format_area(2_500_000.0, "m") == "2.50 m²"
        assert MeasurementService.format_area(250.4, "mm") == "250.4 mm²"

        # 半径
        assert MeasurementService.format_radius(2000.0, "m") == "R=2.000 m"
        assert MeasurementService.format_radius(50.5, "mm") == "R=50.5 mm"

    def test_format_scale_ratio(self):
        # 150 DPI: mm_per_px = 25.4 / 150
        # 1/50 スケール: sf = (25.4 / 150) * 50 = 8.466667
        sf_50 = (25.4 / 150.0) * 50.0
        assert MeasurementService.format_scale_ratio(sf_50, dpi=150.0) == "1/50"

        sf_100 = (25.4 / 150.0) * 100.0
        assert MeasurementService.format_scale_ratio(sf_100, dpi=150.0) == "1/100"

        # 不正値
        assert MeasurementService.format_scale_ratio(0.0) == ""
        assert MeasurementService.format_scale_ratio(-5.0) == ""
