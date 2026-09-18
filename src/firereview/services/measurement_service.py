import math
from typing import List, Optional
from PySide6.QtCore import QPointF
from firereview.models import BaseAnnotation, DrawingModel


class MeasurementService:
    """キャリブレーション、実寸法・面積計算、単位変換、表示フォーマットを担当するサービス"""

    # 縮尺比率を整数表示に丸める際の許容差
    SCALE_RATIO_ROUNDING_TOLERANCE = 0.05
    # PDF基準レンダリング解像度
    DEFAULT_RENDER_DPI = 150.0

    @staticmethod
    def calculate_distance_mm(points: List[QPointF], scale_factor: float) -> float:
        """折れ線（または直線）の頂点リストとスケールファクターから実距離（mm）を計算します"""
        if len(points) < 2 or scale_factor <= 0:
            return 0.0
        total_px = sum(
            math.sqrt((points[i + 1].x() - points[i].x()) ** 2 +
                      (points[i + 1].y() - points[i].y()) ** 2)
            for i in range(len(points) - 1)
        )
        return total_px * scale_factor

    @staticmethod
    def calculate_circle_radius_mm(radius_px: float, real_value: float, scale_factor: float) -> float:
        """円のピクセル半径または実寸法から実半径（mm）を計算します"""
        if scale_factor <= 0:
            return 0.0
        r_px = radius_px if radius_px > 0 else (real_value / scale_factor if real_value > 0 else 0.0)
        return r_px * scale_factor

    @staticmethod
    def calculate_arc_radius_mm(radius_px: float, real_value: float, scale_factor: float) -> float:
        """円弧のピクセル半径または実寸法から実半径（mm）を計算します"""
        if scale_factor <= 0:
            return 0.0
        r_px = radius_px
        if r_px <= 0 and real_value > 0:
            r_px = real_value / scale_factor
        return r_px * scale_factor

    @classmethod
    def calculate_annotation_values(cls, ann: BaseAnnotation, scale_factor: float, model: DrawingModel) -> None:
        """指定されたアノテーションの実寸法・面積および表示テキストを計算・更新します"""
        if ann.type in ("line", "polyline") and len(ann.points) >= 2:
            total = cls.calculate_distance_mm(ann.points, scale_factor)
            ann.real_value = total
            ann.text = cls.format_distance(total, model.unit)
        elif ann.type == "polygon" and len(ann.points) >= 3:
            area_mm2 = model.calculate_real_area(ann.points, scale_factor)
            ann.real_value = area_mm2
            ann.text = cls.format_area(area_mm2, model.unit)
        elif ann.type == "circle":
            radius_mm = cls.calculate_circle_radius_mm(
                getattr(ann, "radius_px", 0.0), ann.real_value, scale_factor
            )
            ann.real_value = radius_mm
            ann.text = cls.format_radius(radius_mm, model.unit)
        elif ann.type == "arc":
            radius_mm = cls.calculate_arc_radius_mm(
                getattr(ann, "radius_px", 0.0), ann.real_value, scale_factor
            )
            ann.real_value = radius_mm
            ann.text = cls.format_radius(radius_mm, model.unit)

    @classmethod
    def recalculate_all_annotations(cls, model: DrawingModel) -> None:
        """モデル内の全アノテーションの実寸法・面積および表示テキストを一括再計算します"""
        for ann in model.annotations:
            sf = model.get_scale_factor(ann.page_num)
            if sf <= 0:
                continue
            if getattr(ann, "is_calculated", False):
                cls.calculate_annotation_values(ann, sf, model)

    @staticmethod
    def format_distance(value_mm: float, unit: str = "m") -> str:
        """実距離（mm）を表示用文字列にフォーマットします"""
        if unit == 'm':
            return f"{value_mm / 1000:.3f} m"
        return f"{value_mm:.1f} mm"

    @staticmethod
    def format_area(value_mm2: float, unit: str = "m") -> str:
        """実面積（mm²）を表示用文字列にフォーマットします"""
        if unit == 'm':
            return f"{value_mm2 / 1_000_000:.2f} m²"
        return f"{value_mm2:.1f} mm²"

    @staticmethod
    def format_radius(value_mm: float, unit: str = "m") -> str:
        """実半径（mm）を表示用文字列にフォーマットします"""
        if unit == 'm':
            return f"R={value_mm / 1000:.3f} m"
        return f"R={value_mm:.1f} mm"

    @classmethod
    def format_scale_ratio(
        cls,
        scale_factor: float,
        dpi: float = DEFAULT_RENDER_DPI,
        tolerance: float = SCALE_RATIO_ROUNDING_TOLERANCE
    ) -> str:
        """スケールファクター（mm/px）から縮尺比率文字列（例: '1/50'）を生成します"""
        mm_per_pixel_on_pdf = 25.4 / dpi
        if scale_factor <= 0 or mm_per_pixel_on_pdf <= 0:
            return ""
        ratio = scale_factor / mm_per_pixel_on_pdf
        rounded = round(ratio)
        if abs(ratio - rounded) < tolerance:
            return f"1/{rounded}"
        return f"1/{ratio:.1f}"
