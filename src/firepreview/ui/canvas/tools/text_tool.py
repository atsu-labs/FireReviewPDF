from PySide6.QtCore import Qt
from .base_tool import BaseCanvasTool

class TextTool(BaseCanvasTool):
    def mouse_press(self, event, scene):
        pos = self.canvas.mapToScene(event.pos())

        if event.button() == Qt.LeftButton:
            item = scene.itemAt(pos, self.canvas.transform())
            if item == self.canvas.editing_text_item:
                return False  # Let parent class process click
            
            if self.canvas.editing_text_item:
                self.canvas.editing_text_item.clearFocus()
                if not self.canvas.continuous_text_input:
                    return False
                    
            self.canvas._start_inline_text_editing(pos)
            return False  # Return False to let default QGraphicsView processing proceed

        return False
