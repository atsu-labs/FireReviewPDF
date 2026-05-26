from PySide6.QtWidgets import QGraphicsTextItem, QGraphicsEllipseItem, QGraphicsItem
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QPen, QColor

class CustomTextItem(QGraphicsTextItem):
    editing_finished = Signal(str)
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        
    def mouseDoubleClickEvent(self, event):
        if self.flags() & QGraphicsItem.ItemIsSelectable:
            self.setTextInteractionFlags(Qt.TextEditorInteraction)
            self.setFocus()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.editing_finished.emit(self.toPlainText())

class VertexHandleItem(QGraphicsEllipseItem):
    def __init__(self, parent_item, index, canvas, size=8):
        scale = canvas.transform().m11()
        s = size / scale if scale > 0 else size
        super().__init__(-s/2, -s/2, s, s, parent_item)
        self.parent_item = parent_item
        self.index = index
        self.canvas = canvas
        self.size = size
        self.is_dragging = False
        
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        
        self.setBrush(QColor("#7c4dff"))
        pen = QPen(QColor("#ffffff"), 1.5 / scale if scale > 0 else 1.5)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setZValue(100)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            new_pos = value
            self.canvas.on_vertex_moved(self.parent_item, self.index, new_pos)
            self.is_dragging = True
        return super().itemChange(change, value)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self.is_dragging:
            self.is_dragging = False
            self.canvas.on_vertex_move_finished(self.parent_item)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.canvas.on_vertex_double_clicked(self.parent_item, self.index)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)
