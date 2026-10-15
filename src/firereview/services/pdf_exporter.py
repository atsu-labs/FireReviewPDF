import os
import tempfile
from typing import Callable, Optional
import fitz
from .pdf_renderers import (
    PdfRenderContext,
    get_or_register_font,
    get_renderer,
)


class PdfExportError(Exception):
    """PDFエクスポート処理における基底例外クラス"""
    pass


class PdfFileLockedError(PdfExportError):
    """出力先ファイルが他のプロセスによりロックされている場合の例外"""
    pass


def check_writable(output_path: str) -> None:
    """出力先ファイルおよびディレクトリが書き込み可能かを事前に検証する (Fast-Fail)。

    Raises:
        PdfFileLockedError: ファイルが他プロセスで開かれている等の理由で上書きできない場合。
        PdfExportError: 出力先ディレクトリが存在しない、または作成・書き込みできない場合。
    """
    if not output_path or not str(output_path).strip():
        raise PdfExportError("出力先パスが指定されていません。")

    abs_output_path = os.path.abspath(output_path)
    if os.path.isdir(abs_output_path):
        raise PdfExportError(f"指定された出力先はフォルダ（ディレクトリ）です: {abs_output_path}")

    # 1. 既存ファイルがある場合
    if os.path.exists(abs_output_path):
        try:
            with open(abs_output_path, "r+b"):
                pass
        except PermissionError as e:
            raise PdfFileLockedError(
                f"指定されたファイルは別のプログラム（Adobe Acrobat Reader、Webブラウザなど）で開かれているため上書きできません。\n"
                f"ファイルを閉じるか、別のファイル名を指定して再度お試しください。\n"
                f"ファイル: {abs_output_path}"
            ) from e
        except OSError as e:
            raise PdfFileLockedError(f"ファイルに書き込むことができません: {e}") from e
    else:
        # 2. ファイルがまだない場合、親ディレクトリの書き込み可否を検証
        output_dir = os.path.dirname(abs_output_path)
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                raise PdfExportError(f"出力先フォルダを作成できません: {output_dir}") from e

        test_file = os.path.join(output_dir, f".firereview_probe_{os.getpid()}_{id(output_path)}.tmp")
        try:
            with open(test_file, "wb") as f:
                f.write(b"")
        except Exception as e:
            raise PdfExportError(f"出力先フォルダへの書き込み権限がありません: {output_dir}") from e
        finally:
            if os.path.exists(test_file):
                try:
                    os.remove(test_file)
                except Exception:
                    pass


def export_pdf_document(
    model,
    output_path: str,
    before_replace: Optional[Callable[[], None]] = None,
    after_replace: Optional[Callable[[], None]] = None,
) -> None:
    """描画モデル内の注釈を元PDFに焼き込み、アトミック保存により指定パスへ安全に出力します。

    Args:
        model: DrawingModel インスタンス
        output_path: 出力先PDFファイルパス
        before_replace: 一時ファイルから正式パスへの置換直前に実行するコールバック（ロック解除等）
        after_replace: 置換直後に実行するコールバック（再オープン等）

    Raises:
        PdfFileLockedError: 出力先ファイルがロックされている場合
        PdfExportError: エクスポート処理中にエラーが発生した場合
    """
    if not model.pdf_path or not os.path.exists(model.pdf_path):
        raise PdfExportError(f"元PDFファイルが見つかりません: {getattr(model, 'pdf_path', '')}")

    abs_output_path = os.path.abspath(output_path)
    output_dir = os.path.dirname(abs_output_path)

    # 1. 事前書き込みチェック (Fast-Fail)
    check_writable(abs_output_path)

    # 2. 同一ディレクトリ内にアトミック保存用の一時ファイルを作成
    temp_fd, temp_path = tempfile.mkstemp(
        dir=output_dir,
        prefix=".firereview_export_",
        suffix=".tmp.pdf"
    )
    os.close(temp_fd)

    dpi_factor = 72.0 / 150.0
    export_doc = None

    try:
        export_doc = fitz.open(model.pdf_path)
        registered_page_fonts = {}

        # 背景不透明度の適用（1.0未満の場合、白マスクを重畳して背景をフェード）
        bg_opacity = getattr(model, "bg_opacity", 1.0)
        if bg_opacity < 0.999:
            white_opacity = max(0.0, min(1.0, 1.0 - bg_opacity))
            for page in export_doc:
                page.draw_rect(
                    page.rect,
                    fill=(1, 1, 1),
                    fill_opacity=white_opacity,
                    stroke_opacity=0,
                )

        for ann in model.annotations:
            if ann.page_num >= len(export_doc):
                continue

            page = export_doc[ann.page_num]

            font_family_str = getattr(ann, "font_family", "BIZ UDゴシック")
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

        # フォントをサブセット化
        try:
            export_doc.subset_fonts()
        except Exception:
            pass

        # 一時ファイルへ書き出し
        export_doc.save(temp_path, garbage=4, deflate=True)
        export_doc.close()
        export_doc = None

        # 置換直前フック（同一ファイル上書き時の既存ハンドルクローズ等）
        if before_replace is not None:
            before_replace()

        try:
            # アトミック置換
            os.replace(temp_path, abs_output_path)
        except (PermissionError, OSError) as e:
            raise PdfFileLockedError(
                f"指定されたファイルは別のプログラム（Adobe Acrobat Reader、Webブラウザなど）で開かれているため上書きできません。\n"
                f"ファイルを閉じるか、別のファイル名を指定して再度お試しください。\n"
                f"ファイル: {abs_output_path}"
            ) from e
        finally:
            # 置換後フック（リオープン等）
            if after_replace is not None:
                try:
                    after_replace()
                except Exception:
                    pass

    finally:
        if export_doc is not None:
            try:
                export_doc.close()
            except Exception:
                pass
        # 置換に失敗し一時ファイルが残っている場合は確実に削除
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
