import fitz
from PySide6.QtGui import QColor
from .base import BasePdfRenderer, PdfRenderContext


class LegendPdfRenderer(BasePdfRenderer):
    """凡例注釈のPDFレンダラー"""

    def render(self, ctx: PdfRenderContext, ann) -> None:
        if not ann.points:
            return

        pos = ctx.to_pdf_pt(ann.points[0])

        # 1. 現在ページのマーカーを集計
        marker_counts = {}
        for other in ctx.model.annotations:
            if other.page_num == ann.page_num and other.type == 'marker':
                style = getattr(other, 'marker_style', 'square')
                color_hex = (other.color or "#7c4dff").lower()
                key = (style, color_hex)
                marker_counts[key] = marker_counts.get(key, 0) + 1

        items = sorted(marker_counts.items(), key=lambda x: x[1], reverse=True)

        # ページごとのカスタム色名を取得
        page_names = ctx.model.page_color_names.get(ann.page_num, {})

        # 動的スケーリングパラメータ
        font_size = getattr(ann, "font_size", 12)
        scale = font_size / 12.0

        # 2. PDFポイント単位での寸法計算
        row_h = max(20.0, 30.0 * scale) * ctx.dpi_factor
        title_h = max(24.0, 32.0 * scale) * ctx.dpi_factor
        w = max(150.0, 200.0 * scale) * ctx.dpi_factor
        h = title_h + max(1, len(items)) * row_h + 10 * ctx.dpi_factor * scale

        card_c0 = pos
        card_c1 = pos + fitz.Point(w, 0) * ctx.rot_matrix
        card_c2 = pos + fitz.Point(w, h) * ctx.rot_matrix
        card_c3 = pos + fitz.Point(0, h) * ctx.rot_matrix

        # カード外枠と背景の描画
        ctx.page.draw_polyline(
            [card_c0, card_c1, card_c2, card_c3, card_c0],
            color=(204/255.0, 204/255.0, 204/255.0),
            fill=(245/255.0, 246/255.0, 248/255.0),
            width=1.2 * ctx.dpi_factor,
            stroke_opacity=1.0,
            fill_opacity=0.95,
        )

        # 4. タイトルの描画
        t_color = QColor(ann.color or "#7c4dff")
        t_rgb = (t_color.red() / 255.0, t_color.green() / 255.0, t_color.blue() / 255.0)

        t_fontsize = font_size * 0.9 * ctx.dpi_factor
        title_baseline_y = title_h / 2.0 + (t_fontsize * 0.35)
        title_pos = pos + fitz.Point(15 * ctx.dpi_factor * scale, title_baseline_y) * ctx.rot_matrix

        ctx.page.insert_text(
            title_pos,
            "凡例" if ctx.page_font != "helv" else "Legend",
            color=t_rgb,
            fontsize=t_fontsize,
            fontname=ctx.page_font,
            fill_opacity=1.0,
            rotate=ctx.page_rotation,
        )

        # セパレータ線
        line_p1 = pos + fitz.Point(15 * ctx.dpi_factor * scale, title_h - 4 * ctx.dpi_factor * scale) * ctx.rot_matrix
        line_p2 = pos + fitz.Point(w - 15 * ctx.dpi_factor * scale, title_h - 4 * ctx.dpi_factor * scale) * ctx.rot_matrix
        ctx.page.draw_line(
            line_p1,
            line_p2,
            color=(220/255.0, 221/255.0, 225/255.0),
            width=1 * ctx.dpi_factor * scale,
            stroke_opacity=1.0,
        )

        # 5. 各アイテムの描画
        y_offset = title_h
        default_color_names = {
            "#ff1744": "赤", "#2979ff": "青", "#00e676": "緑", "#ffd600": "黄",
            "#ff9100": "橙", "#f50057": "桃", "#d500f9": "紫", "#8d6e63": "茶",
            "#00e5ff": "水色", "#aeea00": "黄緑", "#7c4dff": "紫"
        }

        for (style, col), count in items:
            c_val = QColor(col)
            c_rgb = (c_val.red() / 255.0, c_val.green() / 255.0, c_val.blue() / 255.0)
            icon_center = pos + fitz.Point(25 * ctx.dpi_factor * scale, y_offset + row_h / 2.0) * ctx.rot_matrix
            half_sz = 11 * ctx.dpi_factor * scale

            if style == "square":
                square_half = 10 * ctx.dpi_factor * scale
                ic0 = icon_center + fitz.Point(-square_half, -square_half) * ctx.rot_matrix
                ic1 = icon_center + fitz.Point(square_half, -square_half) * ctx.rot_matrix
                ic2 = icon_center + fitz.Point(square_half, square_half) * ctx.rot_matrix
                ic3 = icon_center + fitz.Point(-square_half, square_half) * ctx.rot_matrix

                ctx.page.draw_polyline(
                    [ic0, ic1, ic2, ic3, ic0],
                    color=(1.0, 1.0, 1.0),
                    fill=c_rgb,
                    width=2 * ctx.dpi_factor * scale,
                    stroke_opacity=1.0,
                    fill_opacity=1.0,
                )
                ctx.page.draw_polyline(
                    [ic0, ic1, ic2, ic3, ic0],
                    color=c_rgb,
                    width=1.5 * ctx.dpi_factor * scale,
                    stroke_opacity=1.0,
                )
            elif style == "check":
                ctx.page.draw_circle(
                    icon_center,
                    half_sz,
                    color=c_rgb,
                    fill=(1.0, 1.0, 1.0),
                    width=1.5 * ctx.dpi_factor * scale,
                    stroke_opacity=1.0,
                    fill_opacity=1.0,
                )
                p_start = icon_center + fitz.Point(-6 * ctx.dpi_factor * scale, 0) * ctx.rot_matrix
                p_mid = icon_center + fitz.Point(-1.5 * ctx.dpi_factor * scale, 4.5 * ctx.dpi_factor * scale) * ctx.rot_matrix
                p_end = icon_center + fitz.Point(6 * ctx.dpi_factor * scale, -3 * ctx.dpi_factor * scale) * ctx.rot_matrix
                ctx.page.draw_polyline(
                    [p_start, p_mid, p_end],
                    color=c_rgb,
                    width=2.5 * ctx.dpi_factor * scale,
                    stroke_opacity=1.0,
                    closePath=False,
                )

            # 色名ラベル
            c_name = page_names.get(col.lower(), default_color_names.get(col.lower(), col.upper()))

            if ctx.page_font == "helv":
                c_name_en = {
                    "赤": "Red", "青": "Blue", "緑": "Green", "黄": "Yellow",
                    "橙": "Orange", "桃": "Pink", "紫": "Purple", "茶": "Brown",
                    "水色": "LightBlue", "黄緑": "LightGreen"
                }.get(c_name, c_name)
                c_name = "".join([char for char in c_name_en if ord(char) < 128])

            if len(c_name) > 12:
                c_name = c_name[:10] + "..."

            item_fontsize = font_size * 0.75 * ctx.dpi_factor
            item_baseline_y = y_offset + row_h / 2.0 + (item_fontsize * 0.35)

            text_pos = pos + fitz.Point(48 * ctx.dpi_factor * scale, item_baseline_y) * ctx.rot_matrix
            ctx.page.insert_text(
                text_pos,
                c_name,
                color=(42/255.0, 42/255.0, 61/255.0),
                fontsize=item_fontsize,
                fontname=ctx.page_font,
                fill_opacity=1.0,
                rotate=ctx.page_rotation,
            )

            # カウント数
            count_text = str(count)
            count_pos = pos + fitz.Point((w / ctx.dpi_factor - 45 * scale) * ctx.dpi_factor, item_baseline_y) * ctx.rot_matrix
            ctx.page.insert_text(
                count_pos,
                count_text,
                color=(46/255.0, 125/255.0, 50/255.0),
                fontsize=item_fontsize,
                fontname=ctx.page_font,
                fill_opacity=1.0,
                rotate=ctx.page_rotation,
            )

            y_offset += row_h
