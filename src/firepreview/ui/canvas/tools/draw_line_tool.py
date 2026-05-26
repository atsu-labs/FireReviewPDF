from PySide6.QtCore import Qt, QPointF
from PySide6.QtWidgets import QGraphicsPathItem
from PySide6.QtGui import QPen, QColor, QPainterPath
from .base_tool import BaseCanvasTool
from ..utils import apply_angle_snap

class DrawLineTool(BaseCanvasTool):
    def mouse_press(self, event, scene):
        pos = self.canvas.mapToScene(event.pos())

        if event.button() == Qt.LeftButton:
            # Shift snap
            snap_pos = pos
            if (event.modifiers() & Qt.ShiftModifier) and self.canvas.temp_points:
                snap_pos = apply_angle_snap(self.canvas.temp_points[-1], pos)
            
            self.canvas.temp_points.append(snap_pos)
            
            if not self.canvas.temp_poly:
                self.canvas.temp_poly = QGraphicsPathItem()
                pen = QPen(QColor(self.canvas.current_shape_color), self.canvas.current_shape_line_width)
                pen.setCosmetic(True)
                self.canvas.temp_poly.setPen(pen)
                scene.addItem(self.canvas.temp_poly)
                
            self._update_temp_polyline_path()
            return True

        elif event.button() == Qt.RightButton:
            if len(self.canvas.temp_points) >= 2:
                from ..canvas import ToolMode  # Late import to prevent circular issues
                self.canvas.polyline_complete.emit(self.canvas.temp_points[:])
                self.canvas._finish_tool(ToolMode.DRAW_LINE if self.canvas.continuous_shape else ToolMode.SELECT)
            return True

        return False

    def mouse_move(self, event, scene):
        pos = self.canvas.mapToScene(event.pos())
        shift_held = bool(event.modifiers() & Qt.ShiftModifier)

        if self.canvas.temp_poly and len(self.canvas.temp_points) >= 1:
            preview_pos = apply_angle_snap(self.canvas.temp_points[-1], pos) if shift_held else pos
            self._update_temp_polyline_path(preview_end=preview_pos)
            return True
        return False

    def double_click(self, event, scene):
        if event.button() == Qt.LeftButton:
            if len(self.canvas.temp_points) >= 2:
                self.canvas.temp_points.pop()  # Pop the extra double-click click
            if len(self.canvas.temp_points) >= 2:
                from ..canvas import ToolMode
                self.canvas.polyline_complete.emit(self.canvas.temp_points[:])
                self.canvas._finish_tool(ToolMode.DRAW_LINE if self.canvas.continuous_shape else ToolMode.SELECT)
            return True
        return False

    def _update_temp_polyline_path(self, preview_end=None):
        if not self.canvas.temp_poly or not self.canvas.temp_points:
            return
        path = QPainterPath()
        path.moveTo(self.canvas.temp_points[0])
        for pt in self.canvas.temp_points[1:]:
            path.lineTo(pt)
        if preview_end:
            path.lineTo(preview_end)
        self.canvas.temp_poly.setPath(path)
