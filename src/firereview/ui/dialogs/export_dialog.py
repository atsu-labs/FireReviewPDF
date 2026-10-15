from typing import List, Optional, Dict, Any
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGroupBox,
    QRadioButton,
    QCheckBox,
    QPushButton,
    QFrame,
)


class ExportPdfDialog(QDialog):
    """PDFエクスポート設定ダイアログ (Issue #65)

    エクスポート対象のページ範囲（全ページ / 注釈があるページのみ）および
    背景図面の不透明度反映オプションを設定します。
    """

    def __init__(
        self,
        parent=None,
        total_pages: int = 1,
        annotated_pages: Optional[List[int]] = None,
        bg_opacity: float = 1.0,
    ):
        super().__init__(parent)
        self.total_pages = max(1, total_pages)
        self.annotated_pages = sorted(list(set(annotated_pages or [])))
        self.bg_opacity = bg_opacity

        self.setWindowTitle("PDF書き出し設定")
        self.setFixedSize(460, 320)
        self._apply_dialog_style()
        self._setup_ui()

    def _apply_dialog_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
            }
            QLabel {
                color: #ffffff;
                border: none;
            }
            QGroupBox {
                border: 1px solid #333344;
                border-radius: 6px;
                margin-top: 14px;
                padding-top: 14px;
                padding-bottom: 10px;
                padding-left: 10px;
                padding-right: 10px;
                font-weight: bold;
                color: #aaaacc;
                font-size: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 6px;
                background-color: #1e1e2e;
            }
            QRadioButton {
                color: #dddddd;
                font-size: 12px;
                spacing: 8px;
            }
            QRadioButton:disabled {
                color: #666677;
            }
            QCheckBox {
                color: #dddddd;
                font-size: 12px;
                spacing: 8px;
            }
            QPushButton {
                background-color: #2a2a3d;
                color: #ffffff;
                border: 1px solid #444455;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #35354d;
                border-color: #666677;
            }
            QPushButton#primaryBtn {
                background-color: #7c4dff;
                border: 1px solid #7c4dff;
            }
            QPushButton#primaryBtn:hover {
                background-color: #6c3bee;
            }
        """)

    def _format_page_summary(self, pages: List[int]) -> str:
        """0始まりのページ番号リストを1始まりの表示用文字列（例: 'P.1, P.3, P.12'）に整形する"""
        if not pages:
            return ""
        page_strs = [f"P.{p + 1}" for p in pages]
        if len(page_strs) <= 6:
            return ", ".join(page_strs)
        # 6件を超える場合は省略
        return f"{', '.join(page_strs[:5])} ... (計 {len(page_strs)} ページ)"

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # 1. 範囲指定グループボックス
        range_group = QGroupBox("出力範囲")
        range_layout = QVBoxLayout(range_group)
        range_layout.setSpacing(10)

        has_annotations = len(self.annotated_pages) > 0
        summary_str = self._format_page_summary(self.annotated_pages)

        # 注釈があるページのみラジオボタン
        if has_annotations:
            ann_text = f"注釈があるページのみ  —  {len(self.annotated_pages)} ページ ({summary_str})"
        else:
            ann_text = "注釈があるページのみ  (※注釈がありません)"
        
        self.radio_annotated = QRadioButton(ann_text)
        self.radio_annotated.setEnabled(has_annotations)
        if has_annotations and len(self.annotated_pages) > 6:
            full_summary = ", ".join(f"P.{p + 1}" for p in self.annotated_pages)
            self.radio_annotated.setToolTip(f"出力対象: {full_summary}")

        # 全ページラジオボタン
        self.radio_all = QRadioButton(f"全ページ  —  全 {self.total_pages} ページ")

        # デフォルト選択: 注釈があれば注釈のみ、なければ全ページ
        if has_annotations:
            self.radio_annotated.setChecked(True)
        else:
            self.radio_all.setChecked(True)

        range_layout.addWidget(self.radio_annotated)
        range_layout.addWidget(self.radio_all)
        main_layout.addWidget(range_group)

        # 2. オプショングループボックス
        options_group = QGroupBox("オプション")
        options_layout = QVBoxLayout(options_group)
        options_layout.setSpacing(6)

        self.check_apply_bg_opacity = QCheckBox("背景図面のフェード（透明度）を出力PDFに反映する")
        # デフォルトはON
        self.check_apply_bg_opacity.setChecked(True)

        # 現在の透明度状態についての補足ラベル
        opacity_percent = int(round(self.bg_opacity * 100))
        if self.bg_opacity < 0.999:
            opacity_note = f"現在の背景濃度: {opacity_percent}% （半透明白マスクを重畳して出力します）"
        else:
            opacity_note = "現在の背景濃度: 100% （フェードなしで出力します）"
        lbl_note = QLabel(opacity_note)
        lbl_note.setStyleSheet("color: #888899; font-size: 11px; margin-left: 22px;")

        options_layout.addWidget(self.check_apply_bg_opacity)
        options_layout.addWidget(lbl_note)
        main_layout.addWidget(options_group)

        main_layout.addStretch()

        # 3. アクションボタン
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("キャンセル")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_export = QPushButton("書き出し...")
        self.btn_export.setObjectName("primaryBtn")
        self.btn_export.clicked.connect(self.accept)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_export)
        main_layout.addLayout(btn_layout)

    def get_export_settings(self) -> Dict[str, Any]:
        """ダイアログで確定されたエクスポート設定を返す"""
        annotated_only = self.radio_annotated.isChecked()
        if annotated_only:
            page_indices = list(self.annotated_pages)
            page_count = len(page_indices)
            summary_list = [f"P.{p + 1}" for p in page_indices]
            page_summary = ", ".join(summary_list)
        else:
            page_indices = None
            page_count = self.total_pages
            page_summary = f"全 {self.total_pages} ページ"

        return {
            "page_indices": page_indices,
            "apply_bg_opacity": self.check_apply_bg_opacity.isChecked(),
            "is_annotated_only": annotated_only,
            "page_count": page_count,
            "page_summary": page_summary,
        }
