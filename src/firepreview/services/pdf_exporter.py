import math
import os
import fitz
from PySide6.QtGui import QColor


def export_pdf_document(model, output_path: str) -> None:
    dpi_factor = 72.0 / 150.0
    export_doc = None

    try:
        export_doc = fitz.open(model.pdf_path)
        
        # Track registered fonts per page to avoid redundant inserts
        # {page_num: {font_name_in_pdf: True}}
        registered_page_fonts = {}
        
        # Windows system font file and registration name mapping
        windir = os.environ.get('windir', 'C:/Windows')
        FONT_MAP = {
            "ms gothic": (os.path.join(windir, "Fonts", "msgothic.ttc"), "msgothic"),
            "ｍｓ ゴシック": (os.path.join(windir, "Fonts", "msgothic.ttc"), "msgothic"),
            "msgothic": (os.path.join(windir, "Fonts", "msgothic.ttc"), "msgothic"),
            
            "meiryo": (os.path.join(windir, "Fonts", "meiryo.ttc"), "meiryo"),
            "メイリオ": (os.path.join(windir, "Fonts", "meiryo.ttc"), "meiryo"),
            
            "yu gothic": (os.path.join(windir, "Fonts", "yugothm.ttc"), "yugothic"),
            "游ゴシック": (os.path.join(windir, "Fonts", "yugothm.ttc"), "yugothic"),
            "yugothic": (os.path.join(windir, "Fonts", "yugothm.ttc"), "yugothic"),
        }

        def get_or_register_font(page_obj, page_idx, family_name):
            if page_idx not in registered_page_fonts:
                registered_page_fonts[page_idx] = {}
                
            family_lower = (family_name or "Arial").lower().strip()
            
            # 1. Yu Gothic / Yu Mincho / 游ゴシック (游)
            if "yu" in family_lower or "游" in family_lower or "yugoth" in family_lower:
                font_path, pdf_name = os.path.join(windir, "Fonts", "yugothm.ttc"), "yugothic"
                if pdf_name in registered_page_fonts[page_idx]:
                    return pdf_name
                if os.path.exists(font_path):
                    try:
                        page_obj.insert_font(fontname=pdf_name, fontfile=font_path)
                        registered_page_fonts[page_idx][pdf_name] = True
                        return pdf_name
                    except Exception:
                        pass

            # 2. Meiryo / Meiryo UI / メイリオ
            if "meiryo" in family_lower or "メイリオ" in family_lower:
                font_path, pdf_name = os.path.join(windir, "Fonts", "meiryo.ttc"), "meiryo"
                if pdf_name in registered_page_fonts[page_idx]:
                    return pdf_name
                if os.path.exists(font_path):
                    try:
                        page_obj.insert_font(fontname=pdf_name, fontfile=font_path)
                        registered_page_fonts[page_idx][pdf_name] = True
                        return pdf_name
                    except Exception:
                        pass

            # 3. MS Gothic / MS UI Gothic / MS PGothic / ゴシック
            if "gothic" in family_lower or "ゴシック" in family_lower or "msgoth" in family_lower:
                font_path, pdf_name = os.path.join(windir, "Fonts", "msgothic.ttc"), "msgothic"
                if pdf_name in registered_page_fonts[page_idx]:
                    return pdf_name
                if os.path.exists(font_path):
                    try:
                        page_obj.insert_font(fontname=pdf_name, fontfile=font_path)
                        registered_page_fonts[page_idx][pdf_name] = True
                        return pdf_name
                    except Exception:
                        pass

            # 4. Exact FONT_MAP direct lookup
            if family_lower in FONT_MAP:
                font_path, pdf_name = FONT_MAP[family_lower]
                if pdf_name in registered_page_fonts[page_idx]:
                    return pdf_name
                if os.path.exists(font_path):
                    try:
                        page_obj.insert_font(fontname=pdf_name, fontfile=font_path)
                        registered_page_fonts[page_idx][pdf_name] = True
                        return pdf_name
                    except Exception:
                        pass

            # 5. Fallback - Japanese priority font (Meiryo first, msgothic second) to avoid CJK rendering crash
            for path, name in [
                (os.path.join(windir, "Fonts", "meiryo.ttc"), "meiryo"),
                (os.path.join(windir, "Fonts", "msgothic.ttc"), "msgothic"),
                (os.path.join(windir, "Fonts", "yugothm.ttc"), "yugothic")
            ]:
                if os.path.exists(path):
                    if name in registered_page_fonts[page_idx]:
                        return name
                    try:
                        page_obj.insert_font(fontname=name, fontfile=path)
                        registered_page_fonts[page_idx][name] = True
                        return name
                    except Exception:
                        pass
                        
            return "helv"
        
        for ann in model.annotations:
            if ann.page_num >= len(export_doc):
                continue

            page = export_doc[ann.page_num]
            
            font_family_str = getattr(ann, "font_family", "Arial")
            page_font = get_or_register_font(page, ann.page_num, font_family_str)
            
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
                    offset = getattr(ann, "label_offset", None) or [0.0, 0.0]
                    offset_pt = fitz.Point(offset[0] * dpi_factor, offset[1] * dpi_factor)
                    mid = (p1 + p2) / 2 + offset_pt
                    page.insert_text(
                        mid,
                        ann.text,
                        color=color,
                        fontsize=ann.font_size,
                        fontname=page_font,
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
                    offset = getattr(ann, "label_offset", None) or [0.0, 0.0]
                    offset_pt = fitz.Point(offset[0] * dpi_factor, offset[1] * dpi_factor)
                    avg_x = sum(pt.x for pt in pts) / len(pts)
                    avg_y = sum(pt.y for pt in pts) / len(pts)
                    mid = fitz.Point(avg_x, avg_y) + offset_pt
                    page.insert_text(
                        mid,
                        ann.text,
                        color=color,
                        fontsize=ann.font_size,
                        fontname=page_font,
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
                    offset = getattr(ann, "label_offset", None) or [0.0, 0.0]
                    offset_pt = fitz.Point(offset[0] * dpi_factor, offset[1] * dpi_factor)
                    avg_x = sum(point.x for point in pts) / len(pts) + offset_pt.x
                    avg_y = sum(point.y for point in pts) / len(pts) + offset_pt.y
                    page.insert_text(
                        (avg_x, avg_y),
                        ann.text,
                        color=color,
                        fontsize=ann.font_size,
                        fontname=page_font,
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
                    offset = getattr(ann, "label_offset", None) or [0.0, 0.0]
                    offset_pt = fitz.Point(offset[0] * dpi_factor, offset[1] * dpi_factor)
                    page.insert_text(
                        (center.x + offset_pt.x, center.y - radius - 5 + offset_pt.y),
                        ann.text,
                        color=color,
                        fontsize=ann.font_size,
                        fontname=page_font,
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
                        closePath=False,
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
                    fontname=page_font,
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
                    text_w = fitz.get_text_length(ann.text, fontsize=ann.font_size, fontname=page_font)
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

            elif ann.type == "legend":
                if not ann.points:
                    continue
                pos = to_pdf_pt(ann.points[0])
                
                # 1. Count markers on the current page
                marker_counts = {}
                for other in model.annotations:
                    if other.page_num == ann.page_num and other.type == 'marker':
                        style = getattr(other, 'marker_style', 'square')
                        color_hex = (other.color or "#7c4dff").lower()
                        key = (style, color_hex)
                        marker_counts[key] = marker_counts.get(key, 0) + 1
                        
                items = sorted(marker_counts.items(), key=lambda x: x[1], reverse=True)
                
                # Fetch custom color names for current page
                page_names = model.page_color_names.get(ann.page_num, {})
                
                # Dynamic scaling parameters
                font_size = getattr(ann, "font_size", 12)
                scale = font_size / 12.0
                
                # 2. Dimensions in PDF points
                row_h = max(20.0, 30.0 * scale) * dpi_factor
                title_h = max(24.0, 32.0 * scale) * dpi_factor
                w = max(150.0, 200.0 * scale) * dpi_factor
                h = title_h + max(1, len(items)) * row_h + 10 * dpi_factor * scale
                
                rect = fitz.Rect(pos.x, pos.y, pos.x + w, pos.y + h)
                
                # 3. Draw Background Card
                page.draw_rect(
                    rect,
                    color=(204/255.0, 204/255.0, 204/255.0),
                    fill=(245/255.0, 246/255.0, 248/255.0),
                    width=1.2 * dpi_factor,
                    stroke_opacity=1.0,
                    fill_opacity=0.95,
                )
                
                # 4. Draw Title: "凡例" (Dynamic ann.color or Brand deep purple: #7c4dff)
                t_color = QColor(ann.color or "#7c4dff")
                t_rgb = (t_color.red() / 255.0, t_color.green() / 255.0, t_color.blue() / 255.0)
                
                t_fontsize = font_size * 0.9
                # Calculate precise baseline for centering within title_h
                title_baseline_y = pos.y + title_h / 2.0 + (t_fontsize * 0.35)
                title_pos = fitz.Point(pos.x + 15 * dpi_factor * scale, title_baseline_y)
                
                page.insert_text(
                    title_pos,
                    "凡例" if page_font != "helv" else "Legend",
                    color=t_rgb,
                    fontsize=t_fontsize,
                    fontname=page_font,
                    fill_opacity=1.0,
                )
                
                # Separator Line
                page.draw_line(
                    fitz.Point(pos.x + 15 * dpi_factor * scale, pos.y + (title_h - 4 * scale) * dpi_factor),
                    fitz.Point(pos.x + (w / dpi_factor - 15 * scale) * dpi_factor, pos.y + (title_h - 4 * scale) * dpi_factor),
                    color=(220/255.0, 221/255.0, 225/255.0),
                    width=1 * dpi_factor * scale,
                    stroke_opacity=1.0,
                )
                
                # 5. Loop and draw items
                y_offset = pos.y + title_h
                default_color_names = {
                    "#ff1744": "赤", "#2979ff": "青", "#00e676": "緑", "#ffd600": "黄", 
                    "#ff9100": "橙", "#f50057": "桃", "#d500f9": "紫", "#8d6e63": "茶", 
                    "#00e5ff": "水色", "#aeea00": "黄緑", "#7c4dff": "紫"
                }
                
                for (style, col), count in items:
                    # A. Draw marker icon
                    c_val = QColor(col)
                    c_rgb = (c_val.red() / 255.0, c_val.green() / 255.0, c_val.blue() / 255.0)
                    icon_center = fitz.Point(pos.x + 25 * dpi_factor * scale, y_offset + row_h / 2.0)
                    half_sz = 11 * dpi_factor * scale
                    
                    if style == "square":
                        square_half = 10 * dpi_factor * scale
                        rect_icon = fitz.Rect(
                            icon_center.x - square_half,
                            icon_center.y - square_half,
                            icon_center.x + square_half,
                            icon_center.y + square_half
                        )
                        # White border glow
                        page.draw_rect(
                            rect_icon,
                            color=(1.0, 1.0, 1.0),
                            fill=c_rgb,
                            width=2 * dpi_factor * scale,
                            stroke_opacity=1.0,
                            fill_opacity=1.0,
                        )
                        # Main color border
                        page.draw_rect(
                            rect_icon,
                            color=c_rgb,
                            width=1.5 * dpi_factor * scale,
                            stroke_opacity=1.0,
                        )
                    elif style == "check":
                        # White background disk
                        page.draw_circle(
                            icon_center,
                            half_sz,
                            color=c_rgb,
                            fill=(1.0, 1.0, 1.0),
                            width=1.5 * dpi_factor * scale,
                            stroke_opacity=1.0,
                            fill_opacity=1.0,
                        )
                        # Checkmark path
                        p_start = fitz.Point(icon_center.x - 6 * dpi_factor * scale, icon_center.y)
                        p_mid = fitz.Point(icon_center.x - 1.5 * dpi_factor * scale, icon_center.y + 4.5 * dpi_factor * scale)
                        p_end = fitz.Point(icon_center.x + 6 * dpi_factor * scale, icon_center.y - 3 * dpi_factor * scale)
                        page.draw_polyline(
                            [p_start, p_mid, p_end],
                            color=c_rgb,
                            width=2.5 * dpi_factor * scale,
                            stroke_opacity=1.0,
                            closePath=False,
                        )
                        
                    # B. Color name (Japanese supported with page_font CJK)
                    c_name = page_names.get(col.lower(), default_color_names.get(col.lower(), col.upper()))
                    
                    # Fallback to English translation if no CJK font exists to prevent crashes
                    if page_font == "helv":
                        c_name_en = {
                            "赤": "Red", "青": "Blue", "緑": "Green", "黄": "Yellow", 
                            "橙": "Orange", "桃": "Pink", "紫": "Purple", "茶": "Brown", 
                            "水色": "LightBlue", "黄緑": "LightGreen"
                        }.get(c_name, c_name)
                        c_name = "".join([char for char in c_name_en if ord(char) < 128])
                        
                    if len(c_name) > 12:
                        c_name = c_name[:10] + "..."
                        
                    item_fontsize = font_size * 0.75
                    # Calculate precise baseline for centering within row_h
                    item_baseline_y = y_offset + row_h / 2.0 + (item_fontsize * 0.35)
                    
                    text_pos = fitz.Point(pos.x + 48 * dpi_factor * scale, item_baseline_y)
                    page.insert_text(
                        text_pos,
                        c_name,
                        color=(42/255.0, 42/255.0, 61/255.0),
                        fontsize=item_fontsize,
                        fontname=page_font,
                        fill_opacity=1.0,
                    )
                    
                    # C. Count
                    count_text = str(count)
                    count_pos = fitz.Point(pos.x + (w / dpi_factor - 45 * scale) * dpi_factor, item_baseline_y)
                    page.insert_text(
                        count_pos,
                        count_text,
                        color=(46/255.0, 125/255.0, 50/255.0),
                        fontsize=item_fontsize,
                        fontname=page_font,
                        fill_opacity=1.0,
                    )
                    
                    y_offset += row_h

        export_doc.save(output_path)

    finally:
        if export_doc is not None:
            export_doc.close()
