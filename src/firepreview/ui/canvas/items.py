from PySide6.QtWidgets import QGraphicsTextItem, QGraphicsEllipseItem, QGraphicsItem, QGraphicsLineItem
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QPen, QColor, QPainter, QPainterPath, QFont

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


class LegendItem(QGraphicsItem):
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.marker_counts = {}  # {(style, color): count}
        self.color_names = {}  # {color_hex: name}
        
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setZValue(40)  # High Z-value (sits below handles/markers, above normal annotations)

    def update_data(self, marker_counts, color_names):
        self.prepareGeometryChange()
        self.marker_counts = marker_counts
        self.color_names = color_names
        self.update()

    def get_items_to_draw(self):
        return sorted(self.marker_counts.items(), key=lambda x: x[1], reverse=True)

    def boundingRect(self):
        items = self.get_items_to_draw()
        h = 32 + max(1, len(items)) * 30 + 10
        return QRectF(0, 0, 200, h)

    def paint(self, painter, option, widget=None):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        
        items = self.get_items_to_draw()
        rect = self.boundingRect()
        
        # 1. Glassmorphism Light Background: semi-transparent off-white/light gray
        bg_color = QColor("#f5f6f8")
        bg_color.setAlpha(240)  # semi-transparent
        
        # Draw background border and fill
        if self.isSelected():
            border_pen = QPen(QColor("#7c4dff"), 2)
        else:
            border_pen = QPen(QColor("#cccccc"), 1.2)
            
        border_pen.setCosmetic(True)
        painter.setPen(border_pen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(rect, 8, 8)
        
        # 2. Draw Title: "凡例" (Brand purple accent)
        painter.setPen(QColor("#7c4dff"))
        font_title = painter.font()
        font_title.setPointSize(11)
        font_title.setBold(True)
        painter.setFont(font_title)
        painter.drawText(QRectF(15, 5, 150, 20), Qt.AlignLeft | Qt.AlignVCenter, "凡例")
        
        # Draw a thin light gray separator line below title
        painter.setPen(QPen(QColor("#dcdde1"), 1))
        painter.drawLine(15, 26, 185, 26)
        
        # 3. Draw Items
        font_item = painter.font()
        font_item.setPointSize(9)
        font_item.setBold(False)
        painter.setFont(font_item)
        
        y_offset = 32
        
        if not items:
            painter.setPen(QColor("#888899"))
            painter.drawText(QRectF(15, y_offset, 150, 20), Qt.AlignLeft | Qt.AlignVCenter, "マーカーなし")
        else:
            default_color_names = {
                "#ff1744": "赤", "#2979ff": "青", "#00e676": "緑", "#ffd600": "黄", 
                "#ff9100": "橙", "#f50057": "桃", "#d500f9": "紫", "#8d6e63": "茶", 
                "#00e5ff": "水色", "#aeea00": "黄緑", "#7c4dff": "紫"
            }
            
            for (style, col), count in items:
                # A. Draw marker icon (at exactly the same size as actual canvas markers)
                painter.save()
                # Center of the 30px row vertically, x=25 horizontally
                painter.translate(25, y_offset + 12)
                c = QColor(col)
                
                if style == "square":
                    painter.setPen(QPen(QColor("#ffffff"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                    painter.setBrush(c)
                    painter.drawRoundedRect(QRectF(-10, -10, 20, 20), 3, 3)
                    
                    # Inside solid border
                    painter.setPen(QPen(c, 2))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawRoundedRect(QRectF(-10, -10, 20, 20), 3, 3)
                    
                elif style == "check":
                    bg_disk = QColor("#ffffff")
                    bg_disk.setAlpha(220)
                    painter.setPen(QPen(c, 1.5))
                    painter.setBrush(bg_disk)
                    painter.drawEllipse(QRectF(-11, -11, 22, 22))
                    
                    path = QPainterPath()
                    path.moveTo(-6, 0)
                    path.lineTo(-1.5, 4.5)
                    path.lineTo(6, -3)
                    pen = QPen(c, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                    painter.setPen(pen)
                    painter.setBrush(Qt.NoBrush)
                    painter.drawPath(path)
                    
                painter.restore()
                
                # B. Color name (Elided to fit the wider column)
                c_name = self.color_names.get(col.lower(), default_color_names.get(col.lower(), col.upper()))
                painter.setPen(QColor("#2a2a3d"))
                metrics = painter.fontMetrics()
                elided_name = metrics.elidedText(c_name, Qt.ElideRight, 115)
                # Centered vertically in the 30px row
                painter.drawText(QRectF(48, y_offset + 2, 115, 20), Qt.AlignLeft | Qt.AlignVCenter, elided_name)
                
                # C. Count
                painter.setPen(QColor("#2e7d32"))
                font_count = painter.font()
                font_count.setBold(True)
                painter.setFont(font_count)
                painter.drawText(QRectF(155, y_offset + 2, 30, 20), Qt.AlignRight | Qt.AlignVCenter, f"{count}")
                
                y_offset += 30

                
        painter.restore()



