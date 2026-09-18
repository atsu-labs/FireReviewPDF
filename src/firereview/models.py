import math
import uuid

class DrawingModel:
    def __init__(self):
        self.scale_factor = 1.0  # mm per pixel
        self.is_calibrated = False
        self.page_calibrations = {}  # {page_num: scale_factor}
        self.page_color_names = {}  # {page_num: {color_hex: name}}
        self.annotations = [] # List of annotation objects
        self.pdf_path = ""
        self.unit = 'm'  # 表示単位: 'm' または 'mm'

    def _apply_scale_to_pages(self, page_num, all_pages, total_pages):
        if all_pages:
            self.page_calibrations = {}
            for p in range(total_pages):
                self.page_calibrations[p] = self.scale_factor
        elif page_num is not None:
            self.page_calibrations[int(page_num)] = self.scale_factor

    def set_calibration(self, p1, p2, real_distance_mm, page_num=None, all_pages=False, total_pages=1):
        pixel_dist = math.sqrt((p2.x() - p1.x())**2 + (p2.y() - p1.y())**2)
        if pixel_dist > 0:
            self.scale_factor = real_distance_mm / pixel_dist
            self.is_calibrated = True
            self._apply_scale_to_pages(page_num, all_pages, total_pages)
            return True
        return False

    def set_calibration_by_ratio(self, ratio_denominator, dpi=150.0, page_num=None, all_pages=False, total_pages=1):
        if ratio_denominator > 0:
            mm_per_pixel_on_pdf = 25.4 / dpi
            self.scale_factor = mm_per_pixel_on_pdf * ratio_denominator
            self.is_calibrated = True
            self._apply_scale_to_pages(page_num, all_pages, total_pages)
            return True
        return False

    def get_scale_factor(self, page_num=None):
        if page_num is not None:
            page_key = int(page_num)
            if page_key in self.page_calibrations:
                return self.page_calibrations[page_key]
            if not self.page_calibrations and self.is_calibrated:
                # 旧データ互換: 全ページ共通スケールとして扱う
                return self.scale_factor
        return self.scale_factor

    def is_page_calibrated(self, page_num=None):
        if page_num is not None:
            if self.page_calibrations:
                return int(page_num) in self.page_calibrations
            return self.is_calibrated
        return self.is_calibrated

    def calculate_real_distance(self, p1, p2, scale_factor=None):
        pixel_dist = math.sqrt((p2.x() - p1.x())**2 + (p2.y() - p1.y())**2)
        sf = self.scale_factor if scale_factor is None else scale_factor
        return pixel_dist * sf

    def calculate_real_area(self, points, scale_factor=None):
        if len(points) < 3:
            return 0.0
        area = 0.0
        n = len(points)
        for i in range(n):
            j = (i + 1) % n
            area += points[i].x() * points[j].y()
            area -= points[j].x() * points[i].y()
        pixel_area = abs(area) / 2.0
        sf = self.scale_factor if scale_factor is None else scale_factor
        return pixel_area * (sf ** 2)

    def to_dict(self):
        return {
            "scale_factor": self.scale_factor,
            "is_calibrated": self.is_calibrated,
            "page_calibrations": self.page_calibrations,
            "page_color_names": {str(k): v for k, v in self.page_color_names.items()},
            "pdf_path": self.pdf_path,
            "unit": self.unit,
            "annotations": [a.to_dict() for a in self.annotations]
        }

    @classmethod
    def from_dict(cls, data):
        model = cls()
        model.scale_factor = data.get("scale_factor", 1.0)
        model.is_calibrated = data.get("is_calibrated", False)
        raw_page_calibrations = data.get("page_calibrations", {})
        model.page_calibrations = {int(k): float(v) for k, v in raw_page_calibrations.items()}
        raw_page_color_names = data.get("page_color_names", {})
        model.page_color_names = {int(k): v for k, v in raw_page_color_names.items()}
        model.pdf_path = data.get("pdf_path", "")
        model.unit = data.get("unit", "m")
        for a_data in data.get("annotations", []):
            model.annotations.append(Annotation.from_dict(a_data))
        return model

class BaseAnnotation:
    """すべての注釈の基底クラス"""
    type: str = "base"

    # 後方互換性のためのデフォルト属性
    radius_px: float = 0.0
    center_marker: str = ""
    start_marker: str = ""
    end_marker: str = ""
    has_border: bool = False
    border_color: str = "#ff0000"
    border_width: int = 2
    has_leader: bool = False
    marker_style: str = "square"
    drag_angle: float = 0.0
    arc_span: float = 30.0
    show_radial_line: bool = False

    def __init__(self, type_name: str = "base"):
        self.id = str(uuid.uuid4())
        self.type = type_name
        self.points = []
        self.color = "#7c4dff"
        self.fill_color = ""
        self.text = ""
        self.font_family = "BIZ UDゴシック"
        self.font_size = 12
        self.line_width = 2
        self.stroke_opacity = 100
        self.fill_opacity = 30
        self.real_value = 0.0
        self.page_num = 0
        self.label_offset = [0.0, 0.0]
        self.is_calculated = False

    def to_dict(self):
        from PySide6.QtCore import QPointF
        pts = []
        for p in self.points:
            if isinstance(p, QPointF):
                pts.append((p.x(), p.y()))
            else:
                pts.append(p)
        return {
            "id": self.id,
            "type": self.type,
            "points": pts,
            "color": self.color,
            "fill_color": self.fill_color,
            "text": self.text,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "line_width": self.line_width,
            "stroke_opacity": self.stroke_opacity,
            "fill_opacity": self.fill_opacity,
            "real_value": self.real_value,
            "radius_px": getattr(self, "radius_px", 0.0),
            "center_marker": getattr(self, "center_marker", ""),
            "start_marker": getattr(self, "start_marker", ""),
            "end_marker": getattr(self, "end_marker", ""),
            "has_border": getattr(self, "has_border", False),
            "border_color": getattr(self, "border_color", "#ff0000"),
            "border_width": getattr(self, "border_width", 2),
            "has_leader": getattr(self, "has_leader", False),
            "page_num": self.page_num,
            "marker_style": getattr(self, "marker_style", "square"),
            "label_offset": self.label_offset,
            "drag_angle": getattr(self, "drag_angle", 0.0),
            "arc_span": getattr(self, "arc_span", 30.0),
            "show_radial_line": getattr(self, "show_radial_line", False),
            "is_calculated": self.is_calculated
        }

    def _apply_dict(self, data: dict):
        from PySide6.QtCore import QPointF
        self.id = data.get("id", str(uuid.uuid4()))
        self.points = [QPointF(p[0], p[1]) for p in data.get("points", [])]
        self.color = data.get("color", "#7c4dff")
        self.fill_color = data.get("fill_color", "")
        self.text = data.get("text", "")
        self.font_family = data.get("font_family", "Arial")
        self.font_size = data.get("font_size", 12)
        self.line_width = data.get("line_width", 2)
        _legacy_opacity = data.get("opacity", 100)  # backward compat
        self.stroke_opacity = data.get("stroke_opacity", _legacy_opacity)
        self.fill_opacity = data.get("fill_opacity", 30)
        self.real_value = data.get("real_value", 0.0)
        self.page_num = data.get("page_num", 0)
        self.label_offset = data.get("label_offset", [0.0, 0.0])
        self.is_calculated = data.get("is_calculated", False)

        for attr in [
            "radius_px", "center_marker", "start_marker", "end_marker",
            "has_border", "border_color", "border_width", "has_leader",
            "marker_style", "drag_angle", "arc_span", "show_radial_line"
        ]:
            if attr in data:
                setattr(self, attr, data[attr])

    @classmethod
    def from_dict(cls, data: dict):
        ann_type = data.get("type", "line")
        target_cls = ANNOTATION_REGISTRY.get(ann_type, cls)
        if (cls is BaseAnnotation or cls is Annotation) and target_cls is not cls:
            return target_cls.from_dict(data)

        ann = cls(ann_type)
        ann._apply_dict(data)
        return ann


class Annotation(BaseAnnotation):
    """注釈クラス（後方互換用ファクトリ兼基底クラス）"""
    def __new__(cls, type_name="line", *args, **kwargs):
        if cls is Annotation:
            subclass = ANNOTATION_REGISTRY.get(type_name)
            if subclass is not None and subclass is not Annotation:
                return super().__new__(subclass)
        return super().__new__(cls)


class LineAnnotation(Annotation):
    """直線注釈"""
    type: str = "line"

    def __init__(self, type_name: str = "line"):
        super().__init__(type_name)


class PolylineAnnotation(Annotation):
    """折れ線・矢印注釈"""
    type: str = "polyline"

    def __init__(self, type_name: str = "polyline"):
        super().__init__(type_name)
        self.start_marker: str = ""
        self.end_marker: str = ""


class PolygonAnnotation(Annotation):
    """多角形注釈"""
    type: str = "polygon"

    def __init__(self, type_name: str = "polygon"):
        super().__init__(type_name)


class CircleAnnotation(Annotation):
    """円注釈"""
    type: str = "circle"

    def __init__(self, type_name: str = "circle"):
        super().__init__(type_name)
        self.radius_px: float = 0.0
        self.center_marker: str = ""


class ArcAnnotation(Annotation):
    """円弧注釈"""
    type: str = "arc"

    def __init__(self, type_name: str = "arc"):
        super().__init__(type_name)
        self.radius_px: float = 0.0
        self.drag_angle: float = 0.0
        self.arc_span: float = 30.0
        self.show_radial_line: bool = False


class MarkerAnnotation(Annotation):
    """カウントマーカー注釈"""
    type: str = "marker"

    def __init__(self, type_name: str = "marker"):
        super().__init__(type_name)
        self.marker_style: str = "square"


class TextAnnotation(Annotation):
    """テキスト・引出線注釈"""
    type: str = "text"

    def __init__(self, type_name: str = "text"):
        super().__init__(type_name)
        self.has_border: bool = False
        self.border_color: str = "#ff0000"
        self.border_width: int = 2
        self.has_leader: bool = False


class LegendAnnotation(Annotation):
    """凡例注釈"""
    type: str = "legend"

    def __init__(self, type_name: str = "legend"):
        super().__init__(type_name)


ANNOTATION_REGISTRY = {
    "line": LineAnnotation,
    "polyline": PolylineAnnotation,
    "polygon": PolygonAnnotation,
    "circle": CircleAnnotation,
    "arc": ArcAnnotation,
    "marker": MarkerAnnotation,
    "text": TextAnnotation,
    "legend": LegendAnnotation,
}
