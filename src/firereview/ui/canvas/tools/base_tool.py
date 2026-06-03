from PySide6.QtCore import Qt

class BaseCanvasTool:
    def __init__(self, canvas):
        self.canvas = canvas  # PDFCanvas instance

    def mouse_press(self, event, scene):
        pass

    def mouse_move(self, event, scene):
        pass

    def mouse_release(self, event, scene):
        pass

    def double_click(self, event, scene):
        pass

    def draw_foreground(self, painter, rect, scene):
        pass
