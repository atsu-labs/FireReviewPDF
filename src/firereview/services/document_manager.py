import os
from typing import Optional
from PySide6.QtCore import QObject, Signal
from firereview.models import DrawingModel
from firereview.services.pdf_handler import PDFHandler
from firereview.services.project_store import (
    load_project as load_project_file,
    save_project as save_project_file,
)
from firereview.services.pdf_exporter import export_pdf_document


class DocumentManager(QObject):
    """プロジェクトファイル・PDFドキュメントのライフサイクルおよび変更状態（ダーティフラグ）を管理するサービスクラス"""

    dirty_changed = Signal(bool)
    document_changed = Signal()

    def __init__(self, pdf_handler: Optional[PDFHandler] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.pdf_handler = pdf_handler or PDFHandler()
        self.model = DrawingModel()
        self.current_project_path: str = ""
        self.is_dirty: bool = False

    def set_dirty(self, dirty: bool = True):
        """ダーティ状態を設定し、変更があった場合は dirty_changed シグナルを発行する"""
        if self.is_dirty != dirty:
            self.is_dirty = dirty
            self.dirty_changed.emit(self.is_dirty)

    def get_suggested_save_path(self) -> str:
        """保存ダイアログに提案する初期ファイルパスを返す"""
        if self.current_project_path:
            return self.current_project_path
        if self.model.pdf_path:
            base, _ = os.path.splitext(self.model.pdf_path)
            return base + ".json"
        return ""

    def get_active_document_name(self) -> str:
        """タイトルバー等に表示するアクティブなプロジェクトまたはPDFファイル名を返す"""
        if self.current_project_path:
            return os.path.basename(self.current_project_path)
        if self.model.pdf_path:
            return os.path.basename(self.model.pdf_path)
        return ""

    def open_pdf(self, file_path: str) -> bool:
        """新規PDF図面を開き、描画モデルを初期化する"""
        if self.pdf_handler.open_file(file_path):
            self.model = DrawingModel()
            self.model.pdf_path = file_path
            self.current_project_path = ""
            self.set_dirty(False)
            self.document_changed.emit()
            return True
        return False

    def swap_pdf(self, file_path: str) -> bool:
        """既存のアノテーションを維持したまま背景PDFのみを差し替える"""
        if self.pdf_handler.open_file(file_path):
            self.model.pdf_path = file_path
            self.set_dirty(True)
            self.document_changed.emit()
            return True
        return False

    def save_project(self, file_path: str) -> None:
        """現在のモデルをJSONプロジェクトファイルとして保存する"""
        save_project_file(self.model, file_path)
        self.current_project_path = file_path
        self.set_dirty(False)

    def load_project(self, file_path: str) -> DrawingModel:
        """JSONプロジェクトファイルを読み込み、DrawingModelを復元する"""
        return load_project_file(file_path)

    def apply_loaded_project(self, loaded_model: DrawingModel, file_path: str) -> None:
        """読み込んだモデルを適用し、プロジェクトパスを更新する"""
        self.model = loaded_model
        self.current_project_path = file_path
        self.set_dirty(False)
        self.document_changed.emit()

    def export_pdf(self, output_path: str) -> None:
        """現在の注釈を元PDFに合成してエクスポートする"""
        export_pdf_document(self.model, output_path)
