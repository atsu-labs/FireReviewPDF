import math

import fitz
from PySide6.QtGui import QColor


def export_pdf_document(model, output_path: str) -> None:
    dpi_factor = 72.0 / 150.0
    export_doc = None

    try:
        export_doc = fitz.open(model.pdf_path)
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
            fill_opacity = ann.fill_opacity / 100.0
            stroke_opacity = ann.stroke_opacity / 100.0

            fill_color_value = QColor(ann.fill_color) if ann.fill_color else color_value
            pdf_fill_color = (
                fill_color_value.red() / 255.0,
                fill_color_value.green() / 255.0,
                fill_color_value.blue() / 255.0,
            )

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
                        stroke_opacity=stroke_opacity,
                        fill_opacity=stroke_opacity,
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
                        stroke_opacity=stroke_opacity,
                        fill_opacity=stroke_opacity,
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
                        stroke_opacity=stroke_opacity,
                        fill_opacity=stroke_opacity,
                    )
                elif marker_type == "cross":
                    pdf_page.draw_line(
                        fitz.Point(center.x - size, center.y),
                        fitz.Point(center.x + size, center.y),
                        color=color,
                        width=1.5,
                        stroke_opacity=stroke_opacity,
                    )
                    pdf_page.draw_line(
                        fitz.Point(center.x, center.y - size),
                        fitz.Point(center.x, center.y + size),
                        color=color,
                        width=1.5,
                        stroke_opacity=stroke_opacity,
                    )
                elif marker_type == "x":
                    pdf_page.draw_line(
                        fitz.Point(center.x - size, center.y - size),
                        fitz.Point(center.x + size, center.y + size),
                        color=color,
                        width=1.5,
                        stroke_opacity=stroke_opacity,
                    )
                    pdf_page.draw_line(
                        fitz.Point(center.x + size, center.y - size),
                        fitz.Point(center.x - size, center.y + size),
                        color=color,
                        width=1.5,
                        stroke_opacity=stroke_opacity,
                    )

            if ann.type == "line":
                p1 = to_pdf_pt(ann.points[0])
                p2 = to_pdf_pt(ann.points[1])
                page.draw_line(
                    p1,
                    p2,
                    color=color,
                    width=ann.line_width,
                    stroke_opacity=stroke_opacity,
                )
                if ann.text:
                    mid = (p1 + p2) / 2
                    page.insert_text(
                        mid,
                        ann.text,
                        color=color,
                        fontsize=ann.font_size,
                        fontname="helv",
                        fill_opacity=stroke_opacity,
                    )

            elif ann.type == "polyline":
                pts = [to_pdf_pt(point) for point in ann.points]
                for i in range(len(pts) - 1):
                    page.draw_line(
                        pts[i],
                        pts[i + 1],
                        color=color,
                        width=ann.line_width,
                        stroke_opacity=stroke_opacity,
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
                        fill_opacity=stroke_opacity,
                    )

            elif ann.type == "polygon":
                pts = [to_pdf_pt(point) for point in ann.points]
                _pdf_fill = pdf_fill_color if fill_opacity > 0 else None
                page.draw_polyline(
                    pts + [pts[0]],
                    color=color,
                    fill=_pdf_fill,
                    width=ann.line_width,
                    stroke_opacity=stroke_opacity,
                    fill_opacity=fill_opacity if _pdf_fill else None,
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
                        fill_opacity=stroke_opacity,
                    )

            elif ann.type == "circle":
                center = to_pdf_pt(ann.points[0])
                page_scale_factor = model.get_scale_factor(ann.page_num)
                if ann.radius_px > 0:
                    radius = ann.radius_px * dpi_factor
                elif ann.real_value > 0 and page_scale_factor > 0:
                    radius = (ann.real_value / page_scale_factor) * dpi_factor
                else:
                    radius = 0
                if radius > 0:
                    _pdf_fill = pdf_fill_color if fill_opacity > 0 else None
                    page.draw_circle(
                        center,
                        radius,
                        color=color,
                        fill=_pdf_fill,
                        width=ann.line_width,
                        stroke_opacity=stroke_opacity,
                        fill_opacity=fill_opacity if _pdf_fill else None,
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
                        fill_opacity=stroke_opacity,
                    )

            elif ann.type == "marker":
                if not ann.points:
                    continue
                pos = to_pdf_pt(ann.points[0])
                size = 24 * dpi_factor
                half = size / 2
                marker_style = getattr(ann, "marker_style", "square")
                
                if marker_style == "square":
                    rect = fitz.Rect(pos.x - half, pos.y - half, pos.x + half, pos.y + half)
                    # 1. White border glow
                    page.draw_rect(
                        rect,
                        color=(1.0, 1.0, 1.0),
                        fill=color,
                        width=2 * dpi_factor,
                        stroke_opacity=stroke_opacity,
                        fill_opacity=stroke_opacity,
                    )
                    # 2. Main color border
                    page.draw_rect(
                        rect,
                        color=color,
                        width=1.5 * dpi_factor,
                        stroke_opacity=stroke_opacity,
                    )
                elif marker_style == "check":
                    # 1. White background disk
                    page.draw_circle(
                        pos,
                        half,
                        color=color,
                        fill=(1.0, 1.0, 1.0),
                        width=1.5 * dpi_factor,
                        stroke_opacity=stroke_opacity,
                        fill_opacity=stroke_opacity,
                    )
                    # 2. Checkmark path
                    p_start = fitz.Point(pos.x - 6 * dpi_factor, pos.y)
                    p_mid = fitz.Point(pos.x - 1.5 * dpi_factor, pos.y + 4.5 * dpi_factor)
                    p_end = fitz.Point(pos.x + 6 * dpi_factor, pos.y - 3 * dpi_factor)
                    page.draw_polyline(
                        [p_start, p_mid, p_end],
                        color=color,
                        width=2.5 * dpi_factor,
                        stroke_opacity=stroke_opacity,
                    )

            elif ann.type == "text":
                if not ann.points:
                    continue
                pos = to_pdf_pt(ann.points[0])
                page.insert_text(
                    pos,
                    ann.text,
                    color=color,
                    fontsize=ann.font_size,
                    fontname="helv",
                    fill_opacity=stroke_opacity,
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
                    b_width = getattr(ann, "border_width", 2) * dpi_factor

                    # Calculate precise text bounding box
                    text_w = fitz.get_text_length(ann.text, fontsize=ann.font_size, fontname="helv")
                    text_h = ann.font_size
                    margin = 4 * dpi_factor

                    # Define the border rectangle (insert_text starts at bottom-left)
                    rect = fitz.Rect(
                        pos.x - margin,
                        pos.y - text_h - margin,
                        pos.x + text_w + margin,
                        pos.y + margin
                    )

                    if has_border:
                        page.draw_rect(
                            rect,
                            color=b_color,
                            width=b_width,
                            stroke_opacity=stroke_opacity
                        )

                    if has_leader and len(ann.points) >= 2:
                        p2 = to_pdf_pt(ann.points[1])
                        # Check all 4 corners
                        corners = [
                            fitz.Point(rect.x0, rect.y0),  # Top-left
                            fitz.Point(rect.x1, rect.y0),  # Top-right
                            fitz.Point(rect.x0, rect.y1),  # Bottom-left
                            fitz.Point(rect.x1, rect.y1)   # Bottom-right
                        ]
                        # Find closest corner to the end point
                        best_pt = corners[0]
                        min_dist = float('inf')
                        for pt in corners:
                            dx = pt.x - p2.x
                            dy = pt.y - p2.y
                            dist = dx * dx + dy * dy
                            if dist < min_dist:
                                min_dist = dist
                                best_pt = pt

                        page.draw_line(
                            best_pt,
                            p2,
                            color=b_color,
                            width=b_width,
                            stroke_opacity=stroke_opacity
                        )

        export_doc.save(output_path)
    finally:
        if export_doc is not None:
            export_doc.close()
