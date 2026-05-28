from PySide6.QtCore import Qt
from .base_tool import BaseCanvasTool

class LegendTool(BaseCanvasTool):
    def mouse_press(self, event, scene):
        pos = self.canvas.mapToScene(event.pos())

        if event.button() == Qt.LeftButton:
            if hasattr(self.canvas, "legend_complete"):
                self.canvas.legend_complete.emit(pos)
            return True

        return False
