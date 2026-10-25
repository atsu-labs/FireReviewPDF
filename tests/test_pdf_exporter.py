import os
import fitz
import pytest
from PySide6.QtCore import QPointF
from firereview.models import DrawingModel, Annotation
from firereview.services.pdf_exporter import export_pdf_document
from firereview.services.pdf_renderers import (
    get_renderer,
    PDF_RENDERER_REGISTRY,
    LinePdfRenderer,
    CirclePdfRenderer,
    ArcPdfRenderer,
    TextPdfRenderer,
    MarkerPdfRenderer,
    LegendPdfRenderer,
)


class TestPdfRenderersRegistry:
    def test_registered_renderers(self):
        assert isinstance(get_renderer("line"), LinePdfRenderer)
        assert isinstance(get_renderer("circle"), CirclePdfRenderer)
        assert isinstance(get_renderer("arc"), ArcPdfRenderer)
        assert isinstance(get_renderer("text"), TextPdfRenderer)
        assert isinstance(get_renderer("marker"), MarkerPdfRenderer)
        assert isinstance(get_renderer("legend"), LegendPdfRenderer)
        assert get_renderer("non_existent_type") is None


class TestPdfExportEndToEnd:
    @pytest.fixture
    def base_pdf_path(self, tmp_path):
        pdf_path = str(tmp_path / "source.pdf")
        doc = fitz.open()
        doc.new_page(width=595, height=842)
        doc.save(pdf_path)
        doc.close()
        return pdf_path

    def test_export_all_annotation_types(self, base_pdf_path, tmp_path):
        model = DrawingModel()
        model.pdf_path = base_pdf_path
        model.scale_factor = 2.0
        model.is_calibrated = True

        # 1. Line
        line = Annotation("line")
        line.points = [QPointF(50, 50), QPointF(200, 50)]
        line.text = "Line 10m"
        model.annotations.append(line)

        # 2. Polyline with markers
        polyline = Annotation("polyline")
        polyline.points = [QPointF(50, 100), QPointF(150, 100), QPointF(150, 150)]
        polyline.start_marker = "circle"
        polyline.end_marker = "arrow"
        polyline.text = "Path"
        model.annotations.append(polyline)

        # 3. Polygon
        polygon = Annotation("polygon")
        polygon.points = [QPointF(50, 200), QPointF(150, 200), QPointF(100, 280)]
        polygon.fill_color = "#00ff00"
        polygon.fill_opacity = 40
        polygon.text = "Zone"
        model.annotations.append(polygon)

        # 4. Circle
        circle = Annotation("circle")
        circle.points = [QPointF(300, 200)]
        circle.radius_px = 60.0
        circle.center_marker = "cross"
        circle.text = "Radius"
        model.annotations.append(circle)

        # 5. Arc
        arc = Annotation("arc")
        arc.points = [QPointF(300, 400)]
        arc.radius_px = 50.0
        arc.drag_angle = 45.0
        arc.arc_span = 60.0
        arc.show_radial_line = True
        arc.center_marker = "circle"
        arc.text = "Arc"
        model.annotations.append(arc)

        # 6. Marker (square and check)
        m1 = Annotation("marker")
        m1.points = [QPointF(50, 350)]
        m1.marker_style = "square"
        m1.color = "#ff1744"
        model.annotations.append(m1)

        m2 = Annotation("marker")
        m2.points = [QPointF(80, 350)]
        m2.marker_style = "check"
        m2.color = "#2979ff"
        model.annotations.append(m2)

        # 7. Text with border and leader line
        text = Annotation("text")
        text.points = [QPointF(200, 500), QPointF(300, 550)]
        text.text = "Multiline\nComment"
        text.has_border = True
        text.has_leader = True
        model.annotations.append(text)

        # 8. Legend
        legend = Annotation("legend")
        legend.points = [QPointF(50, 600)]
        model.annotations.append(legend)

        output_path = str(tmp_path / "exported.pdf")
        export_pdf_document(model, output_path)

        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0

        # Verify exported PDF is valid
        out_doc = fitz.open(output_path)
        assert len(out_doc) == 1
        out_doc.close()


class TestPdfAtomicExportAndLocking:
    @pytest.fixture
    def base_pdf_path(self, tmp_path):
        pdf_path = str(tmp_path / "source.pdf")
        doc = fitz.open()
        doc.new_page(width=595, height=842)
        doc.save(pdf_path)
        doc.close()
        return pdf_path

    def test_check_writable_file_locked(self, tmp_path):
        from firereview.services.pdf_exporter import check_writable, PdfFileLockedError
        from unittest.mock import patch

        test_file = str(tmp_path / "locked.pdf")
        with open(test_file, "wb") as f:
            f.write(b"%PDF-1.4 dummy")

        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with pytest.raises(PdfFileLockedError):
                check_writable(test_file)

    def test_export_pdf_atomic_save_success(self, base_pdf_path, tmp_path):
        from firereview.services.pdf_exporter import export_pdf_document

        model = DrawingModel()
        model.pdf_path = base_pdf_path

        out_path = str(tmp_path / "output.pdf")
        export_pdf_document(model, out_path)

        assert os.path.exists(out_path)
        # 一時ファイルが残っていないことを確認
        temp_files = [f for f in os.listdir(tmp_path) if f.startswith(".firereview_export_")]
        assert len(temp_files) == 0

    def test_export_pdf_atomic_failure_keeps_original(self, base_pdf_path, tmp_path):
        from firereview.services.pdf_exporter import export_pdf_document
        from unittest.mock import patch

        model = DrawingModel()
        model.pdf_path = base_pdf_path

        out_path = str(tmp_path / "existing.pdf")
        original_content = b"%PDF-1.4 original intact content"
        with open(out_path, "wb") as f:
            f.write(original_content)

        # レンダリングまたは保存処理中の例外発生をシミュレート
        with patch("fitz.open", side_effect=RuntimeError("Simulated rendering crash")):
            with pytest.raises(RuntimeError):
                export_pdf_document(model, out_path)

        # 既存ファイルが壊れず元の内容のままであること
        assert os.path.exists(out_path)
        with open(out_path, "rb") as f:
            assert f.read() == original_content

        # 一時ファイルも残っていないこと
        temp_files = [f for f in os.listdir(tmp_path) if f.startswith(".firereview_export_")]
        assert len(temp_files) == 0

    def test_export_pdf_overwrite_original_pdf(self, base_pdf_path):
        """元PDFファイル（model.pdf_path）と同一パスへのエクスポートが安全に成功することを確認"""
        from firereview.services.pdf_exporter import export_pdf_document

        model = DrawingModel()
        model.pdf_path = base_pdf_path

        # 注釈を追加
        line = Annotation("line")
        line.points = [QPointF(10, 10), QPointF(100, 100)]
        model.annotations.append(line)

        # 元ファイルと同じパスに出力
        export_pdf_document(model, base_pdf_path)

        assert os.path.exists(base_pdf_path)
        doc = fitz.open(base_pdf_path)
        assert len(doc) == 1
        doc.close()

    def test_document_manager_export_same_file(self, qapp, base_pdf_path):
        """DocumentManager 経由で同一ファイルへエクスポートした際に、pdf_handlerが正常に再オープンされること"""
        from firereview.services.document_manager import DocumentManager
        from firereview.services.pdf_handler import PDFHandler

        handler = PDFHandler()
        manager = DocumentManager(pdf_handler=handler)
        opened = manager.open_pdf(base_pdf_path)
        assert opened is True
        assert handler.doc is not None

        # 注釈を追加
        line = Annotation("line")
        line.points = [QPointF(20, 20), QPointF(80, 80)]
        manager.model.annotations.append(line)

        # 同一パスへエクスポート
        manager.export_pdf(base_pdf_path)

        # エクスポート後もpdf_handlerが開かれており、ページ取得等ができること
        assert handler.doc is not None
        assert handler.get_page_count() == 1
        pixmap = handler.get_page_pixmap(0)
        assert pixmap is not None
        handler.close()

    def test_check_writable_empty_path(self):
        from firereview.services.pdf_exporter import check_writable, PdfExportError

        with pytest.raises(PdfExportError, match="出力先パスが指定されていません"):
            check_writable("")
        with pytest.raises(PdfExportError, match="出力先パスが指定されていません"):
            check_writable("   ")

    def test_check_writable_directory(self, tmp_path):
        from firereview.services.pdf_exporter import check_writable, PdfExportError

        with pytest.raises(PdfExportError, match="フォルダ（ディレクトリ）です"):
            check_writable(str(tmp_path))

    def test_check_writable_probe_cleanup_on_failure(self, tmp_path):
        from firereview.services.pdf_exporter import check_writable, PdfExportError
        from unittest.mock import patch

        target_file = str(tmp_path / "new_dir" / "out.pdf")

        # ディレクトリ作成後のプローブ書き込み失敗時に一時ファイルが残らないこと
        with patch("builtins.open", side_effect=PermissionError("Cannot write to directory")):
            with pytest.raises(PdfExportError, match="書き込み権限がありません"):
                check_writable(target_file)

        # プローブファイルが残っていないこと
        parent_dir = str(tmp_path / "new_dir")
        if os.path.exists(parent_dir):
            probe_files = [f for f in os.listdir(parent_dir) if f.startswith(".firereview_probe_")]
            assert len(probe_files) == 0

    def test_export_pdf_after_replace_exception_safety(self, base_pdf_path, tmp_path):
        """after_replace フックで例外が発生しても、エクスポート完了自体は成功すること"""
        from firereview.services.pdf_exporter import export_pdf_document

        model = DrawingModel()
        model.pdf_path = base_pdf_path
        out_path = str(tmp_path / "out_hook_test.pdf")

        def failing_after_replace():
            raise RuntimeError("Hook failure")

        # 例外が握りつぶされて正常終了（ファイル置換は完了）すること
        export_pdf_document(model, out_path, after_replace=failing_after_replace)
        assert os.path.exists(out_path)

    def test_export_pdf_sets_rgb_transparency_group_on_all_pages(self, tmp_path):
        """エクスポートされたPDFの全ページ辞書に /Group (/CS /DeviceRGB) が設定されること（Issue #80）"""
        src_path = str(tmp_path / "src_multipage.pdf")
        src_doc = fitz.open()
        src_doc.new_page(width=595, height=842)
        src_doc.new_page(width=595, height=842)
        # 1ページ目にあえて CMYK Transparency Group を設定しておく
        src_doc.xref_set_key(
            src_doc[0].xref, "Group", "<< /Type /Group /S /Transparency /CS /DeviceCMYK >>"
        )
        src_doc.save(src_path)
        src_doc.close()

        model = DrawingModel()
        model.pdf_path = src_path
        model.bg_opacity = 0.4

        out_path = str(tmp_path / "out_rgb_group.pdf")
        export_pdf_document(model, out_path)

        out_doc = fitz.open(out_path)
        assert len(out_doc) == 2
        for page in out_doc:
            key_type, key_val = out_doc.xref_get_key(page.xref, "Group")
            assert key_type == "dict"
            assert "/Type/Group" in key_val.replace(" ", "")
            assert "/S/Transparency" in key_val.replace(" ", "")
            assert "/CS/DeviceRGB" in key_val.replace(" ", "")
        out_doc.close()
        assert os.path.exists(out_path)

