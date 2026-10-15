import os
import tempfile
import fitz
import pytest
from PySide6.QtWidgets import QApplication
from firereview.models import DrawingModel
from firereview.services.pdf_handler import PDFHandler
from firereview.services.pdf_exporter import export_pdf_document
from firereview.ui.canvas.view import PDFCanvas
from firereview.ui.panels.navigator_panel import NavigatorPanel


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def sample_pdf(tmp_path):
    pdf_path = str(tmp_path / "test_doc.pdf")
    doc = fitz.open()
    page = doc.new_page(width=300, height=300)
    # 赤い四角を描画
    page.draw_rect(fitz.Rect(50, 50, 150, 150), color=(1, 0, 0), fill=(1, 0, 0))
    doc.save(pdf_path)
    doc.close()
    return pdf_path


def test_drawing_model_bg_settings():
    model = DrawingModel()
    assert model.bg_opacity == 1.0
    assert model.bg_grayscale is False

    model.bg_opacity = 0.5
    model.bg_grayscale = True
    data = model.to_dict()
    assert data["bg_opacity"] == 0.5
    assert data["bg_grayscale"] is True

    # 復元
    restored = DrawingModel.from_dict(data)
    assert restored.bg_opacity == 0.5
    assert restored.bg_grayscale is True

    # 旧データ互換性テスト
    legacy_data = {
        "scale_factor": 1.0,
        "is_calibrated": False,
        "annotations": [],
    }
    legacy_model = DrawingModel.from_dict(legacy_data)
    assert legacy_model.bg_opacity == 1.0
    assert legacy_model.bg_grayscale is False


def test_pdf_handler_grayscale(qapp, sample_pdf):
    handler = PDFHandler()
    assert handler.open_file(sample_pdf) is True

    pix_color = handler.get_page_pixmap(0, dpi=72, grayscale=False)
    assert pix_color is not None

    pix_gray = handler.get_page_pixmap(0, dpi=72, grayscale=True)
    assert pix_gray is not None

    # キャッシュキーの分離確認
    assert (0, 72, False) in handler._pixmap_cache
    assert (0, 72, True) in handler._pixmap_cache


def test_canvas_bg_opacity(qapp, sample_pdf):
    canvas = PDFCanvas()
    handler = PDFHandler()
    handler.open_file(sample_pdf)
    pix = handler.get_page_pixmap(0, dpi=72)
    canvas.set_page_image(pix)

    assert canvas.bg_opacity == 1.0
    assert canvas.background_item.opacity() == pytest.approx(1.0)

    # 不透明度変更
    canvas.set_background_opacity(0.4)
    assert canvas.bg_opacity == pytest.approx(0.4)
    assert canvas.background_item.opacity() == pytest.approx(0.4)

    # ページ再設定後も不透明度が維持されること
    canvas.set_page_image(pix)
    assert canvas.background_item.opacity() == pytest.approx(0.4)

    # クランプ確認
    canvas.set_background_opacity(0.01)
    assert canvas.bg_opacity == pytest.approx(0.1)
    canvas.set_background_opacity(1.5)
    assert canvas.bg_opacity == pytest.approx(1.0)


def test_navigator_bg_settings_ui(qapp):
    nav = NavigatorPanel()
    
    received_opacity = []
    received_grayscale = []
    nav.bg_opacity_changed.connect(lambda v: received_opacity.append(v))
    nav.bg_grayscale_changed.connect(lambda v: received_grayscale.append(v))

    # スライダー操作
    nav.bg_opacity_slider.setValue(40)
    assert len(received_opacity) == 1
    assert received_opacity[-1] == pytest.approx(0.4)
    assert nav.bg_opacity_value_lbl.text() == "40%"

    # グレースケールトグル操作
    nav.bg_grayscale_check.setChecked(True)
    assert len(received_grayscale) == 1
    assert received_grayscale[-1] is True

    # リセットボタン操作
    nav.bg_reset_btn.click()
    assert received_opacity[-1] == pytest.approx(1.0)
    assert received_grayscale[-1] is False
    assert nav.bg_opacity_slider.value() == 100
    assert nav.bg_opacity_value_lbl.text() == "100%"
    assert nav.bg_grayscale_check.isChecked() is False

    # set_bg_settings によるシグナル非発火更新
    op_len = len(received_opacity)
    gray_len = len(received_grayscale)
    nav.set_bg_settings(0.65, True)
    assert len(received_opacity) == op_len
    assert len(received_grayscale) == gray_len
    assert nav.bg_opacity_slider.value() == 65
    assert nav.bg_opacity_value_lbl.text() == "65%"
    assert nav.bg_grayscale_check.isChecked() is True


def test_pdf_export_with_bg_opacity(sample_pdf, tmp_path):
    model = DrawingModel()
    model.pdf_path = sample_pdf
    model.bg_opacity = 0.5  # 半透明白マスク重畳テスト

    output_pdf = str(tmp_path / "output_faded.pdf")
    export_pdf_document(model, output_pdf)

    assert os.path.exists(output_pdf)
    doc = fitz.open(output_pdf)
    assert len(doc) == 1
    page = doc[0]
    # ページから描画リストやピクスマップが正常に取得できること
    pix = page.get_pixmap()
    assert pix.width > 0 and pix.height > 0
    doc.close()
