import fitz
from PySide6.QtGui import QColor
from .base import BasePdfRenderer, PdfRenderContext
from .fonts import get_font_object


class TextPdfRenderer(BasePdfRenderer):
    """テキスト・引出線注釈のPDFレンダラー"""

    def render(self, ctx: PdfRenderContext, ann) -> None:
        if not ann.points:
            return

        pos = ctx.to_pdf_pt(ann.points[0])
        fontsize = ann.font_size * ctx.dpi_factor
        dy = ctx.get_baseline_shift(ann.font_size)
        lines = (ann.text or "").split('\n')
        line_height = fontsize * 1.2

        for i, line in enumerate(lines):
            dy_pt = fitz.Point(0, dy + i * line_height) * ctx.rot_matrix
            ctx.page.insert_text(
                pos + dy_pt,
                line,
                color=ctx.color,
                fontsize=fontsize,
                fontname=ctx.page_font,
                fill_opacity=ctx.stroke_opacity,
                rotate=ctx.page_rotation,
            )

        has_border = getattr(ann, "has_border", False)
        has_leader = getattr(ann, "has_leader", False)

        if has_border or has_leader:
            b_color_value = QColor(getattr(ann, "border_color", "#ff0000"))
            b_color = (
                b_color_value.red() / 255.0,
                b_color_value.green() / 255.0,
                b_color_value.blue() / 255.0,
            )
            b_width = getattr(ann, "border_width", 2) * ctx.dpi_factor

            font_obj = get_font_object(ctx.page_font)

            num_lines = max(1, len(lines))
            text_w = max(font_obj.text_length(line, fontsize=fontsize) for line in lines) if lines else 0
            text_h = line_height * (num_lines - 1) + fontsize
            margin = 4 * ctx.dpi_factor

            c0 = pos + fitz.Point(-margin, -margin) * ctx.rot_matrix
            c1 = pos + fitz.Point(text_w + margin, -margin) * ctx.rot_matrix
            c2 = pos + fitz.Point(text_w + margin, text_h + margin) * ctx.rot_matrix
            c3 = pos + fitz.Point(-margin, text_h + margin) * ctx.rot_matrix

            if has_border:
                ctx.page.draw_polyline(
                    [c0, c1, c2, c3, c0],
                    color=b_color,
                    width=b_width,
                    stroke_opacity=ctx.stroke_opacity,
                )

            if has_leader and len(ann.points) >= 2:
                p2 = ctx.to_pdf_pt(ann.points[1])
                corners = [c0, c1, c2, c3]
                best_pt = corners[0]
                min_dist = float('inf')
                for pt in corners:
                    dx = pt.x - p2.x
                    dy = pt.y - p2.y
                    dist = dx * dx + dy * dy
                    if dist < min_dist:
                        min_dist = dist
                        best_pt = pt

                ctx.page.draw_line(
                    best_pt,
                    p2,
                    color=b_color,
                    width=b_width,
                    stroke_opacity=ctx.stroke_opacity,
                )
