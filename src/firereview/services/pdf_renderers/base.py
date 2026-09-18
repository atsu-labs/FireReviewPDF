import math
import fitz
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor


class PdfRenderContext:
    """PDF描画に必要なページ情報・座標変換・描画設定をカプセル化するコンテキスト"""

    def __init__(self, page, page_num: int, model, dpi_factor: float, page_font: str, ann):
        self.page = page
        self.page_num = page_num
        self.model = model
        self.dpi_factor = dpi_factor
        self.page_font = page_font

        # ページの回転情報と変換行列
        self.page_rotation = page.rotation
        self.derot_matrix = page.derotation_matrix
        self.rot_matrix = fitz.Matrix(
            self.derot_matrix.a, self.derot_matrix.b,
            self.derot_matrix.c, self.derot_matrix.d,
            0, 0
        )

        # 色と透明度の初期化
        color_value = QColor(ann.color)
        self.color = (
            color_value.red() / 255.0,
            color_value.green() / 255.0,
            color_value.blue() / 255.0,
        )
        self.fill_opacity = ann.fill_opacity / 100.0
        self.stroke_opacity = ann.stroke_opacity / 100.0

        fill_color_value = QColor(ann.fill_color) if ann.fill_color else color_value
        self.fill_color = (
            fill_color_value.red() / 255.0,
            fill_color_value.green() / 255.0,
            fill_color_value.blue() / 255.0,
        )

        self.marker_size = max(ann.line_width * 3, 10 * dpi_factor)

    def to_pdf_pt(self, qp: QPointF) -> fitz.Point:
        """QPointFの画面座標をPDFページ座標（ポイント単位）に変換します"""
        pt = fitz.Point(qp.x() * self.dpi_factor, qp.y() * self.dpi_factor)
        return pt * self.derot_matrix

    def get_baseline_shift(self, font_size: float) -> float:
        """Y軸ベースラインシフト補正量を計算します"""
        return (4 + font_size * 0.85) * self.dpi_factor

    def draw_endpoint_marker(self, point: fitz.Point, neighbor: fitz.Point, marker_type: str):
        """線の端点マーカー（円または矢印）を描画します"""
        if marker_type == "circle":
            self.page.draw_circle(
                point,
                self.marker_size / 2,
                color=self.color,
                fill=self.color,
                width=1,
                stroke_opacity=self.stroke_opacity,
                fill_opacity=self.stroke_opacity,
            )
        elif marker_type == "arrow":
            dx = point.x - neighbor.x
            dy = point.y - neighbor.y
            length = math.sqrt(dx * dx + dy * dy)
            if length == 0:
                return
            dx /= length
            dy /= length
            perp_x, perp_y = -dy, dx
            bx = point.x - dx * self.marker_size
            by = point.y - dy * self.marker_size
            wing1 = fitz.Point(
                bx + perp_x * self.marker_size * 0.45,
                by + perp_y * self.marker_size * 0.45,
            )
            wing2 = fitz.Point(
                bx - perp_x * self.marker_size * 0.45,
                by - perp_y * self.marker_size * 0.45,
            )
            self.page.draw_polyline(
                [point, wing1, wing2],
                color=self.color,
                fill=self.color,
                width=0,
                closePath=True,
                stroke_opacity=self.stroke_opacity,
                fill_opacity=self.stroke_opacity,
            )

    def draw_center_marker(self, center: fitz.Point, marker_type: str):
        """円や円弧の中心マーカー（円、十文字、×）を描画します"""
        size = self.marker_size / 2
        if marker_type == "circle":
            self.page.draw_circle(
                center,
                size,
                color=self.color,
                fill=self.color,
                width=1,
                stroke_opacity=self.stroke_opacity,
                fill_opacity=self.stroke_opacity,
            )
        elif marker_type == "cross":
            self.page.draw_line(
                fitz.Point(center.x - size, center.y),
                fitz.Point(center.x + size, center.y),
                color=self.color,
                width=1.5,
                stroke_opacity=self.stroke_opacity,
            )
            self.page.draw_line(
                fitz.Point(center.x, center.y - size),
                fitz.Point(center.x, center.y + size),
                color=self.color,
                width=1.5,
                stroke_opacity=self.stroke_opacity,
            )
        elif marker_type == "x":
            self.page.draw_line(
                fitz.Point(center.x - size, center.y - size),
                fitz.Point(center.x + size, center.y + size),
                color=self.color,
                width=1.5,
                stroke_opacity=self.stroke_opacity,
            )
            self.page.draw_line(
                fitz.Point(center.x + size, center.y - size),
                fitz.Point(center.x - size, center.y + size),
                color=self.color,
                width=1.5,
                stroke_opacity=self.stroke_opacity,
            )


class BasePdfRenderer:
    """PDF描画ストラテジーの基底クラス"""

    def render(self, ctx: PdfRenderContext, ann) -> None:
        raise NotImplementedError
