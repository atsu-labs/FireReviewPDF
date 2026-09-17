import math
import pytest
from PySide6.QtCore import QPointF
from firereview.ui.canvas.utils import point_to_segment_distance, apply_angle_snap


class TestPointToSegmentDistance:
    def test_point_on_segment(self):
        s1 = QPointF(0, 0)
        s2 = QPointF(100, 0)
        pt = QPointF(50, 0)
        dist, proj = point_to_segment_distance(pt, s1, s2)
        assert pytest.approx(dist, abs=1e-6) == 0.0
        assert pytest.approx(proj.x(), abs=1e-6) == 50.0
        assert pytest.approx(proj.y(), abs=1e-6) == 0.0

    def test_point_perpendicular_to_segment(self):
        s1 = QPointF(0, 0)
        s2 = QPointF(100, 0)
        pt = QPointF(50, 30)
        dist, proj = point_to_segment_distance(pt, s1, s2)
        assert pytest.approx(dist, abs=1e-6) == 30.0
        assert pytest.approx(proj.x(), abs=1e-6) == 50.0
        assert pytest.approx(proj.y(), abs=1e-6) == 0.0

    def test_point_beyond_start_point(self):
        s1 = QPointF(10, 0)
        s2 = QPointF(100, 0)
        pt = QPointF(0, 0)
        dist, proj = point_to_segment_distance(pt, s1, s2)
        assert pytest.approx(dist, abs=1e-6) == 10.0
        assert pytest.approx(proj.x(), abs=1e-6) == 10.0
        assert pytest.approx(proj.y(), abs=1e-6) == 0.0

    def test_point_beyond_end_point(self):
        s1 = QPointF(0, 0)
        s2 = QPointF(100, 0)
        pt = QPointF(120, 0)
        dist, proj = point_to_segment_distance(pt, s1, s2)
        assert pytest.approx(dist, abs=1e-6) == 20.0
        assert pytest.approx(proj.x(), abs=1e-6) == 100.0
        assert pytest.approx(proj.y(), abs=1e-6) == 0.0

    def test_zero_length_segment(self):
        s1 = QPointF(50, 50)
        s2 = QPointF(50, 50)
        pt = QPointF(50, 80)
        dist, proj = point_to_segment_distance(pt, s1, s2)
        assert pytest.approx(dist, abs=1e-6) == 30.0
        assert pytest.approx(proj.x(), abs=1e-6) == 50.0
        assert pytest.approx(proj.y(), abs=1e-6) == 50.0


class TestApplyAngleSnap:
    def test_horizontal_snap_positive(self):
        start = QPointF(0, 0)
        # 近い角度 (約5度) -> 0度（水平右向き）にスナップ
        pos = QPointF(100, 10)
        snapped = apply_angle_snap(start, pos)
        assert pytest.approx(snapped.y(), abs=1e-4) == 0.0
        assert pytest.approx(snapped.x(), abs=1e-2) == math.sqrt(100**2 + 10**2)

    def test_vertical_snap_positive(self):
        start = QPointF(0, 0)
        # 近い角度 (約85度) -> 90度（垂直下向き）にスナップ
        pos = QPointF(10, 100)
        snapped = apply_angle_snap(start, pos)
        assert pytest.approx(snapped.x(), abs=1e-4) == 0.0
        assert pytest.approx(snapped.y(), abs=1e-2) == math.sqrt(10**2 + 100**2)

    def test_45_degree_snap(self):
        start = QPointF(0, 0)
        # 約40度 -> 45度にスナップ
        pos = QPointF(100, 85)
        dist = math.sqrt(100**2 + 85**2)
        snapped = apply_angle_snap(start, pos)
        expected_coord = dist * math.cos(math.radians(45))
        assert pytest.approx(snapped.x(), abs=1e-3) == expected_coord
        assert pytest.approx(snapped.y(), abs=1e-3) == expected_coord

    def test_very_small_distance(self):
        start = QPointF(10, 10)
        pos = QPointF(10.0001, 10.0001)
        snapped = apply_angle_snap(start, pos)
        # 距離 < 0.001 の場合はそのまま返る
        assert snapped.x() == pos.x()
        assert snapped.y() == pos.y()
