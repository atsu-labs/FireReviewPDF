import pytest
from PySide6.QtCore import QPointF
from firereview.models import (
    DrawingModel,
    BaseAnnotation,
    Annotation,
    LineAnnotation,
    PolylineAnnotation,
    PolygonAnnotation,
    CircleAnnotation,
    ArcAnnotation,
    MarkerAnnotation,
    TextAnnotation,
    LegendAnnotation,
    ANNOTATION_REGISTRY,
)


class TestAnnotationPolymorphism:
    def test_subclass_hierarchy(self):
        assert issubclass(LineAnnotation, Annotation)
        assert issubclass(PolylineAnnotation, Annotation)
        assert issubclass(PolygonAnnotation, Annotation)
        assert issubclass(CircleAnnotation, Annotation)
        assert issubclass(ArcAnnotation, Annotation)
        assert issubclass(MarkerAnnotation, Annotation)
        assert issubclass(TextAnnotation, Annotation)
        assert issubclass(LegendAnnotation, Annotation)
        assert issubclass(Annotation, BaseAnnotation)

    def test_factory_dispatch_returns_subclasses(self):
        line = Annotation("line")
        assert isinstance(line, LineAnnotation)
        assert line.type == "line"

        circle = Annotation("circle")
        assert isinstance(circle, CircleAnnotation)
        assert circle.type == "circle"
        assert circle.radius_px == 0.0
        assert circle.center_marker == ""

        arc = Annotation("arc")
        assert isinstance(arc, ArcAnnotation)
        assert arc.type == "arc"
        assert arc.arc_span == 30.0
        assert arc.center_marker == ""

        marker = Annotation("marker")
        assert isinstance(marker, MarkerAnnotation)
        assert marker.type == "marker"
        assert marker.marker_style == "square"

        text = Annotation("text")
        assert isinstance(text, TextAnnotation)
        assert text.type == "text"
        assert text.has_border is False

        legend = Annotation("legend")
        assert isinstance(legend, LegendAnnotation)
        assert legend.type == "legend"

    def test_unknown_type_falls_back_to_annotation(self):
        unknown = Annotation("unknown_custom_type")
        assert isinstance(unknown, Annotation)
        assert unknown.type == "unknown_custom_type"

    def test_from_dict_polymorphic_restoration(self):
        data = {
            "type": "circle",
            "points": [(100.0, 150.0)],
            "radius_px": 45.0,
            "center_marker": "cross",
            "color": "#ff0000",
        }
        restored = Annotation.from_dict(data)
        assert isinstance(restored, CircleAnnotation)
        assert restored.type == "circle"
        assert restored.radius_px == 45.0
        assert restored.center_marker == "cross"
        assert restored.color == "#ff0000"
        assert len(restored.points) == 1

    def test_backward_compatible_attribute_access(self):
        line = Annotation("line")
        # LineAnnotationでも安全にデフォルト値が取得可能
        assert line.radius_px == 0.0
        assert line.center_marker == ""
        assert line.has_border is False
        assert line.marker_style == "square"

    def test_drawing_model_with_polymorphic_annotations(self):
        model = DrawingModel()
        model.annotations.append(Annotation("line"))
        model.annotations.append(Annotation("circle"))
        model.annotations.append(Annotation("arc"))
        model.annotations.append(Annotation("text"))

        d = model.to_dict()
        assert len(d["annotations"]) == 4

        restored_model = DrawingModel.from_dict(d)
        assert len(restored_model.annotations) == 4
        assert isinstance(restored_model.annotations[0], LineAnnotation)
        assert isinstance(restored_model.annotations[1], CircleAnnotation)
        assert isinstance(restored_model.annotations[2], ArcAnnotation)
        assert isinstance(restored_model.annotations[3], TextAnnotation)
