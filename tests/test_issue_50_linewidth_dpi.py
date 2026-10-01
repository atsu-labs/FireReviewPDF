import os
import fitz
import pytest
from unittest.mock import MagicMock
from PySide6.QtCore import QPointF
from firereview.models import DrawingModel, Annotation
from firereview.services.pdf_exporter import export_pdf_document
from firereview.services.pdf_renderers import (
    LinePdfRenderer,
    PolylinePdfRenderer,
    PolygonPdfRenderer,
    CirclePdfRenderer,
    ArcPdfRenderer,
)
from firereview.services.pdf_renderers.base import PdfRenderContext


class DummyPage:
    def __init__(self):
        self.rotation = 0
        self.derotation_matrix = fitz.Matrix(1, 0, 0, 1, 0, 0)
        self.draw_line_calls = []
        self.draw_polyline_calls = []
        self.draw_circle_calls = []
        self.insert_text_calls = []

    def draw_line(self, p1, p2, **kwargs):
        self.draw_line_calls.append({"p1": p1, "p2": p2, **kwargs})

    def draw_polyline(self, points, **kwargs):
        self.draw_polyline_calls.append({"points": points, **kwargs})

    def draw_circle(self, center, radius, **kwargs):
        self.draw_circle_calls.append({"center": center, "radius": radius, **kwargs})

    def insert_text(self, pos, text, **kwargs):
        self.insert_text_calls.append({"pos": pos, "text": text, **kwargs})


def create_mock_context(page, ann, dpi_factor=72.0 / 150.0):
    model = DrawingModel()
    model.scale_factor = 1.0
    model.is_calibrated = True
    return PdfRenderContext(
        page=page,
        page_num=0,
        model=model,
        dpi_factor=dpi_factor,
        page_font="helv",
        ann=ann,
    )


class TestShapeRenderersLinewidthDpi:
    def test_line_renderer_linewidth_scaled(self):
        page = DummyPage()
        ann = Annotation("line")
        ann.points = [QPointF(0, 0), QPointF(100, 100)]
        ann.line_width = 4
        dpi_factor = 72.0 / 150.0

        ctx = create_mock_context(page, ann, dpi_factor)
        LinePdfRenderer().render(ctx, ann)

        assert len(page.draw_line_calls) == 1
        expected_width = 4 * dpi_factor
        assert page.draw_line_calls[0]["width"] == pytest.approx(expected_width)

    def test_polyline_renderer_linewidth_and_marker_scaled(self):
        page = DummyPage()
        ann = Annotation("polyline")
        ann.points = [QPointF(0, 0), QPointF(50, 50), QPointF(100, 50)]
        ann.line_width = 3
        ann.start_marker = "circle"
        dpi_factor = 72.0 / 150.0

        ctx = create_mock_context(page, ann, dpi_factor)
        PolylinePdfRenderer().render(ctx, ann)

        assert len(page.draw_line_calls) == 2
        expected_width = 3 * dpi_factor
        for call in page.draw_line_calls:
            assert call["width"] == pytest.approx(expected_width)

        # start_marker="circle" -> draw_circle with width=1 * dpi_factor
        assert len(page.draw_circle_calls) == 1
        assert page.draw_circle_calls[0]["width"] == pytest.approx(1 * dpi_factor)

    def test_polygon_renderer_linewidth_scaled(self):
        page = DummyPage()
        ann = Annotation("polygon")
        ann.points = [QPointF(0, 0), QPointF(50, 0), QPointF(25, 50)]
        ann.line_width = 5
        dpi_factor = 72.0 / 150.0

        ctx = create_mock_context(page, ann, dpi_factor)
        PolygonPdfRenderer().render(ctx, ann)

        assert len(page.draw_polyline_calls) == 1
        expected_width = 5 * dpi_factor
        assert page.draw_polyline_calls[0]["width"] == pytest.approx(expected_width)

    def test_circle_renderer_linewidth_and_center_marker_scaled(self):
        page = DummyPage()
        ann = Annotation("circle")
        ann.points = [QPointF(100, 100)]
        ann.radius_px = 50.0
        ann.line_width = 2
        ann.center_marker = "cross"
        dpi_factor = 72.0 / 150.0

        ctx = create_mock_context(page, ann, dpi_factor)
        CirclePdfRenderer().render(ctx, ann)

        # Circle outline
        assert len(page.draw_circle_calls) == 1
        expected_width = 2 * dpi_factor
        assert page.draw_circle_calls[0]["width"] == pytest.approx(expected_width)

        # Cross marker (2 lines with width=1.5 * dpi_factor)
        assert len(page.draw_line_calls) == 2
        for call in page.draw_line_calls:
            assert call["width"] == pytest.approx(1.5 * dpi_factor)

    def test_arc_renderer_linewidth_and_radial_line_scaled(self):
        page = DummyPage()
        ann = Annotation("arc")
        ann.points = [QPointF(100, 100)]
        ann.radius_px = 40.0
        ann.line_width = 3
        ann.show_radial_line = True
        dpi_factor = 72.0 / 150.0

        ctx = create_mock_context(page, ann, dpi_factor)
        ArcPdfRenderer().render(ctx, ann)

        # All lines (arc segments + radial line) should use ann.line_width * dpi_factor
        expected_width = 3 * dpi_factor
        assert len(page.draw_line_calls) > 0
        for call in page.draw_line_calls:
            assert call["width"] == pytest.approx(expected_width)


class TestPdfExportEndToEndWithLinewidthDpi:
    def test_export_pdf_document_end_to_end(self, tmp_path):
        pdf_path = str(tmp_path / "source.pdf")
        doc = fitz.open()
        doc.new_page(width=595, height=842)
        doc.save(pdf_path)
        doc.close()

        model = DrawingModel()
        model.pdf_path = pdf_path

        # Add line, circle, polygon
        line = Annotation("line")
        line.points = [QPointF(50, 50), QPointF(200, 50)]
        line.line_width = 4
        model.annotations.append(line)

        circle = Annotation("circle")
        circle.points = [QPointF(200, 200)]
        circle.radius_px = 50.0
        circle.line_width = 2
        circle.center_marker = "x"
        model.annotations.append(circle)

        out_path = str(tmp_path / "out.pdf")
        export_pdf_document(model, out_path)

        assert os.path.exists(out_path)
        assert os.path.getsize(out_path) > 0
        out_doc = fitz.open(out_path)
        assert len(out_doc) == 1
        out_doc.close()
