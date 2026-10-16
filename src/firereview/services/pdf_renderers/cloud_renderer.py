from .base import BasePdfRenderer, PdfRenderContext
from ...ui.canvas.utils import compute_cloud_beziers


class CloudPdfRenderer(BasePdfRenderer):
    """雲マーク（クラウド注釈）のPDFレンダラー"""

    def render(self, ctx: PdfRenderContext, ann) -> None:
        if not ann.points or len(ann.points) < 3:
            return
        beziers = compute_cloud_beziers(ann.points)
        if not beziers:
            return

        shape = ctx.page.new_shape()
        for start_pt, ctrl1, ctrl2, end_pt in beziers:
            shape.draw_bezier(
                ctx.to_pdf_pt(start_pt),
                ctx.to_pdf_pt(ctrl1),
                ctx.to_pdf_pt(ctrl2),
                ctx.to_pdf_pt(end_pt),
            )

        _pdf_fill = ctx.fill_color if ctx.fill_opacity > 0 else None
        shape.finish(
            color=ctx.color,
            fill=_pdf_fill,
            width=ann.line_width * ctx.dpi_factor,
            closePath=True,
            stroke_opacity=ctx.stroke_opacity,
            fill_opacity=ctx.fill_opacity if _pdf_fill else 1,
        )
        shape.commit()


CloudRenderer = CloudPdfRenderer
