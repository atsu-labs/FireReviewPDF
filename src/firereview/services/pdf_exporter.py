import fitz
from .pdf_renderers import (
    PdfRenderContext,
    get_or_register_font,
    get_renderer,
)


def export_pdf_document(model, output_path: str) -> None:
    """描画モデル内の注釈を元PDFに焼き込み、指定パスへ出力します。"""
    dpi_factor = 72.0 / 150.0
    export_doc = None

    try:
        export_doc = fitz.open(model.pdf_path)
        # Track registered fonts per page to avoid redundant inserts: {page_num: {font_name_in_pdf: name}}
        registered_page_fonts = {}

        for ann in model.annotations:
            if ann.page_num >= len(export_doc):
                continue

            page = export_doc[ann.page_num]

            font_family_str = getattr(ann, "font_family", "Arial")
            page_font = get_or_register_font(
                page, ann.page_num, font_family_str, getattr(ann, "text", ""), ann.type, registered_page_fonts
            )

            renderer = get_renderer(ann.type)
            if renderer is None:
                continue

            ctx = PdfRenderContext(
                page=page,
                page_num=ann.page_num,
                model=model,
                dpi_factor=dpi_factor,
                page_font=page_font,
                ann=ann,
            )
            renderer.render(ctx, ann)

        # フォントをサブセット化して不要な文字グリフを排除し、PDFサイズを劇的に軽量化します（数MBから数KB程度に削減）
        try:
            export_doc.subset_fonts()
        except Exception:
            pass

        export_doc.save(output_path, garbage=4, deflate=True)

    finally:
        if export_doc is not None:
            export_doc.close()
