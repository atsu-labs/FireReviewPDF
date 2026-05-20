import math
import uuid

class DrawingModel:
    def __init__(self):
        self.scale_factor = 1.0  # mm per pixel
        self.is_calibrated = False
        self.page_calibrations = {}  # {page_num: scale_factor}
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
        model.pdf_path = data.get("pdf_path", "")
        model.unit = data.get("unit", "m")
        for a_data in data.get("annotations", []):
            model.annotations.append(Annotation.from_dict(a_data))
        return model

class Annotation:
    def __init__(self, type):
        self.id = str(uuid.uuid4())
        self.type = type # 'line', 'polyline', 'polygon', 'circle', 'text'
        self.points = [] # List of QPointF or (x,y) tuples? internally let's use QPointF
        self.color = "#7c4dff"
        self.fill_color = ""  # Optional fill color; empty means derive from color
        self.text = ""
        self.font_family = "Arial"
        self.font_size = 12
        self.line_width = 2
        self.stroke_opacity = 100
        self.fill_opacity = 30
        self.real_value = 0.0
        self.radius_px = 0.0  # For circle: radius in pixels (stored when uncalibrated)
        self.center_marker = ""  # For circles: "", "circle", "cross", "x"
        self.start_marker = ""   # For polylines: "", "circle", "arrow"
        self.end_marker = ""     # For polylines: "", "circle", "arrow"
        self.page_num = 0

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
            "radius_px": self.radius_px,
            "center_marker": self.center_marker,
            "start_marker": self.start_marker,
            "end_marker": self.end_marker,
            "page_num": self.page_num
        }

    @classmethod
    def from_dict(cls, data):
        from PySide6.QtCore import QPointF
        ann = cls(data["type"])
        ann.id = data.get("id", str(uuid.uuid4()))
        ann.points = [QPointF(p[0], p[1]) for p in data.get("points", [])]
        ann.color = data.get("color", "#7c4dff")
        ann.fill_color = data.get("fill_color", "")
        ann.text = data.get("text", "")
        ann.font_family = data.get("font_family", "Arial")
        ann.font_size = data.get("font_size", 12)
        ann.line_width = data.get("line_width", 2)
        _legacy_opacity = data.get("opacity", 100)  # backward compat
        ann.stroke_opacity = data.get("stroke_opacity", _legacy_opacity)
        ann.fill_opacity = data.get("fill_opacity", 30)
        ann.real_value = data.get("real_value", 0.0)
        ann.radius_px = data.get("radius_px", 0.0)
        ann.center_marker = data.get("center_marker", "")
        ann.start_marker = data.get("start_marker", "")
        ann.end_marker = data.get("end_marker", "")
        ann.page_num = data.get("page_num", 0)
        return ann
