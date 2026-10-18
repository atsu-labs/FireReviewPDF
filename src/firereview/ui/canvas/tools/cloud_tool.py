from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPen, QColor
from .base_tool import BaseCanvasTool
from ..items import CloudItem
from ..enums import ToolMode


class CloudTool(BaseCanvasTool):
    """矩形ドラッグにより雲マーク（クラウド注釈）を描画するツール"""

    MIN_DRAG_SIZE = 5.0

    @staticmethod
    def _make_rect_points(start: QPointF, end: QPointF, shift_held: bool = False) -> list[QPointF]:
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        if shift_held:
            size = max(abs(dx), abs(dy))
            sx = 1.0 if dx >= 0 else -1.0
            sy = 1.0 if dy >= 0 else -1.0
            end = QPointF(start.x() + sx * size, start.y() + sy * size)

        x1 = min(start.x(), end.x())
        x2 = max(start.x(), end.x())
        y1 = min(start.y(), end.y())
        y2 = max(start.y(), end.y())
        return [
            QPointF(x1, y1),
            QPointF(x2, y1),
            QPointF(x2, y2),
            QPointF(x1, y2),
        ]

    def mouse_press(self, event, scene):
        if event.button() == Qt.LeftButton:
            self.canvas.drag_start = self.canvas.mapToScene(event.pos())
            return True
        return False

    def mouse_move(self, event, scene):
        if not self.canvas.drag_start:
            return False

        pos = self.canvas.mapToScene(event.pos())
        shift_held = bool(event.modifiers() & Qt.ShiftModifier)
        pts = self._make_rect_points(self.canvas.drag_start, pos, shift_held)
        w = abs(pts[1].x() - pts[0].x())
        h = abs(pts[2].y() - pts[1].y())

        if w < self.MIN_DRAG_SIZE or h < self.MIN_DRAG_SIZE:
            if getattr(self.canvas, "temp_cloud", None):
                scene.removeItem(self.canvas.temp_cloud)
                self.canvas.temp_cloud = None
            return True

        if not getattr(self.canvas, "temp_cloud", None):
            self.canvas.temp_cloud = CloudItem(pts)
            pen = QPen(QColor(self.canvas.current_shape_color), self.canvas.current_shape_line_width)
            pen.setCosmetic(True)
            self.canvas.temp_cloud.setPen(pen)

            fill_opacity = getattr(self.canvas, "current_fill_opacity", 0)
            if fill_opacity > 0:
                fill_color_str = self.canvas.current_fill_color or self.canvas.current_shape_color
                fill = QColor(fill_color_str)
                fill.setAlpha(round(fill_opacity / 100.0 * 255))
                self.canvas.temp_cloud.setBrush(fill)
            else:
                self.canvas.temp_cloud.setBrush(Qt.NoBrush)

            scene.addItem(self.canvas.temp_cloud)
        else:
            self.canvas.temp_cloud.set_points(pts)

        return True

    def mouse_release(self, event, scene):
        if event.button() == Qt.LeftButton and self.canvas.drag_start:
            pos = self.canvas.mapToScene(event.pos())
            shift_held = bool(event.modifiers() & Qt.ShiftModifier)
            pts = self._make_rect_points(self.canvas.drag_start, pos, shift_held)
            w = abs(pts[1].x() - pts[0].x())
            h = abs(pts[2].y() - pts[1].y())
            self.canvas.drag_start = None

            if getattr(self.canvas, "temp_cloud", None):
                scene.removeItem(self.canvas.temp_cloud)
                self.canvas.temp_cloud = None

            if w >= self.MIN_DRAG_SIZE and h >= self.MIN_DRAG_SIZE:
                self.canvas.cloud_complete.emit(pts)
                self.canvas._finish_tool(
                    ToolMode.DRAW_CLOUD if self.canvas.continuous_shape else ToolMode.SELECT
                )
            return True
        return False
