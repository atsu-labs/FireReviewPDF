from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsLineItem
from PySide6.QtGui import QPen, QColor
from .base_tool import BaseCanvasTool
from ..utils import apply_angle_snap

class CalibrationTool(BaseCanvasTool):
    def mouse_press(self, event, scene):
        pos = self.canvas.mapToScene(event.pos())

        if event.button() == Qt.LeftButton:
            self.canvas.temp_points.append(pos)
            if len(self.canvas.temp_points) == 1:
                self.canvas.temp_line = QGraphicsLineItem(pos.x(), pos.y(), pos.x(), pos.y())
                pen = QPen(QColor(124, 77, 255), 2)
                pen.setCosmetic(True)
                self.canvas.temp_line.setPen(pen)
                scene.addItem(self.canvas.temp_line)
            elif len(self.canvas.temp_points) == 2:
                p1, p2 = self.canvas.temp_points
                self.canvas.calibration_points_selected.emit(p1, p2)
                self.canvas._finish_tool()
            return True
        return False

    def mouse_move(self, event, scene):
        pos = self.canvas.mapToScene(event.pos())
        shift_held = bool(event.modifiers() & Qt.ShiftModifier)

        if self.canvas.temp_line and len(self.canvas.temp_points) == 1:
            preview_pos = apply_angle_snap(self.canvas.temp_points[0], pos) if shift_held else pos
            self.canvas.temp_line.setLine(self.canvas.temp_points[0].x(), self.canvas.temp_points[0].y(),
                                         preview_pos.x(), preview_pos.y())
            return True
        return False
