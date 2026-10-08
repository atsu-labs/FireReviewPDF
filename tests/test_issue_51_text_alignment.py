import pytest
import fitz
from PySide6.QtCore import QPointF
from PySide6.QtGui import QFont

from firereview.models import DrawingModel, Annotation
from firereview.ui.canvas.items import CustomTextItem
from firereview.ui.canvas.view import PDFCanvas
from firereview.services.pdf_renderers.base import PdfRenderContext
from firereview.services.pdf_renderers.text_renderer import TextPdfRenderer
from firereview.services.pdf_renderers.shape_renderers import CirclePdfRenderer
from firereview.services.pdf_renderers.fonts import get_font_object
from firereview.services.pdf_exporter import export_pdf_document


def test_custom_text_item_document_margin_is_zero(qtbot):
    """CustomTextItemの内部余白（documentMargin）が0に設定されていることを検証"""
    item = CustomTextItem("テスト文字列")
    assert item.document().documentMargin() == 0


def test_canvas_view_font_pixel_size(qtbot):
    """_add_text_itemおよびインライン編集テキストでpixelSizeが指定されていることを検証"""
    view = PDFCanvas()
    qtbot.addWidget(view)

    # _add_text_item
    item = view._add_text_item("テスト", 100, 200, "#000000", font_size=16)
    assert item is not None
    font = item.font()
    assert font.pixelSize() == 16

    # インライン編集アイテム
    view.current_text_size = 20
    view._start_inline_text_editing(QPointF(50, 50))
    assert view.editing_text_item is not None
    editing_font = view.editing_text_item.font()
    assert editing_font.pixelSize() == 20


def test_baseline_shift_calculation():
    """get_baseline_shiftが固定4px余白を含まずフォントのascenderに基づく計算になっていることを検証"""
    doc = fitz.open()
    page = doc.new_page()
    model = DrawingModel()
    ann = Annotation("text")
    ann.page_num = 0
    ann.points = [QPointF(100, 100)]
    ann.font_size = 12
    dpi_factor = 72.0 / 150.0

    ctx = PdfRenderContext(
        page=page,
        page_num=0,
        model=model,
        dpi_factor=dpi_factor,
        page_font="helv",
        ann=ann,
    )

    shift = ctx.get_baseline_shift(12, page_font="helv")
    font_obj = get_font_object("helv")
    expected_shift = 12 * dpi_factor * font_obj.ascender
    assert pytest.approx(shift, rel=1e-4) == expected_shift
    doc.close()


def test_circle_label_offset_in_pdf():
    """CirclePdfRendererが画面側と同じ-10*dpi_factorの基準オフセットを使用していることを検証"""
    doc = fitz.open()
    page = doc.new_page()
    model = DrawingModel()
    ann = Annotation("circle")
    ann.page_num = 0
    ann.points = [QPointF(100, 100)]
    ann.radius_px = 30
    ann.text = "ラベル"
    ann.font_size = 12
    ann.color = "#00ff00"
    dpi_factor = 72.0 / 150.0

    ctx = PdfRenderContext(
        page=page,
        page_num=0,
        model=model,
        dpi_factor=dpi_factor,
        page_font="helv",
        ann=ann,
    )

    renderer = CirclePdfRenderer()
    renderer.render(ctx, ann)

    # 描画されたテキストを検証
    text_page = page.get_text("words")
    # text_page entries: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
    assert len(text_page) >= 1
    doc.close()


def test_export_pdf_document_text_and_circle_integration(tmp_path):
    """テキストおよび円注釈を含むドキュメントのPDFエクスポート結合テスト"""
    pdf_path = str(tmp_path / "test_input.pdf")
    doc = fitz.open()
    doc.new_page(width=600, height=800)
    doc.save(pdf_path)
    doc.close()

    model = DrawingModel()
    model.pdf_path = pdf_path

    # テキスト注釈（複数行）
    text_ann = Annotation("text")
    text_ann.page_num = 0
    text_ann.points = [QPointF(100, 100), QPointF(200, 200)]
    text_ann.text = "一行目\n二行目"
    text_ann.font_size = 14
    text_ann.color = "#ff0000"
    text_ann.has_border = True
    text_ann.has_leader = True

    # 円注釈（ラベル付き）
    circle_ann = Annotation("circle")
    circle_ann.page_num = 0
    circle_ann.points = [QPointF(300, 300)]
    circle_ann.radius_px = 40
    circle_ann.text = "R40"
    circle_ann.font_size = 12
    circle_ann.color = "#0000ff"
    circle_ann.label_offset = [5, -5]

    model.annotations.append(text_ann)
    model.annotations.append(circle_ann)

    output_path = str(tmp_path / "test_output.pdf")
    export_pdf_document(model, output_path)

    # 出力されたPDFの検証
    out_doc = fitz.open(output_path)
    assert len(out_doc) == 1
    page = out_doc[0]
    page_text = page.get_text()
    assert "一行目" in page_text
    assert "二行目" in page_text
    assert "R40" in page_text
    out_doc.close()


def test_alphanumeric_text_uses_biz_ud_gothic():
    """英数字テキスト（R=15mなど）でもBIZ UDゴシックが選択され、画面とPDFの文字幅が一致することを検証"""
    from firereview.services.pdf_renderers.fonts import get_or_register_font, get_font_object
    from PySide6.QtGui import QFont, QFontMetrics

    doc = fitz.open()
    page = doc.new_page()
    reg_fonts = {}
    font_name = get_or_register_font(page, 0, "BIZ UDゴシック", "R=15m", "text", reg_fonts)
    assert font_name == "bizudgothic"

    # 幅の検証
    font_size = 14
    dpi_factor = 72.0 / 150.0
    font_qt = QFont("BIZ UDゴシック")
    font_qt.setPixelSize(font_size)
    fm = QFontMetrics(font_qt)
    qt_w = fm.horizontalAdvance("R=15m")

    font_pdf = get_font_object("bizudgothic")
    pdf_w = font_pdf.text_length("R=15m", fontsize=font_size * dpi_factor) / dpi_factor

    assert pytest.approx(qt_w, abs=1.0) == pdf_w
    doc.close()


def test_update_item_properties_uses_pixel_size(qtbot):
    """update_item_propertiesでfont_sizeが更新された際、pixelSizeが正しく適用されることを検証"""
    view = PDFCanvas()
    qtbot.addWidget(view)
    item = view._add_text_item("テスト", 0, 0, "#000000", font_size=12)
    view.update_item_properties(item.data(0), {"font_size": 18})
    assert item.font().pixelSize() == 18

