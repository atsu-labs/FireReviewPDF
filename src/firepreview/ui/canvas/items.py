from PySide6.QtWidgets import QGraphicsTextItem, QGraphicsEllipseItem, QGraphicsItem, QGraphicsLineItem
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QPen, QColor, QPainter, QPainterPath

class CustomTextItem(QGraphicsTextItem):
    editing_finished = Signal(str)
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.has_border = False
        self.border_color = QColor("#ff0000")
        self.border_width = 2
        
        self.has_leader = False
        self.leader_end_point = QPointF(0, 0)
        self.leader_line_item = None
        
        # Enable tracking position changes for dynamic connection line updates
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        
    def set_border(self, has_border, color=None, width=None):
        self.has_border = has_border
        if color:
            self.border_color = QColor(color)
        if width is not None:
            self.border_width = width
        self.update()
        self.update_leader_line()

    def set_leader(self, has_leader, end_point=None):
        self.has_leader = has_leader
        if end_point is not None:
            self.leader_end_point = end_point
            
        if self.has_leader:
            if not self.leader_line_item and self.scene():
                # Make QGraphicsLineItem a child of self (CustomTextItem)
                self.leader_line_item = QGraphicsLineItem(self)
                self.leader_line_item.setZValue(-1)
            
            self.update_leader_line()
        else:
            if self.leader_line_item:
                if self.scene():
                    self.scene().removeItem(self.leader_line_item)
                self.leader_line_item = None

    def update_leader_line(self):
        if not self.has_leader or not self.leader_line_item:
            return
            
        # Get bounding box and apply a visual margin to align with the border rectangle
        margin = 4
        rect = self.boundingRect().adjusted(-margin, -margin, margin, margin)
        
        # Check all 4 corners in local coordinates
        corners = [
            rect.topLeft(),
            rect.topRight(),
            rect.bottomLeft(),
            rect.bottomRight()
        ]
        
        # Map the scene-based leader end point to local coordinates
        local_end_pt = self.mapFromScene(self.leader_end_point)
        
        # Choose the corner closest to the leader end point (in local coordinates)
        best_pt = corners[0]
        min_dist = float('inf')
        for pt in corners:
            dx = pt.x() - local_end_pt.x()
            dy = pt.y() - local_end_pt.y()
            dist = dx * dx + dy * dy
            if dist < min_dist:
                min_dist = dist
                best_pt = pt
                
        # Set line coordinates in local coordinates
        self.leader_line_item.setLine(best_pt.x(), best_pt.y(), local_end_pt.x(), local_end_pt.y())
        
        pen = QPen(self.border_color, self.border_width)
        pen.setCosmetic(True)
        self.leader_line_item.setPen(pen)

    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        if self.has_border:
            painter.save()
            pen = QPen(self.border_color, self.border_width)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            # Draw border with a nice margin
            margin = 4
            rect = self.boundingRect().adjusted(-margin, -margin, margin, margin)
            painter.drawRect(rect)
            painter.restore()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.update_leader_line()
        return super().itemChange(change, value)

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
            scene_pos = self.parentItem().mapToScene(new_pos) if self.parentItem() else new_pos
            self.canvas.on_vertex_moved(self.parent_item, self.index, scene_pos)
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


class MarkerItem(QGraphicsItem):
    def __init__(self, marker_style="square", color="#7c4dff", opacity=100, parent=None):
        super().__init__(parent)
        self.marker_style = marker_style  # "square" or "check"
        self.color = QColor(color)
        self.opacity = opacity
        
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setZValue(50)  # High Z-value to sit on top of annotations

    def boundingRect(self):
        return QRectF(-14, -14, 28, 28)

    def paint(self, painter, option, widget=None):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Apply opacity
        c = QColor(self.color)
        c.setAlpha(round(self.opacity / 100.0 * 255))
        
        if self.marker_style == "square":
            # 1. White border/glow for contrast
            painter.setPen(QPen(QColor("#ffffff"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.setBrush(c)
            painter.drawRoundedRect(QRectF(-10, -10, 20, 20), 3, 3)
            
            # 2. Inside solid line border
            painter.setPen(QPen(c, 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(QRectF(-10, -10, 20, 20), 3, 3)
            
        elif self.marker_style == "check":
            # Round background disk for visibility
            bg_color = QColor("#ffffff")
            bg_color.setAlpha(220)
            painter.setPen(QPen(c, 1.5))
            painter.setBrush(bg_color)
            painter.drawEllipse(QRectF(-11, -11, 22, 22))
            
            # Checkmark path
            path = QPainterPath()
            path.moveTo(-6, 0)
            path.lineTo(-1.5, 4.5)
            path.lineTo(6, -3)
            
            pen = QPen(c, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)
            
        painter.restore()

