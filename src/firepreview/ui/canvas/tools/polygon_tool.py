from PySide6.QtCore import Qt, QPointF
from PySide6.QtWidgets import QGraphicsPolygonItem
from PySide6.QtGui import QPen, QColor, QPolygonF
from .base_tool import BaseCanvasTool
from ..utils import apply_angle_snap
from ..enums import ToolMode

class PolygonTool(BaseCanvasTool):
    def mouse_press(self, event, scene):
        pos = self.canvas.mapToScene(event.pos())

        if event.button() == Qt.LeftButton:
            snap_pos = pos
            if (event.modifiers() & Qt.ShiftModifier) and self.canvas.temp_points:
                snap_pos = apply_angle_snap(self.canvas.temp_points[-1], pos)
                
            self.canvas.temp_points.append(snap_pos)
            
            if not self.canvas.temp_poly:
                self.canvas.temp_poly = QGraphicsPolygonItem()
                pen = QPen(QColor(self.canvas.current_shape_color), self.canvas.current_shape_line_width)
                pen.setCosmetic(True)
                self.canvas.temp_poly.setPen(pen)
                
                fill = QColor(self.canvas.current_fill_color) if self.canvas.current_fill_color else QColor(self.canvas.current_shape_color)
                fill.setAlpha(50)
                self.canvas.temp_poly.setBrush(fill)
                scene.addItem(self.canvas.temp_poly)
                
            self.canvas.temp_poly.setPolygon(QPolygonF(self.canvas.temp_points))
            return True

        elif event.button() == Qt.RightButton:
            if len(self.canvas.temp_points) >= 3:
                self.canvas.polygon_complete.emit(self.canvas.temp_points)
                self.canvas._finish_tool(ToolMode.POLYGON_AREA if self.canvas.continuous_shape else ToolMode.SELECT)
            return True

        return False

    def mouse_move(self, event, scene):
        pos = self.canvas.mapToScene(event.pos())
        shift_held = bool(event.modifiers() & Qt.ShiftModifier)

        if self.canvas.temp_poly and len(self.canvas.temp_points) >= 1:
            preview_pos = apply_angle_snap(self.canvas.temp_points[-1], pos) if shift_held else pos
            preview_points = self.canvas.temp_points + [preview_pos]
            self.canvas.temp_poly.setPolygon(QPolygonF(preview_points))
            return True
        return False
