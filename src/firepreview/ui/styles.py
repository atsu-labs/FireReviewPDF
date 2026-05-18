GLOBAL_STYLE = """
QMainWindow {
    background-color: #151521;
}

QWidget {
    background-color: #1e1e2d;
    color: #ffffff;
    font-family: 'Inter', 'Segoe UI', sans-serif;
}

QDockWidget {
    titlebar-close-icon: url(close.png);
    titlebar-normal-icon: url(undock.png);
    border: none;
}

QDockWidget::title {
    background-color: #1e1e2d;
    padding: 10px;
    font-weight: bold;
}

/* Header and Toolbars */
#MainHeader {
    background-color: #151521;
    border-bottom: 1px solid #333344;
}

#ToolBar, #ToolOptionsBar {
    background-color: #1e1e2d;
    border-bottom: 1px solid #333344;
    min-height: 45px;
}

/* Buttons */
QPushButton {
    background-color: #2a2a3d;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    color: #ffffff;
}

QPushButton:hover {
    background-color: #3d3d5c;
}

QPushButton:pressed {
    background-color: #7c4dff;
}

#ToolBtn {
    background-color: transparent;
    border-radius: 4px;
    padding: 8px;
    font-size: 18px;
}

#ToolBtn:hover {
    background-color: #2a2a3d;
}

#ToolBtn[active="true"] {
    background-color: #7c4dff;
    color: white;
}

/* ScrollArea */
QScrollArea {
    border: none;
    background-color: transparent;
}

/* Labels */
QLabel {
    background: transparent;
}

/* LineEdit and SpinBox */
QLineEdit, QSpinBox, QFontComboBox {
    background-color: #2a2a3d;
    border: 1px solid #3d3d5c;
    border-radius: 4px;
    padding: 4px;
    color: white;
}

QSlider::groove:horizontal {
    border: 1px solid #3d3d5c;
    height: 4px;
    background: #2a2a3d;
    margin: 2px 0;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #7c4dff;
    border: none;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
"""
