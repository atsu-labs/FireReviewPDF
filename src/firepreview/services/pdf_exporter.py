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
            "biz udゴシック": (os.path.join(windir, "Fonts", "BIZ-UDGothicR.ttc"), "BIZUDGothic"),
            "biz udgothic": (os.path.join(windir, "Fonts", "BIZ-UDGothicR.ttc"), "BIZUDGothic"),
            "ms gothic": (os.path.join(windir, "Fonts", "msgothic.ttc"), "MSGothic"),
            "ｍｓ ゴシック": (os.path.join(windir, "Fonts", "msgothic.ttc"), "MSGothic"),
            "msgothic": (os.path.join(windir, "Fonts", "msgothic.ttc"), "MSGothic"),
            "meiryo": (os.path.join(windir, "Fonts", "meiryo.ttc"), "Meiryo"),
            "メイリオ": (os.path.join(windir, "Fonts", "meiryo.ttc"), "Meiryo"),
            "yu gothic": (os.path.join(windir, "Fonts", "yugothm.ttc"), "YuGothic"),
            "游ゴシック": (os.path.join(windir, "Fonts", "yugothm.ttc"), "YuGothic"),
            "yugothic": (os.path.join(windir, "Fonts", "yugothm.ttc"), "YuGothic"),
        }

        # 動的にWindowsのレジストリから任意のフォントファミリー名に対応するフォントファイルパスを自動検出します。
        # これにより "Noto Sans JP" や "BIZ UDゴシック" などすべてのシステムフォントをPDFに正しく埋め込むことができます。
        def get_windows_font_path(font_family_name):
            import winreg
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows NT\CurrentVersion\Fonts") as reg_key:
                    num_values = winreg.QueryInfoKey(reg_key)[1]
                    
                    target = font_family_name.lower().strip()
                    
                    # 特殊な日本語フォント名の英語置換マップ
                    replacement_map = {
                        "ゴシック": "gothic",
                        "明朝": "mincho",
                        "メイリオ": "meiryo",
                        "游ゴシック": "yu gothic",
                        "游明朝": "yu mincho"
                    }
                    
                    targets = [target]
                    for jp, en in replacement_map.items():
                        if jp in target:
                            targets.append(target.replace(jp, en))
                            
                    # スペースを排除したバージョンを追加
                    for t in list(targets):
                        no_space = t.replace(" ", "").replace("　", "")
                        if no_space not in targets:
                            targets.append(no_space)
                            
                    # レジストリから検索
                    for i in range(num_values):
                        name, value, _ = winreg.EnumValue(reg_key, i)
                        name_lower = name.lower()
                        
                        matched = False
                        for t in targets:
                            name_no_space = name_lower.replace(" ", "").replace("　", "").replace(";", "")
                            if t in name_no_space:
                                matched = True
                                break
                                
                        if matched:
                            windir = os.environ.get('windir', 'C:/Windows')
                            sys_path = os.path.join(windir, "Fonts", value)
                            if os.path.exists(sys_path):
                                return sys_path
                                
                            user_profile = os.environ.get('USERPROFILE', 'C:/Users/Default')
                            user_path = os.path.join(user_profile, r"AppData/Local/Microsoft/Windows/Fonts", value)
                            if os.path.exists(user_path):
                                return user_path
                                
                            if os.path.exists(value):
                                return os.path.abspath(value)
            except Exception:
                pass
            return None

        # 日本語フォントをロードしてPDFに埋め込み登録します。
        # 保存直前に subset_fonts() を呼び出すことで、PDFサイズ増加をわずか数KB〜数十KBに抑えながら本物の書体出力を実現します。
        def get_or_register_font(page_obj, page_idx, family_name, text_content, ann_type=""):
            if page_idx not in registered_page_fonts:
                registered_page_fonts[page_idx] = {}
                
            family_lower = (family_name or "Arial").lower().strip()
            
            # テキスト内容自体に非アスキー文字（日本語等）が含まれるか
            has_japanese_text = False
            if text_content:
                has_japanese_text = any(char > '\u007f' for char in text_content)
                
            is_legend = (ann_type == "legend")
            
            # 日本語を描画する必要があるか
            need_japanese = has_japanese_text or is_legend or any(x in family_lower for x in ["gothic", "ゴシック", "meiryo", "メイリオ", "yu", "游", "mincho", "明朝", "biz", "noto", "sans", "jp"])
            
            if not need_japanese:
                return "helv"
                
            # 日本語を描画する場合は、指定フォント名に関わらず常に BIZ UDゴシック に完全強制統一します
            pdf_name = "BIZUDGothic"
            
            if pdf_name in registered_page_fonts[page_idx]:
                return registered_page_fonts[page_idx][pdf_name]
                
            # BIZ UDゴシックのフォントパスを検出（英語名・日本語名の両方で最優先探索）
            font_path = get_windows_font_path("BIZ UD Gothic") or get_windows_font_path("BIZ UDゴシック")
            
            # フォールバック処理 (BIZ UDゴシックが見つからなかった場合は MSゴシック -> Meiryo を探索)
            if not font_path:
                for fallback_name in ["MS Gothic", "Meiryo"]:
                    font_path = get_windows_font_path(fallback_name)
                    if font_path:
                        break
                        
            if not font_path:
                # 最終安全フォールバック (システムフォントがどうしても一切ない場合)
                return "helv"
                
            try:
                page_obj.insert_font(fontname=pdf_name, fontfile=font_path)
                registered_page_fonts[page_idx][pdf_name] = pdf_name
                return pdf_name
            except Exception:
                registered_page_fonts[page_idx][pdf_name] = "helv"
                return "helv"
        
        for ann in model.annotations:
            if ann.page_num >= len(export_doc):
                continue

            page = export_doc[ann.page_num]
            
            font_family_str = getattr(ann, "font_family", "Arial")
            page_font = get_or_register_font(page, ann.page_num, font_family_str, ann.text, ann.type)
            
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
                    fontsize = ann.font_size * dpi_factor
                    dy = 4 * dpi_factor + fontsize * 0.85
                    page.insert_text(
                        fitz.Point(mid.x, mid.y + dy),
                        ann.text,
                        color=color,
                        fontsize=fontsize,
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
                    fontsize = ann.font_size * dpi_factor
                    dy = 4 * dpi_factor + fontsize * 0.85
                    page.insert_text(
                        fitz.Point(mid.x, mid.y + dy),
                        ann.text,
                        color=color,
                        fontsize=fontsize,
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
                    fontsize = ann.font_size * dpi_factor
                    dy = 4 * dpi_factor + fontsize * 0.85
                    page.insert_text(
                        (avg_x, avg_y + dy),
                        ann.text,
                        color=color,
                        fontsize=fontsize,
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
                    fontsize = ann.font_size * dpi_factor
                    dy = 4 * dpi_factor + fontsize * 0.85
                    page.insert_text(
                        (center.x + offset_pt.x, center.y - radius - 5 + offset_pt.y + dy),
                        ann.text,
                        color=color,
                        fontsize=fontsize,
                        fontname=page_font,
                        fill_opacity=stroke_opacity,
                    )

            elif ann.type == "arc":
                center = to_pdf_pt(ann.points[0])
                page_scale_factor = model.get_scale_factor(ann.page_num)
                if getattr(ann, "radius_px", 0.0) > 0:
                    radius = ann.radius_px * dpi_factor
                elif ann.real_value > 0 and page_scale_factor > 0:
                    radius = (ann.real_value / page_scale_factor) * dpi_factor
                else:
                    radius = 0
                
                if radius > 0:
                    drag_angle = getattr(ann, "drag_angle", 0.0)
                    arc_span = getattr(ann, "arc_span", 30.0)
                    
                    start_angle_deg = drag_angle - arc_span / 2.0
                    end_angle_deg = drag_angle + arc_span / 2.0
                    
                    num_segments = max(10, int(arc_span / 5.0))
                    segment_points = []
                    for step in range(num_segments + 1):
                        deg = start_angle_deg + (end_angle_deg - start_angle_deg) * step / num_segments
                        rad = math.radians(deg)
                        px = center.x + radius * math.cos(rad)
                        py = center.y + radius * math.sin(rad)
                        segment_points.append(fitz.Point(px, py))
                    
                    for i in range(len(segment_points) - 1):
                        page.draw_line(
                            segment_points[i],
                            segment_points[i + 1],
                            color=color,
                            width=ann.line_width,
                            stroke_opacity=stroke_opacity,
                        )
                        
                    if getattr(ann, "show_radial_line", False):
                        mid_rad = math.radians(drag_angle)
                        mid_pt = fitz.Point(center.x + radius * math.cos(mid_rad),
                                            center.y + radius * math.sin(mid_rad))
                        page.draw_line(
                            center,
                            mid_pt,
                            color=color,
                            width=ann.line_width,
                            stroke_opacity=stroke_opacity,
                        )
                
                if ann.center_marker:
                    draw_center_marker(page, center, ann.center_marker)
                    
                if ann.text:
                    offset = getattr(ann, "label_offset", None) or [0.0, 0.0]
                    offset_pt = fitz.Point(offset[0] * dpi_factor, offset[1] * dpi_factor)
                    mid_rad = math.radians(drag_angle)
                    label_radius = radius + 10 * dpi_factor
                    ref_pos = fitz.Point(center.x + label_radius * math.cos(mid_rad),
                                         center.y + label_radius * math.sin(mid_rad))
                    fontsize = ann.font_size * dpi_factor
                    dy = 4 * dpi_factor + fontsize * 0.85
                    page.insert_text(
                        ref_pos + offset_pt + fitz.Point(0, dy),
                        ann.text,
                        color=color,
                        fontsize=fontsize,
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
                fontsize = ann.font_size * dpi_factor
                dy = 4 * dpi_factor + fontsize * 0.85
                page.insert_text(
                    fitz.Point(pos.x, pos.y + dy),
                    ann.text,
                    color=color,
                    fontsize=fontsize,
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
                    text_w = fitz.get_text_length(ann.text, fontsize=fontsize, fontname=page_font)
                    text_h = fontsize
                    margin = 4 * dpi_factor

                    # Define the border rectangle matching Qt's QGraphicsTextItem bounds (top-left is pos)
                    rect = fitz.Rect(
                        pos.x - margin,
                        pos.y - margin,
                        pos.x + text_w + margin,
                        pos.y + text_h + margin
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
                
                t_fontsize = font_size * 0.9 * dpi_factor
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
                        
                    item_fontsize = font_size * 0.75 * dpi_factor
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

        # フォントをサブセット化して不要な文字グリフを排除し、PDFサイズを劇的に軽量化します（数MBから数KB程度に削減）
        try:
            export_doc.subset_fonts()
        except Exception:
            pass

        export_doc.save(output_path, garbage=4, deflate=True)

    finally:
        if export_doc is not None:
            export_doc.close()
