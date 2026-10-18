import fitz
import pytest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QImage, QPainter

from firereview.services.pdf_handler import PDFHandler
from firereview.ui.canvas.view import PDFCanvas
from firereview.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def sample_pdf(tmp_path):
    pdf_path = str(tmp_path / "issue42_test.pdf")
    doc = fitz.open()
    page = doc.new_page(width=400, height=400)
    # 境界確認用の赤矩形と黒矩形を描画
    page.draw_rect(fitz.Rect(40, 40, 200, 200), color=(1, 0, 0), fill=(1, 0, 0))
    page.draw_rect(fitz.Rect(200, 200, 360, 360), color=(0, 0, 0), fill=(0, 0, 0))
    doc.save(pdf_path)
    doc.close()
    return pdf_path


def test_pdf_handler_clip_pixmap_and_cache_isolation(qapp, sample_pdf):
    handler = PDFHandler()
    assert handler.open_file(sample_pdf) is True

    # 1. ベース全体画像(150 DPI)を取得
    base_pix = handler.get_page_pixmap(0, dpi=150, grayscale=False)
    assert base_pix is not None
    assert (0, 150, False) in handler._pixmap_cache

    # 2. 150 DPIシーン座標系での部分領域(100x100)を 300 DPI (2倍) でクリップ取得
    clip_scene = QRectF(50.0, 60.0, 120.0, 100.0)
    res_300 = handler.get_page_clip_pixmap(0, clip_scene, dpi=300, base_dpi=150, grayscale=False)
    assert res_300 is not None
    pix_300, actual_rect_300 = res_300

    # 300 DPI は 150 DPI の2倍のピクセル密度を持つこと
    assert pix_300.width() == pytest.approx(actual_rect_300.width() * 2.0, abs=1.0)
    assert pix_300.height() == pytest.approx(actual_rect_300.height() * 2.0, abs=1.0)
    assert actual_rect_300.x() == pytest.approx(50.0, abs=1.0)
    assert actual_rect_300.y() == pytest.approx(60.0, abs=1.0)

    # 3. 最大DPI上限(600 DPI)のクランプ確認（900 DPI要求時も600 DPI=4倍に制限されること）
    res_capped = handler.get_page_clip_pixmap(0, clip_scene, dpi=900, base_dpi=150, grayscale=False)
    assert res_capped is not None
    pix_600, actual_rect_600 = res_capped
    assert pix_600.width() == pytest.approx(actual_rect_600.width() * 4.0, abs=1.0)

    # 4. クリップキャッシュが全体画像キャッシュを追い出さないこと
    assert (0, 150, False) in handler._pixmap_cache
    assert len(handler._clip_cache) == 2

    handler.close()


def test_canvas_zoom_debounced_rerender_and_immediate_clear_on_zoom_out(qapp, sample_pdf):
    handler = PDFHandler()
    handler.open_file(sample_pdf)

    canvas = PDFCanvas()
    canvas.resize(400, 300)
    canvas.set_high_res_provider(
        lambda rect, dpi: handler.get_page_clip_pixmap(0, rect, dpi=dpi, base_dpi=150)
    )

    base_pix = handler.get_page_pixmap(0, dpi=150)
    canvas.set_page_image(base_pix)

    # 初期状態（等倍 1.0x = 150 DPI）では高解像度パッチは存在しない
    assert canvas.high_res_bg_item is None
    assert canvas.current_high_res_dpi == 0

    # 2.0倍（300 DPI相当）にズームするとデバウンスタイマーが開始される
    canvas.set_zoom_scale(2.0)
    assert canvas._rerender_timer.isActive() is True
    assert canvas._calculate_target_dpi() == 300

    # デバウンス発火（高解像度描画実行）
    canvas._rerender_timer.stop()
    assert canvas.update_high_res_background() is True
    assert canvas.high_res_bg_item is not None
    assert canvas.high_res_paper_item is not None
    assert canvas.current_high_res_dpi == 300
    assert canvas.high_res_bg_item.scale() == pytest.approx(150.0 / 300.0)
    assert canvas.high_res_bg_item.zValue() == pytest.approx(-0.8)
    assert canvas.high_res_paper_item.zValue() == pytest.approx(-0.9)

    # 4.0倍（600 DPI相当）および 6.0倍（上限600 DPI）の確認
    canvas.set_zoom_scale(6.0)
    canvas._rerender_timer.stop()
    assert canvas.update_high_res_background() is True
    assert canvas.current_high_res_dpi == 600
    assert canvas.high_res_bg_item.scale() == pytest.approx(150.0 / 600.0)

    # 等倍以下（1.0倍）に縮小した際は、デバウンスを待たず即座に高解像度パッチが破棄されること
    canvas.set_zoom_scale(1.0)
    assert canvas._rerender_timer.isActive() is False
    assert canvas.high_res_bg_item is None
    assert canvas.high_res_paper_item is None
    assert canvas.current_high_res_dpi == 0

    handler.close()


def test_viewport_margin_and_pan_retains_patch_until_debounce(qapp, sample_pdf):
    handler = PDFHandler()
    handler.open_file(sample_pdf)

    canvas = PDFCanvas()
    canvas.resize(200, 200)
    canvas.set_high_res_provider(
        lambda rect, dpi: handler.get_page_clip_pixmap(0, rect, dpi=dpi, base_dpi=150)
    )
    canvas.set_page_image(handler.get_page_pixmap(0, dpi=150))

    canvas.set_zoom_scale(2.0)
    canvas._rerender_timer.stop()
    canvas.centerOn(400.0, 400.0)
    canvas._rerender_timer.stop()

    # 余白なしの表示領域と、25%余白（縦横1.5倍）付きの表示領域を比較
    raw_rect = canvas.get_visible_scene_rect(margin_ratio=0.0)
    padded_rect = canvas.get_visible_scene_rect(margin_ratio=0.25)
    assert padded_rect.width() == pytest.approx(raw_rect.width() * 1.5, rel=1e-2)
    assert padded_rect.height() == pytest.approx(raw_rect.height() * 1.5, rel=1e-2)

    assert canvas.update_high_res_background() is True
    prev_rect = QRectF(canvas.current_high_res_rect)

    # パン（スクロール）した直後は、直前の高解像度パッチを維持したままデバウンスタイマーが動くこと
    canvas.horizontalScrollBar().setValue(canvas.horizontalScrollBar().value() + 30)
    assert canvas._rerender_timer.isActive() is True
    assert canvas.high_res_bg_item is not None
    assert canvas.current_high_res_rect == prev_rect

    handler.close()


def test_high_res_patch_does_not_double_darken_with_bg_opacity(qapp, tmp_path):
    # 全面黒のPDFを作成して、背景不透明度(0.2)でベース画像と高解像度パッチが二重合成されないことを検証
    black_pdf = str(tmp_path / "black.pdf")
    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    page.draw_rect(fitz.Rect(0, 0, 200, 200), color=(0, 0, 0), fill=(0, 0, 0))
    doc.save(black_pdf)
    doc.close()

    handler = PDFHandler()
    handler.open_file(black_pdf)

    canvas = PDFCanvas()
    canvas.resize(200, 200)
    canvas.set_high_res_provider(
        lambda rect, dpi: handler.get_page_clip_pixmap(0, rect, dpi=dpi, base_dpi=150)
    )
    canvas.set_page_image(handler.get_page_pixmap(0, dpi=150))
    canvas.set_background_opacity(0.2)

    # 1. 高解像度パッチなしでのレンダリング輝度を取得
    img_base = QImage(100, 100, QImage.Format_ARGB32)
    p1 = QPainter(img_base)
    canvas.scene.render(p1, QRectF(0, 0, 100, 100), QRectF(50, 50, 100, 100))
    p1.end()
    base_red = img_base.pixelColor(50, 50).red()

    # 2. 2倍ズームで高解像度パッチを重ねた状態でのレンダリング輝度を取得
    canvas.set_zoom_scale(2.0)
    canvas._rerender_timer.stop()
    assert canvas.update_high_res_background() is True
    assert canvas.high_res_bg_item.opacity() == pytest.approx(0.2)

    img_high = QImage(100, 100, QImage.Format_ARGB32)
    p2 = QPainter(img_high)
    canvas.scene.render(p2, QRectF(0, 0, 100, 100), QRectF(50, 50, 100, 100))
    p2.end()
    high_red = img_high.pixelColor(50, 50).red()

    # 白下地マスクにより二重合成されず、ベース画像単体時と同じ明るさ(約204)が保たれること
    assert high_red == pytest.approx(base_red, abs=3)
    assert high_red > 180

    handler.close()


def test_main_window_toolbar_zoom_and_grayscale_sync(qapp, sample_pdf):
    window = MainWindow()
    window.resize(1000, 800)
    assert window.document_manager.open_pdf(sample_pdf) is True
    window.update_page_view()
    window.fit_to_page()

    # Fit to Page 時は高解像度パッチなし
    assert window.canvas.high_res_bg_item is None

    # ツールバーから 200% を選択 -> 論理倍率2.0 (300 DPI) がスケジュールされること
    window._on_zoom_combo_changed_from_toolbar("200%")
    assert window.canvas._calculate_target_dpi() == 300
    window.canvas._rerender_timer.stop()
    assert window.canvas.update_high_res_background() is True
    assert window.canvas.current_high_res_dpi == 300

    # 高倍率のまま白黒(グレースケール)設定を切り替えた際も再描画がスケジュールされること
    window.on_bg_grayscale_changed(True)
    assert window.canvas._rerender_timer.isActive() is True
    window.canvas._rerender_timer.stop()
    assert window.canvas.update_high_res_background() is True
    assert window.canvas.high_res_bg_item is not None

    # 100% 実寸大表示にリセットすると即座に高解像度パッチが解除されること
    window.reset_zoom_to_100()
    assert window.canvas.high_res_bg_item is None
    assert window.canvas.current_high_res_dpi == 0

    window.pdf_handler.close()
