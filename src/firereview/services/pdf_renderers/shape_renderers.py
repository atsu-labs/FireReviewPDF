import math
import fitz
from .base import BasePdfRenderer, PdfRenderContext


class LinePdfRenderer(BasePdfRenderer):
    """直線注釈のPDFレンダラー"""

    def render(self, ctx: PdfRenderContext, ann) -> None:
        if len(ann.points) < 2:
            return
        p1 = ctx.to_pdf_pt(ann.points[0])
        p2 = ctx.to_pdf_pt(ann.points[1])
        ctx.page.draw_line(
            p1,
            p2,
            color=ctx.color,
            width=ann.line_width,
            stroke_opacity=ctx.stroke_opacity,
        )
        if ann.text:
            offset = getattr(ann, "label_offset", None) or [0.0, 0.0]
            offset_pt = fitz.Point(offset[0] * ctx.dpi_factor, offset[1] * ctx.dpi_factor) * ctx.rot_matrix
            mid = (p1 + p2) / 2 + offset_pt
            fontsize = ann.font_size * ctx.dpi_factor
            dy = ctx.get_baseline_shift(ann.font_size)
            dy_pt = fitz.Point(0, dy) * ctx.rot_matrix
            ctx.page.insert_text(
                mid + dy_pt,
                ann.text,
                color=ctx.color,
                fontsize=fontsize,
                fontname=ctx.page_font,
                fill_opacity=ctx.stroke_opacity,
                rotate=ctx.page_rotation,
            )


class PolylinePdfRenderer(BasePdfRenderer):
    """折れ線・矢印注釈のPDFレンダラー"""

    def render(self, ctx: PdfRenderContext, ann) -> None:
        if not ann.points:
            return
        pts = [ctx.to_pdf_pt(point) for point in ann.points]
        for i in range(len(pts) - 1):
            ctx.page.draw_line(
                pts[i],
                pts[i + 1],
                color=ctx.color,
                width=ann.line_width,
                stroke_opacity=ctx.stroke_opacity,
            )
        if len(pts) >= 2:
            start_marker = getattr(ann, "start_marker", "")
            if start_marker:
                ctx.draw_endpoint_marker(pts[0], pts[1], start_marker)
            end_marker = getattr(ann, "end_marker", "")
            if end_marker:
                ctx.draw_endpoint_marker(pts[-1], pts[-2], end_marker)

        if ann.text and pts:
            offset = getattr(ann, "label_offset", None) or [0.0, 0.0]
            offset_pt = fitz.Point(offset[0] * ctx.dpi_factor, offset[1] * ctx.dpi_factor) * ctx.rot_matrix
            avg_x = sum(pt.x for pt in pts) / len(pts)
            avg_y = sum(pt.y for pt in pts) / len(pts)
            mid = fitz.Point(avg_x, avg_y) + offset_pt
            fontsize = ann.font_size * ctx.dpi_factor
            dy = ctx.get_baseline_shift(ann.font_size)
            dy_pt = fitz.Point(0, dy) * ctx.rot_matrix
            ctx.page.insert_text(
                mid + dy_pt,
                ann.text,
                color=ctx.color,
                fontsize=fontsize,
                fontname=ctx.page_font,
                fill_opacity=ctx.stroke_opacity,
                rotate=ctx.page_rotation,
            )


class PolygonPdfRenderer(BasePdfRenderer):
    """多角形注釈のPDFレンダラー"""

    def render(self, ctx: PdfRenderContext, ann) -> None:
        if not ann.points:
            return
        pts = [ctx.to_pdf_pt(point) for point in ann.points]
        _pdf_fill = ctx.fill_color if ctx.fill_opacity > 0 else None
        ctx.page.draw_polyline(
            pts + [pts[0]],
            color=ctx.color,
            fill=_pdf_fill,
            width=ann.line_width,
            stroke_opacity=ctx.stroke_opacity,
            fill_opacity=ctx.fill_opacity if _pdf_fill else None,
        )
        if ann.text:
            offset = getattr(ann, "label_offset", None) or [0.0, 0.0]
            offset_pt = fitz.Point(offset[0] * ctx.dpi_factor, offset[1] * ctx.dpi_factor) * ctx.rot_matrix
            avg_x = sum(point.x for point in pts) / len(pts) + offset_pt.x
            avg_y = sum(point.y for point in pts) / len(pts) + offset_pt.y
            fontsize = ann.font_size * ctx.dpi_factor
            dy = ctx.get_baseline_shift(ann.font_size)
            dy_pt = fitz.Point(0, dy) * ctx.rot_matrix
            ctx.page.insert_text(
                fitz.Point(avg_x, avg_y) + dy_pt,
                ann.text,
                color=ctx.color,
                fontsize=fontsize,
                fontname=ctx.page_font,
                fill_opacity=ctx.stroke_opacity,
                rotate=ctx.page_rotation,
            )


class CirclePdfRenderer(BasePdfRenderer):
    """円注釈のPDFレンダラー"""

    def render(self, ctx: PdfRenderContext, ann) -> None:
        if not ann.points:
            return
        center = ctx.to_pdf_pt(ann.points[0])
        page_scale_factor = ctx.model.get_scale_factor(ann.page_num)
        radius_px = getattr(ann, "radius_px", 0.0)
        if radius_px > 0:
            radius = radius_px * ctx.dpi_factor
        elif ann.real_value > 0 and page_scale_factor > 0:
            radius = (ann.real_value / page_scale_factor) * ctx.dpi_factor
        else:
            radius = 0

        if radius > 0:
            _pdf_fill = ctx.fill_color if ctx.fill_opacity > 0 else None
            ctx.page.draw_circle(
                center,
                radius,
                color=ctx.color,
                fill=_pdf_fill,
                width=ann.line_width,
                stroke_opacity=ctx.stroke_opacity,
                fill_opacity=ctx.fill_opacity if _pdf_fill else None,
            )

        center_marker = getattr(ann, "center_marker", "")
        if center_marker:
            ctx.draw_center_marker(center, center_marker)

        if ann.text:
            offset = getattr(ann, "label_offset", None) or [0.0, 0.0]
            offset_pt = fitz.Point(offset[0] * ctx.dpi_factor, offset[1] * ctx.dpi_factor) * ctx.rot_matrix
            fontsize = ann.font_size * ctx.dpi_factor
            dy = ctx.get_baseline_shift(ann.font_size)
            dy_pt = fitz.Point(0, dy) * ctx.rot_matrix
            text_rel_pt = fitz.Point(0, -radius - 5 * ctx.dpi_factor) * ctx.rot_matrix
            ctx.page.insert_text(
                center + text_rel_pt + offset_pt + dy_pt,
                ann.text,
                color=ctx.color,
                fontsize=fontsize,
                fontname=ctx.page_font,
                fill_opacity=ctx.stroke_opacity,
                rotate=ctx.page_rotation,
            )


class ArcPdfRenderer(BasePdfRenderer):
    """円弧注釈のPDFレンダラー"""

    def render(self, ctx: PdfRenderContext, ann) -> None:
        if not ann.points:
            return
        center = ctx.to_pdf_pt(ann.points[0])
        page_scale_factor = ctx.model.get_scale_factor(ann.page_num)
        radius_px = getattr(ann, "radius_px", 0.0)
        if radius_px > 0:
            radius = radius_px * ctx.dpi_factor
        elif ann.real_value > 0 and page_scale_factor > 0:
            radius = (ann.real_value / page_scale_factor) * ctx.dpi_factor
        else:
            radius = 0

        drag_angle_pdf = 0.0
        if radius > 0:
            drag_angle = getattr(ann, "drag_angle", 0.0)
            drag_angle_pdf = drag_angle - ctx.page_rotation
            arc_span = getattr(ann, "arc_span", 30.0)

            start_angle_deg = drag_angle_pdf - arc_span / 2.0
            end_angle_deg = drag_angle_pdf + arc_span / 2.0

            num_segments = max(10, int(arc_span / 5.0))
            segment_points = []
            for step in range(num_segments + 1):
                deg = start_angle_deg + (end_angle_deg - start_angle_deg) * step / num_segments
                rad = math.radians(deg)
                px = center.x + radius * math.cos(rad)
                py = center.y + radius * math.sin(rad)
                segment_points.append(fitz.Point(px, py))

            for i in range(len(segment_points) - 1):
                ctx.page.draw_line(
                    segment_points[i],
                    segment_points[i + 1],
                    color=ctx.color,
                    width=ann.line_width,
                    stroke_opacity=ctx.stroke_opacity,
                )

            if getattr(ann, "show_radial_line", False):
                mid_rad = math.radians(drag_angle_pdf)
                mid_pt = fitz.Point(
                    center.x + radius * math.cos(mid_rad),
                    center.y + radius * math.sin(mid_rad)
                )
                ctx.page.draw_line(
                    center,
                    mid_pt,
                    color=ctx.color,
                    width=ann.line_width,
                    stroke_opacity=ctx.stroke_opacity,
                )

        center_marker = getattr(ann, "center_marker", "")
        if center_marker:
            ctx.draw_center_marker(center, center_marker)

        if ann.text and radius > 0:
            offset = getattr(ann, "label_offset", None) or [0.0, 0.0]
            offset_pt = fitz.Point(offset[0] * ctx.dpi_factor, offset[1] * ctx.dpi_factor) * ctx.rot_matrix
            mid_rad = math.radians(drag_angle_pdf)
            label_radius = radius + 10 * ctx.dpi_factor
            ref_pos = fitz.Point(
                center.x + label_radius * math.cos(mid_rad),
                center.y + label_radius * math.sin(mid_rad)
            )
            fontsize = ann.font_size * ctx.dpi_factor
            dy = ctx.get_baseline_shift(ann.font_size)
            dy_pt = fitz.Point(0, dy) * ctx.rot_matrix
            ctx.page.insert_text(
                ref_pos + offset_pt + dy_pt,
                ann.text,
                color=ctx.color,
                fontsize=fontsize,
                fontname=ctx.page_font,
                fill_opacity=ctx.stroke_opacity,
                rotate=ctx.page_rotation,
            )
