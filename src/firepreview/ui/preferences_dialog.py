import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QLabel,
    QFrame, QRadioButton, QButtonGroup, QComboBox, QPushButton,
    QMessageBox, QDialogButtonBox, QGroupBox
)

class PreferencesDialog(QDialog):
    trigger_canvas_calibration = Signal(bool)  # True = all pages, False = current page only
    settings_updated = Signal()

    def __init__(self, parent, model, current_page, total_pages, dpi=150.0):
        super().__init__(parent)
        self.main_window = parent
        self.model = model
        self.current_page = current_page
        self.total_pages = total_pages
        self.dpi = dpi
        
        self.selected_unit = self.model.unit
        self.selected_scope = "current"  # "current" or "all"

        self.setWindowTitle("環境設定")
        self.setFixedSize(450, 480)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
            }
            QLabel {
                color: #ffffff;
                border: none;
            }
            QTabWidget::pane {
                border: 1px solid #333344;
                background-color: #1e1e2d;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #151521;
                color: #888899;
                border: 1px solid #333344;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #1e1e2d;
                color: #ffffff;
                border-bottom: 2px solid #7c4dff;
            }
            QTabBar::tab:hover {
                background-color: #242438;
            }
            QGroupBox {
                border: 1px solid #333344;
                border-radius: 6px;
                margin-top: 12px;
                font-weight: bold;
                color: #aaaacc;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QRadioButton {
                color: #ffffff;
                font-size: 12px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #555577;
                border-radius: 9px;
                background-color: #2a2a3d;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #ffffff;
                background-color: #7c4dff;
            }
            QRadioButton::indicator:hover {
                border-color: #7c4dff;
            }
        """)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Tab Widget
        self.tabs = QTabWidget()
        self.tab_general = QWidget()
        self.tab_calibration = QWidget()

        self._setup_general_tab()
        self._setup_calibration_tab()

        self.tabs.addTab(self.tab_general, "全般（単位設定）")
        self.tabs.addTab(self.tab_calibration, "キャリブレーション")
        layout.addWidget(self.tabs)

        # Standard dialog buttons (OK / Cancel)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.setStyleSheet("""
            QPushButton {
                background-color: #2a2a3d;
                color: #ffffff;
                border: 1px solid #555566;
                border-radius: 4px;
                padding: 6px 20px;
            }
            QPushButton:hover {
                background-color: #7c4dff;
                border-color: #7c4dff;
            }
        """)
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _setup_general_tab(self):
        layout = QVBoxLayout(self.tab_general)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("表示単位を選択してください")
        title.setStyleSheet("font-size: 13px; color: #aaaacc; font-weight: bold;")
        layout.addWidget(title)

        def _card_style(active):
            border = "#7c4dff" if active else "#333355"
            bg = "#2e2e45" if active else "#1e1e2e"
            return f"QFrame {{ background-color: {bg}; border: 2px solid {border}; border-radius: 8px; }}"

        # Create Unit Selection Cards
        self.m_card = QFrame()
        self.m_card.setStyleSheet(_card_style(self.selected_unit == 'm'))
        self.m_card.setCursor(Qt.PointingHandCursor)
        m_layout = QHBoxLayout(self.m_card)
        m_layout.setContentsMargins(15, 12, 15, 12)
        m_text_col = QVBoxLayout()
        m_lbl = QLabel("m (メートル)")
        m_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        m_desc = QLabel("土木・建築図面の広範囲な計測に適しています。")
        m_desc.setStyleSheet("font-size: 11px; color: #888899;")
        m_text_col.addWidget(m_lbl)
        m_text_col.addWidget(m_desc)
        m_layout.addLayout(m_text_col)
        m_layout.addStretch()
        self.m_check = QLabel("✓" if self.selected_unit == 'm' else "")
        self.m_check.setStyleSheet("font-size: 20px; font-weight: bold; color: #7c4dff;")
        m_layout.addWidget(self.m_check)

        self.mm_card = QFrame()
        self.mm_card.setStyleSheet(_card_style(self.selected_unit == 'mm'))
        self.mm_card.setCursor(Qt.PointingHandCursor)
        mm_layout = QHBoxLayout(self.mm_card)
        mm_layout.setContentsMargins(15, 12, 15, 12)
        mm_text_col = QVBoxLayout()
        mm_lbl = QLabel("mm (ミリメートル)")
        mm_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        mm_desc = QLabel("詳細設計図面や、高精度な計測に適しています。")
        mm_desc.setStyleSheet("font-size: 11px; color: #888899;")
        mm_text_col.addWidget(mm_lbl)
        mm_text_col.addWidget(mm_desc)
        mm_layout.addLayout(mm_text_col)
        mm_layout.addStretch()
        self.mm_check = QLabel("✓" if self.selected_unit == 'mm' else "")
        self.mm_check.setStyleSheet("font-size: 20px; font-weight: bold; color: #7c4dff;")
        mm_layout.addWidget(self.mm_check)

        # Mouse click events to toggle unit selection
        def select_m(event):
            self.selected_unit = 'm'
            self.m_card.setStyleSheet(_card_style(True))
            self.m_check.setText("✓")
            self.mm_card.setStyleSheet(_card_style(False))
            self.mm_check.setText("")

        def select_mm(event):
            self.selected_unit = 'mm'
            self.m_card.setStyleSheet(_card_style(False))
            self.m_check.setText("")
            self.mm_card.setStyleSheet(_card_style(True))
            self.mm_check.setText("✓")

        self.m_card.mousePressEvent = select_m
        self.mm_card.mousePressEvent = select_mm

        layout.addWidget(self.m_card)
        layout.addWidget(self.mm_card)
        layout.addStretch()

    def _setup_calibration_tab(self):
        layout = QVBoxLayout(self.tab_calibration)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # 1. Current Calibration Status
        self.status_group = QGroupBox("現在のキャリブレーション状態")
        status_layout = QVBoxLayout(self.status_group)
        status_layout.setContentsMargins(12, 12, 12, 12)
        
        self.lbl_current_page_status = QLabel("現在のページ: 未設定")
        self.lbl_current_page_status.setStyleSheet("font-size: 12px; color: #ffffff;")
        status_layout.addWidget(self.lbl_current_page_status)
        
        layout.addWidget(self.status_group)

        # 2. Calibration Scope (Current vs All)
        self.scope_group = QGroupBox("適用範囲設定")
        scope_layout = QHBoxLayout(self.scope_group)
        scope_layout.setContentsMargins(15, 12, 15, 12)
        
        self.rad_scope_current = QRadioButton("現在のページのみに適用")
        self.rad_scope_all = QRadioButton("すべてのページに適用")
        self.rad_scope_current.setChecked(True)
        
        scope_layout.addWidget(self.rad_scope_current)
        scope_layout.addWidget(self.rad_scope_all)
        
        layout.addWidget(self.scope_group)

        # 3. Calibration Methods
        self.method_group = QGroupBox("キャリブレーション方法の選択")
        method_layout = QVBoxLayout(self.method_group)
        method_layout.setContentsMargins(15, 15, 15, 15)
        method_layout.setSpacing(12)

        # Method A: 1/N Ratio Input
        ratio_title = QLabel("方法A: 縮尺比率 (1/N) を直接入力")
        ratio_title.setStyleSheet("font-weight: bold; color: #7c4dff;")
        method_layout.addWidget(ratio_title)

        h_ratio_layout = QHBoxLayout()
        lbl_one_over = QLabel("縮尺比率 =  1 / ")
        lbl_one_over.setStyleSheet("font-size: 14px; font-weight: bold;")
        h_ratio_layout.addWidget(lbl_one_over)

        self.ratio_combo = QComboBox()
        self.ratio_combo.setEditable(True)
        self.ratio_combo.addItems(["10", "20", "30", "50", "100", "200", "250", "300", "500", "600", "1000"])
        self.ratio_combo.setCurrentText("100")
        self.ratio_combo.setStyleSheet("""
            QComboBox {
                background-color: #2a2a3d;
                border: 1px solid #3d3d5c;
                border-radius: 4px;
                padding: 4px 10px;
                color: white;
                font-size: 14px;
                font-weight: bold;
                min-width: 100px;
            }
        """)
        h_ratio_layout.addWidget(self.ratio_combo)
        
        self.btn_apply_ratio = QPushButton("比率を適用")
        self.btn_apply_ratio.setStyleSheet("""
            QPushButton {
                background-color: #7c4dff;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #966eff;
            }
        """)
        self.btn_apply_ratio.clicked.connect(self._apply_ratio_calibration)
        h_ratio_layout.addWidget(self.btn_apply_ratio)
        method_layout.addLayout(h_ratio_layout)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        sep.setStyleSheet("background-color: #333344; max-height: 1px; border: none; margin: 5px 0;")
        method_layout.addWidget(sep)

        # Method B: 2-Point Selection
        twopt_title = QLabel("方法B: 図面上の2点間で指定")
        twopt_title.setStyleSheet("font-weight: bold; color: #7c4dff;")
        method_layout.addWidget(twopt_title)

        self.btn_canvas_calib = QPushButton("図面上で2点を指定してキャリブレーションを開始")
        self.btn_canvas_calib.setStyleSheet("""
            QPushButton {
                background-color: #2a2a3d;
                border: 1px solid #3d3d5c;
                border-radius: 4px;
                padding: 8px;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d3d5c;
                border-color: #7c4dff;
            }
        """)
        self.btn_canvas_calib.clicked.connect(self._start_canvas_calibration)
        method_layout.addWidget(self.btn_canvas_calib)

        layout.addWidget(self.method_group)
        layout.addStretch()

        self._update_status_display()

    def _update_status_display(self):
        # Update current calibration status text
        is_calibrated = self.model.is_page_calibrated(self.current_page)
        if is_calibrated:
            scale_factor = self.model.get_scale_factor(self.current_page)
            ratio_text = self._format_scale_ratio(scale_factor)
            status_str = f"現在のページ (P.{self.current_page + 1}): キャリブレーション済み ({ratio_text})"
        else:
            status_str = f"現在のページ (P.{self.current_page + 1}): 未キャリブレーション"
        self.lbl_current_page_status.setText(status_str)

    def _format_scale_ratio(self, scale_factor):
        mm_per_pixel_on_pdf = 25.4 / self.dpi
        if scale_factor <= 0 or mm_per_pixel_on_pdf <= 0:
            return ""
        ratio = scale_factor / mm_per_pixel_on_pdf
        rounded = round(ratio)
        if abs(ratio - rounded) < 0.05:
            return f"1/{rounded}"
        return f"1/{ratio:.1f}"

    def _apply_ratio_calibration(self):
        ratio_str = self.ratio_combo.currentText().strip()
        try:
            ratio_denominator = float(ratio_str)
        except ValueError:
            QMessageBox.critical(self, "エラー", "縮尺比率の分母には有効な数値を入力してください。")
            return

        if ratio_denominator <= 0:
            QMessageBox.critical(self, "エラー", "縮尺比率は0より大きい数値を入力してください。")
            return

        all_pages = self.rad_scope_all.isChecked()
        
        success = self.model.set_calibration_by_ratio(
            ratio_denominator,
            dpi=self.dpi,
            page_num=self.current_page,
            all_pages=all_pages,
            total_pages=self.total_pages
        )

        if success:
            QMessageBox.information(self, "完了", "縮尺比率によるキャリブレーションを適用しました。")
            self._update_status_display()
            self.settings_updated.emit()
        else:
            QMessageBox.critical(self, "エラー", "キャリブレーションの適用に失敗しました。")

    def _start_canvas_calibration(self):
        all_pages = self.rad_scope_all.isChecked()
        self.trigger_canvas_calibration.emit(all_pages)

    def _on_accept(self):
        # Apply Unit Change if changed
        if self.selected_unit != self.model.unit:
            self.main_window._apply_unit_change(self.selected_unit)
            self.settings_updated.emit()
        self.accept()
