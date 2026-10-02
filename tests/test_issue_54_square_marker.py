import pytest
import fitz
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPixmap, QPainter, QColor
from firereview.models import DrawingModel, Annotation
from firereview.services.pdf_renderers import MarkerPdfRenderer, LegendPdfRenderer
from firereview.services.pdf_renderers.base import PdfRenderContext
from firereview.ui.canvas.items import MarkerItem, LegendItem


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class DummyPage:
    def __init__(self):
        self.rotation = 0
        self.derotation_matrix = fitz.Matrix(1, 0, 0, 1, 0, 0)
        self.draw_rect_calls = []
        self.draw_polyline_calls = []
        self.draw_line_calls = []
        self.draw_circle_calls = []
        self.insert_text_calls = []

    def draw_rect(self, rect, **kwargs):
        self.draw_rect_calls.append({"rect": rect, **kwargs})

    def draw_polyline(self, points, **kwargs):
        self.draw_polyline_calls.append({"points": points, **kwargs})

    def draw_line(self, p1, p2, **kwargs):
        self.draw_line_calls.append({"p1": p1, "p2": p2, **kwargs})

    def draw_circle(self, center, radius, **kwargs):
        self.draw_circle_calls.append({"center": center, "radius": radius, **kwargs})

    def insert_text(self, pos, text, **kwargs):
        self.insert_text_calls.append({"pos": pos, "text": text, **kwargs})


def create_context(page, ann, dpi_factor=72.0 / 150.0):
    model = DrawingModel()
    return PdfRenderContext(
        page=page,
        page_num=0,
        model=model,
        dpi_factor=dpi_factor,
        page_font="helv",
        ann=ann,
    )


class TestMarkerPdfRendererSquare:
    def test_square_marker_single_draw_rect_and_size_20(self):
        page = DummyPage()
        ann = Annotation("marker")
        ann.points = [QPointF(100, 100)]
        ann.marker_style = "square"
        ann.color = "#ff1744"
        dpi_factor = 72.0 / 150.0

        ctx = create_context(page, ann, dpi_factor)
        MarkerPdfRenderer().render(ctx, ann)

        # 二重描画ではなく単一描画（1回のみ）であること
        assert len(page.draw_rect_calls) == 1
        call = page.draw_rect_calls[0]

        # サイズが 20 * dpi_factor（幅・高さ）であること
        rect = call["rect"]
        expected_size = 20 * dpi_factor
        assert rect.width == pytest.approx(expected_size)
        assert rect.height == pytest.approx(expected_size)

        # 線幅が 2 * dpi_factor であること
        assert call["width"] == pytest.approx(2 * dpi_factor)

        # 白枠ではなくメイン色（ctx.color）で線と塗りが指定されていること
        assert call["color"] == ctx.color
        assert call["fill"] == ctx.color


class TestLegendPdfRendererSquare:
    def test_legend_square_marker_single_draw_polyline(self):
        page = DummyPage()
        ann = Annotation("legend")
        ann.points = [QPointF(50, 50)]
        ann.font_size = 12
        dpi_factor = 72.0 / 150.0

        ctx = create_context(page, ann, dpi_factor)
        # モデルに四角形マーカーを1件登録
        m = Annotation("marker")
        m.page_num = 0
        m.marker_style = "square"
        m.color = "#2979ff"
        ctx.model.annotations.append(m)

        LegendPdfRenderer().render(ctx, ann)

        # draw_polyline の呼び出しを確認（カード外枠以外に、白枠の二重描画がなくメイン色単一であること）
        # 1件目は凡例カードの背景外枠
        marker_polylines = page.draw_polyline_calls[1:]
        assert len(marker_polylines) == 1
        poly_call = marker_polylines[0]

        # 白（1.0, 1.0, 1.0）ではなくメイン色（青）であること
        color_val = poly_call["color"]
        assert color_val != (1.0, 1.0, 1.0)
        assert poly_call["fill"] == color_val
        assert poly_call["width"] == pytest.approx(2 * dpi_factor)


class TestMarkerItemCanvasPaint:
    def test_marker_item_paint_execution(self, qapp):
        item = MarkerItem(marker_style="square", color="#ff1744", opacity=80)
        pixmap = QPixmap(100, 100)
        painter = QPainter(pixmap)
        # paintがエラーなく直角四角形描画を実行できること
        item.paint(painter, None, None)
        painter.end()
