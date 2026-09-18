import os
import fitz
import pytest
from PySide6.QtCore import QPointF
from firereview.models import DrawingModel, Annotation
from firereview.services.pdf_exporter import export_pdf_document
from firereview.services.pdf_renderers import (
    get_renderer,
    PDF_RENDERER_REGISTRY,
    LinePdfRenderer,
    CirclePdfRenderer,
    ArcPdfRenderer,
    TextPdfRenderer,
    MarkerPdfRenderer,
    LegendPdfRenderer,
)


class TestPdfRenderersRegistry:
    def test_registered_renderers(self):
        assert isinstance(get_renderer("line"), LinePdfRenderer)
        assert isinstance(get_renderer("circle"), CirclePdfRenderer)
        assert isinstance(get_renderer("arc"), ArcPdfRenderer)
        assert isinstance(get_renderer("text"), TextPdfRenderer)
        assert isinstance(get_renderer("marker"), MarkerPdfRenderer)
        assert isinstance(get_renderer("legend"), LegendPdfRenderer)
        assert get_renderer("non_existent_type") is None


class TestPdfExportEndToEnd:
    @pytest.fixture
    def base_pdf_path(self, tmp_path):
        pdf_path = str(tmp_path / "source.pdf")
        doc = fitz.open()
        doc.new_page(width=595, height=842)
        doc.save(pdf_path)
        doc.close()
        return pdf_path

    def test_export_all_annotation_types(self, base_pdf_path, tmp_path):
        model = DrawingModel()
        model.pdf_path = base_pdf_path
        model.scale_factor = 2.0
        model.is_calibrated = True

        # 1. Line
        line = Annotation("line")
        line.points = [QPointF(50, 50), QPointF(200, 50)]
        line.text = "Line 10m"
        model.annotations.append(line)

        # 2. Polyline with markers
        polyline = Annotation("polyline")
        polyline.points = [QPointF(50, 100), QPointF(150, 100), QPointF(150, 150)]
        polyline.start_marker = "circle"
        polyline.end_marker = "arrow"
        polyline.text = "Path"
        model.annotations.append(polyline)

        # 3. Polygon
        polygon = Annotation("polygon")
        polygon.points = [QPointF(50, 200), QPointF(150, 200), QPointF(100, 280)]
        polygon.fill_color = "#00ff00"
        polygon.fill_opacity = 40
        polygon.text = "Zone"
        model.annotations.append(polygon)

        # 4. Circle
        circle = Annotation("circle")
        circle.points = [QPointF(300, 200)]
        circle.radius_px = 60.0
        circle.center_marker = "cross"
        circle.text = "Radius"
        model.annotations.append(circle)

        # 5. Arc
        arc = Annotation("arc")
        arc.points = [QPointF(300, 400)]
        arc.radius_px = 50.0
        arc.drag_angle = 45.0
        arc.arc_span = 60.0
        arc.show_radial_line = True
        arc.center_marker = "circle"
        arc.text = "Arc"
        model.annotations.append(arc)

        # 6. Marker (square and check)
        m1 = Annotation("marker")
        m1.points = [QPointF(50, 350)]
        m1.marker_style = "square"
        m1.color = "#ff1744"
        model.annotations.append(m1)

        m2 = Annotation("marker")
        m2.points = [QPointF(80, 350)]
        m2.marker_style = "check"
        m2.color = "#2979ff"
        model.annotations.append(m2)

        # 7. Text with border and leader line
        text = Annotation("text")
        text.points = [QPointF(200, 500), QPointF(300, 550)]
        text.text = "Multiline\nComment"
        text.has_border = True
        text.has_leader = True
        model.annotations.append(text)

        # 8. Legend
        legend = Annotation("legend")
        legend.points = [QPointF(50, 600)]
        model.annotations.append(legend)

        output_path = str(tmp_path / "exported.pdf")
        export_pdf_document(model, output_path)

        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0

        # Verify exported PDF is valid
        out_doc = fitz.open(output_path)
        assert len(out_doc) == 1
        out_doc.close()
