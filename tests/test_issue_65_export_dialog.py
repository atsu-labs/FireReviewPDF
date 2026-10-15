import os
import fitz
import pytest
from PySide6.QtWidgets import QApplication
from firereview.models import DrawingModel, LineAnnotation
from firereview.services.pdf_handler import PDFHandler
from firereview.services.document_manager import DocumentManager
from firereview.services.pdf_exporter import export_pdf_document, PdfExportError
from firereview.ui.dialogs.export_dialog import ExportPdfDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def multi_page_pdf(tmp_path):
    pdf_path = str(tmp_path / "multi_page.pdf")
    doc = fitz.open()
    for i in range(5):
        page = doc.new_page(width=300, height=300)
        page.draw_rect(fitz.Rect(10, 10, 50, 50), color=(0, 0, 1))
    doc.save(pdf_path)
    doc.close()
    return pdf_path


def test_export_dialog_no_annotations(qapp):
    dialog = ExportPdfDialog(total_pages=5, annotated_pages=[], bg_opacity=1.0)
    assert dialog.radio_annotated.isEnabled() is False
    assert dialog.radio_all.isChecked() is True

    settings = dialog.get_export_settings()
    assert settings["page_indices"] is None
    assert settings["is_annotated_only"] is False
    assert settings["page_count"] == 5
    assert settings["apply_bg_opacity"] is True


def test_export_dialog_with_annotations(qapp):
    annotated = [0, 2, 4]
    dialog = ExportPdfDialog(total_pages=5, annotated_pages=annotated, bg_opacity=0.7)
    assert dialog.radio_annotated.isEnabled() is True
    assert dialog.radio_annotated.isChecked() is True
    assert "P.1, P.3, P.5" in dialog.radio_annotated.text()

    settings = dialog.get_export_settings()
    assert settings["page_indices"] == [0, 2, 4]
    assert settings["is_annotated_only"] is True
    assert settings["page_count"] == 3
    assert settings["apply_bg_opacity"] is True

    # 全ページに切り替え
    dialog.radio_all.setChecked(True)
    settings_all = dialog.get_export_settings()
    assert settings_all["page_indices"] is None
    assert settings_all["is_annotated_only"] is False
    assert settings_all["page_count"] == 5

    # オプション解除
    dialog.check_apply_bg_opacity.setChecked(False)
    settings_opt = dialog.get_export_settings()
    assert settings_opt["apply_bg_opacity"] is False


def test_export_pdf_document_with_page_selection(multi_page_pdf, tmp_path):
    model = DrawingModel()
    model.pdf_path = multi_page_pdf
    
    # ページ0とページ2に注釈を追加
    ann0 = LineAnnotation()
    ann0.page_num = 0
    from PySide6.QtCore import QPointF
    ann0.points = [QPointF(20, 20), QPointF(80, 80)]
    ann0.color = "#ff0000"

    ann2 = LineAnnotation()
    ann2.page_num = 2
    ann2.points = [QPointF(30, 30), QPointF(90, 90)]
    ann2.color = "#00ff00"

    model.annotations = [ann0, ann2]

    # 1. ページ0と2のみ抽出
    out_pdf = str(tmp_path / "output_selected.pdf")
    export_pdf_document(model, out_pdf, page_indices=[0, 2], apply_bg_opacity=True)

    assert os.path.exists(out_pdf)
    doc = fitz.open(out_pdf)
    assert len(doc) == 2
    doc.close()

    # 2. 全ページエクスポート (page_indices=None)
    out_all_pdf = str(tmp_path / "output_all.pdf")
    export_pdf_document(model, out_all_pdf, page_indices=None, apply_bg_opacity=True)

    assert os.path.exists(out_all_pdf)
    doc_all = fitz.open(out_all_pdf)
    assert len(doc_all) == 5
    doc_all.close()


def test_export_pdf_document_invalid_page_indices(multi_page_pdf, tmp_path):
    model = DrawingModel()
    model.pdf_path = multi_page_pdf
    out_pdf = str(tmp_path / "output_invalid.pdf")
    
    # 存在しないページ番号のみ指定
    with pytest.raises(PdfExportError):
        export_pdf_document(model, out_pdf, page_indices=[99, 100])


def test_document_manager_export_pdf(multi_page_pdf, tmp_path):
    handler = PDFHandler()
    dm = DocumentManager(pdf_handler=handler)
    assert dm.open_pdf(multi_page_pdf) is True

    out_pdf = str(tmp_path / "dm_export.pdf")
    dm.export_pdf(out_pdf, page_indices=[1, 3], apply_bg_opacity=False)

    assert os.path.exists(out_pdf)
    doc = fitz.open(out_pdf)
    assert len(doc) == 2
    doc.close()
