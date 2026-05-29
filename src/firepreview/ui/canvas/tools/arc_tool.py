import math
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtWidgets import QGraphicsPathItem
from PySide6.QtGui import QPen, QColor, QPainterPath
from .base_tool import BaseCanvasTool
from ..enums import ToolMode

class ArcTool(BaseCanvasTool):
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
            if radius < 1:
                return True
                
            drag_angle = math.degrees(math.atan2(pos.y() - self.canvas.drag_start.y(), pos.x() - self.canvas.drag_start.x()))
            
            path = QPainterPath()
            cx, cy = self.canvas.drag_start.x(), self.canvas.drag_start.y()
            rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
            
            span = getattr(self.canvas, 'current_arc_span', 30.0)
            start_angle = -drag_angle - span / 2.0
            
            path.arcMoveTo(rect, start_angle)
            path.arcTo(rect, start_angle, span)
            
            if getattr(self.canvas, 'current_arc_show_radial_line', False):
                path.moveTo(self.canvas.drag_start)
                mid_rad = math.radians(drag_angle)
                mid_pt = QPointF(cx + radius * math.cos(mid_rad), cy + radius * math.sin(mid_rad))
                path.lineTo(mid_pt)

            if hasattr(self.canvas, 'temp_arc') and self.canvas.temp_arc:
                self.canvas.temp_arc.setPath(path)
            else:
                self.canvas.temp_arc = QGraphicsPathItem(path)
                pen = QPen(QColor(self.canvas.current_shape_color), self.canvas.current_shape_line_width)
                pen.setCosmetic(True)
                self.canvas.temp_arc.setPen(pen)
                self.canvas.temp_arc.setBrush(Qt.NoBrush)
                scene.addItem(self.canvas.temp_arc)
            return True
        return False

    def mouse_release(self, event, scene):
        if event.button() == Qt.LeftButton and self.canvas.drag_start:
            pos = self.canvas.mapToScene(event.pos())
            radius = math.sqrt((pos.x() - self.canvas.drag_start.x()) ** 2 + (pos.y() - self.canvas.drag_start.y()) ** 2)
            center = self.canvas.drag_start
            self.canvas.drag_start = None
            
            if hasattr(self.canvas, 'temp_arc') and self.canvas.temp_arc:
                try:
                    scene.removeItem(self.canvas.temp_arc)
                except RuntimeError:
                    pass
                self.canvas.temp_arc = None
                
            if radius >= 3:
                drag_angle = math.degrees(math.atan2(pos.y() - center.y(), pos.x() - center.x()))
                self.canvas.arc_drag_complete.emit(center, radius, drag_angle)
                
            self.canvas._finish_tool(ToolMode.DRAW_ARC if self.canvas.continuous_shape else ToolMode.SELECT)
            return True
        return False
