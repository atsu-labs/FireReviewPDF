import math

import fitz
from PySide6.QtGui import QColor


def export_pdf_document(model, output_path: str) -> None:
    dpi_factor = 72.0 / 150.0
    export_doc = fitz.open(model.pdf_path)

    try:
        for ann in model.annotations:
            if ann.page_num >= len(export_doc):
                continue

            page = export_doc[ann.page_num]
            color_value = QColor(ann.color)
            color = (
                color_value.red() / 255.0,
                color_value.green() / 255.0,
                color_value.blue() / 255.0,
            )
            fill_opacity = ann.opacity / 100.0

            def to_pdf_pt(qp):
                return fitz.Point(qp.x() * dpi_factor, qp.y() * dpi_factor)

            marker_size = max(ann.line_width * 3, 10 * dpi_factor)

            def draw_endpoint_marker(pdf_page, point, neighbor, marker_type):
                if marker_type == "circle":
                    pdf_page.draw_circle(
                        point,
                        marker_size / 2,
                        color=color,
                        fill=color,
                        width=1,
                        stroke_opacity=fill_opacity,
                        fill_opacity=fill_opacity,
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
                    bx = point.x - dx * marker_size
                    by = point.y - dy * marker_size
                    wing1 = fitz.Point(
                        bx + perp_x * marker_size * 0.45,
                        by + perp_y * marker_size * 0.45,
                    )
                    wing2 = fitz.Point(
                        bx - perp_x * marker_size * 0.45,
                        by - perp_y * marker_size * 0.45,
                    )
                    pdf_page.draw_polyline(
                        [point, wing1, wing2],
                        color=color,
                        fill=color,
                        width=0,
                        closePath=True,
                        stroke_opacity=fill_opacity,
                        fill_opacity=fill_opacity,
                    )

            def draw_center_marker(pdf_page, center, marker_type):
                size = marker_size / 2
                if marker_type == "circle":
                    pdf_page.draw_circle(
                        center,
                        size,
                        color=color,
                        fill=color,
                        width=1,
                        stroke_opacity=fill_opacity,
                        fill_opacity=fill_opacity,
                    )
                elif marker_type == "cross":
                    pdf_page.draw_line(
                        fitz.Point(center.x - size, center.y),
                        fitz.Point(center.x + size, center.y),
                        color=color,
                        width=1.5,
                        stroke_opacity=fill_opacity,
                    )
                    pdf_page.draw_line(
                        fitz.Point(center.x, center.y - size),
                        fitz.Point(center.x, center.y + size),
                        color=color,
                        width=1.5,
                        stroke_opacity=fill_opacity,
                    )
                elif marker_type == "x":
                    pdf_page.draw_line(
                        fitz.Point(center.x - size, center.y - size),
                        fitz.Point(center.x + size, center.y + size),
                        color=color,
                        width=1.5,
                        stroke_opacity=fill_opacity,
                    )
                    pdf_page.draw_line(
                        fitz.Point(center.x + size, center.y - size),
                        fitz.Point(center.x - size, center.y + size),
                        color=color,
                        width=1.5,
                        stroke_opacity=fill_opacity,
                    )

            if ann.type == "line":
                p1 = to_pdf_pt(ann.points[0])
                p2 = to_pdf_pt(ann.points[1])
                page.draw_line(
                    p1,
                    p2,
                    color=color,
                    width=ann.line_width,
                    stroke_opacity=fill_opacity,
                )
                if ann.text:
                    mid = (p1 + p2) / 2
                    page.insert_text(
                        mid,
                        ann.text,
                        color=color,
                        fontsize=ann.font_size,
                        fontname="helv",
                        fill_opacity=fill_opacity,
                    )

            elif ann.type == "polyline":
                pts = [to_pdf_pt(point) for point in ann.points]
                for i in range(len(pts) - 1):
                    page.draw_line(
                        pts[i],
                        pts[i + 1],
                        color=color,
                        width=ann.line_width,
                        stroke_opacity=fill_opacity,
                    )
                if len(pts) >= 2:
                    if ann.start_marker:
                        draw_endpoint_marker(page, pts[0], pts[1], ann.start_marker)
                    if ann.end_marker:
                        draw_endpoint_marker(page, pts[-1], pts[-2], ann.end_marker)
                if ann.text and pts:
                    mid = pts[len(pts) // 2]
                    page.insert_text(
                        mid,
                        ann.text,
                        color=color,
                        fontsize=ann.font_size,
                        fontname="helv",
                        fill_opacity=fill_opacity,
                    )

            elif ann.type == "polygon":
                pts = [to_pdf_pt(point) for point in ann.points]
                page.draw_polyline(
                    pts + [pts[0]],
                    color=color,
                    width=ann.line_width,
                    stroke_opacity=fill_opacity,
                )
                if ann.text:
                    avg_x = sum(point.x for point in pts) / len(pts)
                    avg_y = sum(point.y for point in pts) / len(pts)
                    page.insert_text(
                        (avg_x, avg_y),
                        ann.text,
                        color=color,
                        fontsize=ann.font_size,
                        fontname="helv",
                        fill_opacity=fill_opacity,
                    )

            elif ann.type == "circle":
                center = to_pdf_pt(ann.points[0])
                if ann.radius_px > 0:
                    radius = ann.radius_px * dpi_factor
                elif ann.real_value > 0 and model.scale_factor > 0:
                    radius = (ann.real_value / model.scale_factor) * dpi_factor
                else:
                    radius = 0
                if radius > 0:
                    page.draw_circle(
                        center,
                        radius,
                        color=color,
                        width=ann.line_width,
                        stroke_opacity=fill_opacity,
                    )
                if ann.center_marker:
                    draw_center_marker(page, center, ann.center_marker)
                if ann.text:
                    page.insert_text(
                        (center.x, center.y - radius - 5),
                        ann.text,
                        color=color,
                        fontsize=ann.font_size,
                        fontname="helv",
                        fill_opacity=fill_opacity,
                    )

            elif ann.type == "text":
                pos = to_pdf_pt(ann.points[0])
                page.insert_text(
                    pos,
                    ann.text,
                    color=color,
                    fontsize=ann.font_size,
                    fontname="helv",
                    fill_opacity=fill_opacity,
                )

        export_doc.save(output_path)
    finally:
        export_doc.close()
