from .base import BasePdfRenderer, PdfRenderContext
from .fonts import get_or_register_font, get_windows_font_path, get_font_object
from .shape_renderers import (
    LinePdfRenderer,
    PolylinePdfRenderer,
    PolygonPdfRenderer,
    CirclePdfRenderer,
    ArcPdfRenderer,
)
from .text_renderer import TextPdfRenderer
from .marker_renderer import MarkerPdfRenderer
from .legend_renderer import LegendPdfRenderer

PDF_RENDERER_REGISTRY = {
    "line": LinePdfRenderer(),
    "polyline": PolylinePdfRenderer(),
    "polygon": PolygonPdfRenderer(),
    "circle": CirclePdfRenderer(),
    "arc": ArcPdfRenderer(),
    "marker": MarkerPdfRenderer(),
    "text": TextPdfRenderer(),
    "legend": LegendPdfRenderer(),
}


def get_renderer(ann_type: str) -> BasePdfRenderer | None:
    """指定された注釈タイプに対応するPDFレンダラーインスタンスを返します"""
    return PDF_RENDERER_REGISTRY.get(ann_type)


def register_renderer(ann_type: str, renderer: BasePdfRenderer) -> None:
    """新規の注釈タイプと対応するPDFレンダラーをレジストリに登録します"""
    PDF_RENDERER_REGISTRY[ann_type] = renderer


__all__ = [
    "BasePdfRenderer",
    "PdfRenderContext",
    "get_or_register_font",
    "get_windows_font_path",
    "get_font_object",
    "LinePdfRenderer",
    "PolylinePdfRenderer",
    "PolygonPdfRenderer",
    "CirclePdfRenderer",
    "ArcPdfRenderer",
    "TextPdfRenderer",
    "MarkerPdfRenderer",
    "LegendPdfRenderer",
    "PDF_RENDERER_REGISTRY",
    "get_renderer",
    "register_renderer",
]
