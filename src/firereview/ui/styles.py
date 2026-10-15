import os
import sys


def _asset(filename: str) -> str:
    """アセットファイルの絶対パスを返す（Qt stylesheet 用にスラッシュに統一）"""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_dir = os.path.join(sys._MEIPASS, "firereview", "ui", "assets")
        return os.path.join(base_dir, filename).replace("\\", "/")
    return os.path.join(os.path.dirname(__file__), "assets", filename).replace("\\", "/")


def _build_style() -> str:
    up_arrow = _asset("arrow_up.svg")
    down_arrow = _asset("arrow_down.svg")
    check_icon = _asset("check.svg")
    return f"""
QMainWindow {{
    background-color: #151521;
}}

QWidget {{
    background-color: #1e1e2d;
    color: #ffffff;
    font-family: 'Inter', 'Segoe UI', sans-serif;
}}

QDockWidget {{
    titlebar-close-icon: url(close.png);
    titlebar-normal-icon: url(undock.png);
    border: none;
}}

QDockWidget::title {{
    background-color: #1e1e2d;
    padding: 10px;
    font-weight: bold;
}}

/* Header and Toolbars */
#MainHeader {{
    background-color: #151521;
    border-bottom: 1px solid #333344;
}}

#ToolBar, #ToolOptionsBar {{
    background-color: #1e1e2d;
    border-bottom: 1px solid #333344;
    min-height: 45px;
}}

/* Buttons */
QPushButton {{
    background-color: #2a2a3d;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    color: #ffffff;
}}

QPushButton:hover {{
    background-color: #3d3d5c;
}}

QPushButton:pressed {{
    background-color: #7c4dff;
}}

#ToolBtn {{
    background-color: transparent;
    border-radius: 4px;
    padding: 8px;
    font-size: 18px;
}}

#ToolBtn:hover {{
    background-color: #2a2a3d;
}}

#ToolBtn[active="true"] {{
    background-color: #7c4dff;
    color: white;
}}

/* ScrollArea */
QScrollArea {{
    border: none;
    background-color: transparent;
}}

/* Labels */
QLabel {{
    background: transparent;
}}

/* LineEdit and SpinBox */
QLineEdit, QSpinBox, QDoubleSpinBox, QFontComboBox, QComboBox {{
    background-color: #2a2a3d;
    border: 1px solid #3d3d5c;
    border-radius: 4px;
    padding: 4px;
    color: white;
}}

/* SpinBox ボタンを縦並び（右側上下）に固定 */
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 18px;
    border-left: 1px solid #3d3d5c;
    border-bottom: 1px solid #3d3d5c;
    border-top-right-radius: 4px;
    background-color: #2a2a3d;
}}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
    background-color: #3d3d5c;
}}

QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed {{
    background-color: #7c4dff;
}}

QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 18px;
    border-left: 1px solid #3d3d5c;
    border-bottom-right-radius: 4px;
    background-color: #2a2a3d;
}}

QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: #3d3d5c;
}}

QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {{
    background-color: #7c4dff;
}}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url("{up_arrow}");
    width: 8px;
    height: 8px;
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url("{down_arrow}");
    width: 8px;
    height: 8px;
}}

/* ComboBox ドロップダウンボタン */
/* ComboBox ドロップダウンボタン */
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #3d3d5c;
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
    background-color: #2a2a3d;
}}

QComboBox::down-arrow {{
    image: url("{down_arrow}");
    width: 10px;
    height: 10px;
}}
QComboBox::drop-down:hover {{
    background-color: #3d3d5c;
}}

QComboBox QAbstractItemView {{
    background-color: #2a2a3d;
    border: 1px solid #3d3d5c;
    selection-background-color: #7c4dff;
    color: white;
}}

QSlider::groove:horizontal {{
    border: 1px solid #3d3d5c;
    height: 4px;
    background: #2a2a3d;
    margin: 2px 0;
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: #7c4dff;
    border: none;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}

/* RadioButton */
QRadioButton {{
    color: #ffffff;
    font-size: 12px;
    spacing: 8px;
}}

QRadioButton:hover {{
    color: #ffffff;
}}

QRadioButton:disabled {{
    color: #666677;
}}

QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 9px;
    border: 2px solid #777799;
    background-color: #242436;
}}

QRadioButton::indicator:hover {{
    border-color: #9999cc;
}}

QRadioButton::indicator:checked {{
    border: 2px solid #7c4dff;
    background-color: qradialgradient(cx: 0.5, cy: 0.5, radius: 0.5, fx: 0.5, fy: 0.5, stop: 0 #7c4dff, stop: 0.55 #7c4dff, stop: 0.6 transparent, stop: 1 transparent);
}}

QRadioButton::indicator:disabled {{
    border: 2px solid #444455;
    background-color: #1a1a26;
}}

/* CheckBox */
QCheckBox {{
    color: #ffffff;
    font-size: 12px;
    spacing: 8px;
}}

QCheckBox:hover {{
    color: #ffffff;
}}

QCheckBox:disabled {{
    color: #666677;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 2px solid #777799;
    background-color: #242436;
}}

QCheckBox::indicator:hover {{
    border-color: #9999cc;
}}

QCheckBox::indicator:checked {{
    border: 2px solid #7c4dff;
    background-color: #7c4dff;
    image: url("{check_icon}");
}}

QCheckBox::indicator:disabled {{
    border: 2px solid #444455;
    background-color: #1a1a26;
}}
"""


GLOBAL_STYLE = _build_style()
