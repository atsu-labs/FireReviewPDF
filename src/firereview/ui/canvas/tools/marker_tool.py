from PySide6.QtCore import Qt, QPointF
from .base_tool import BaseCanvasTool

class MarkerTool(BaseCanvasTool):
    def mouse_press(self, event, scene):
        pos = self.canvas.mapToScene(event.pos())

        if event.button() == Qt.LeftButton:
            if hasattr(self.canvas, "marker_complete"):
                self.canvas.marker_complete.emit(pos)
            return True

        return False
