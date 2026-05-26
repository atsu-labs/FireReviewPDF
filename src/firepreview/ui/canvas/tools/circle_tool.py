import math
from PySide6.QtCore import Qt, QPointF
from PySide6.QtWidgets import QGraphicsEllipseItem
from PySide6.QtGui import QPen, QColor
from .base_tool import BaseCanvasTool

class CircleTool(BaseCanvasTool):
    def mouse_press(self, event, scene):
        pos = self.canvas.mapToScene(event.pos())
        if event.button() == Qt.LeftButton:
            self.canvas.drag_start = pos
            return True
        return False

    def mouse_move(self, event, scene):
        pos = self.canvas.mapToScene(event.pos())

        if self.canvas.drag_start:
            radius = math.sqrt((pos.x() - self.canvas.drag_start.x()) ** 2 + (pos.y() - self.canvas.drag_start.y()) ** 2)
            if self.canvas.temp_circle:
                scene.removeItem(self.canvas.temp_circle)
                
            cx, cy = self.canvas.drag_start.x(), self.canvas.drag_start.y()
            self.canvas.temp_circle = QGraphicsEllipseItem(cx - radius, cy - radius, radius * 2, radius * 2)
            
            pen = QPen(QColor(self.canvas.current_shape_color), self.canvas.current_shape_line_width)
            pen.setCosmetic(True)
            self.canvas.temp_circle.setPen(pen)
            
            if self.canvas.current_fill_color:
                fill = QColor(self.canvas.current_fill_color)
                fill.setAlpha(50)
                self.canvas.temp_circle.setBrush(fill)
                
            scene.addItem(self.canvas.temp_circle)
            return True
        return False

    def mouse_release(self, event, scene):
        if event.button() == Qt.LeftButton and self.canvas.drag_start:
            pos = self.canvas.mapToScene(event.pos())
            radius = math.sqrt((pos.x() - self.canvas.drag_start.x()) ** 2 + (pos.y() - self.canvas.drag_start.y()) ** 2)
            center = self.canvas.drag_start
            self.canvas.drag_start = None
            
            if self.canvas.temp_circle:
                scene.removeItem(self.canvas.temp_circle)
                self.canvas.temp_circle = None
                
            from .. import ToolMode
            self.canvas.circle_drag_complete.emit(center, radius)
            self.canvas._finish_tool(ToolMode.DRAW_CIRCLE_DRAG if self.canvas.continuous_shape else ToolMode.SELECT)
            return True
        return False
