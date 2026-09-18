import fitz
from .base import BasePdfRenderer, PdfRenderContext


class MarkerPdfRenderer(BasePdfRenderer):
    """カウントマーカー注釈のPDFレンダラー"""

    def render(self, ctx: PdfRenderContext, ann) -> None:
        if not ann.points:
            return

        pos = ctx.to_pdf_pt(ann.points[0])
        size = 24 * ctx.dpi_factor
        half = size / 2
        marker_style = getattr(ann, "marker_style", "square")

        if marker_style == "square":
            rect = fitz.Rect(pos.x - half, pos.y - half, pos.x + half, pos.y + half)
            # 1. White border glow
            ctx.page.draw_rect(
                rect,
                color=(1.0, 1.0, 1.0),
                fill=ctx.color,
                width=2 * ctx.dpi_factor,
                stroke_opacity=ctx.stroke_opacity,
                fill_opacity=ctx.stroke_opacity,
            )
            # 2. Main color border
            ctx.page.draw_rect(
                rect,
                color=ctx.color,
                width=1.5 * ctx.dpi_factor,
                stroke_opacity=ctx.stroke_opacity,
            )
        elif marker_style == "check":
            # 1. White background disk
            ctx.page.draw_circle(
                pos,
                half,
                color=ctx.color,
                fill=(1.0, 1.0, 1.0),
                width=1.5 * ctx.dpi_factor,
                stroke_opacity=ctx.stroke_opacity,
                fill_opacity=ctx.stroke_opacity,
            )
            # 2. Checkmark path
            p_start = pos + fitz.Point(-6 * ctx.dpi_factor, 0) * ctx.rot_matrix
            p_mid = pos + fitz.Point(-1.5 * ctx.dpi_factor, 4.5 * ctx.dpi_factor) * ctx.rot_matrix
            p_end = pos + fitz.Point(6 * ctx.dpi_factor, -3 * ctx.dpi_factor) * ctx.rot_matrix
            ctx.page.draw_polyline(
                [p_start, p_mid, p_end],
                color=ctx.color,
                width=2.5 * ctx.dpi_factor,
                stroke_opacity=ctx.stroke_opacity,
                closePath=False,
            )
