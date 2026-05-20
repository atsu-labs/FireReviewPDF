from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsLineItem, QGraphicsTextItem, QGraphicsEllipseItem, QGraphicsPolygonItem, QGraphicsPathItem, QMenu, QGraphicsItem
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QPolygonF, QAction, QFont, QPainterPath
import math

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

class ToolMode:
    NONE = 0
    CALIBRATE = 1
    MEASURE_LINE = 2
    CIRCLE_FIXED = 3
    POLYGON_AREA = 4
    TEXT = 5
    SELECT = 6
    DRAW_LINE = 7       # Polyline drawing (no calibration required)
    DRAW_CIRCLE_DRAG = 8  # Circle by dragging center→radius (no calibration required)

class PDFCanvas(QGraphicsView):
    # 既定のベースズーム倍率（1.0 = 100%）
    DEFAULT_BASE_ZOOM = 1.0

    calibration_points_selected = Signal(QPointF, QPointF)
    measurement_complete = Signal(QPointF, QPointF)
    polygon_complete = Signal(list) # list of QPointF
    point_selected = Signal(QPointF) # For circle and text
    polyline_complete = Signal(list)  # list of QPointF for polyline tool
    circle_drag_complete = Signal(QPointF, float)  # center, radius_px
    
    # Selection/Editing signals
    item_selected = Signal(str) # id
    selection_cleared = Signal()
    item_moved = Signal(str, QPointF) # id, delta
    request_delete = Signal(str) # id
    request_tool_change = Signal(int) # next_mode
    zoom_changed = Signal(float)  # 表示倍率(%)
    
    text_editing_finished = Signal(QPointF, str, str, str, int, str) # pos, text, item_id, font_family, font_size, color
    existing_text_edited = Signal(str, str) # item_id, new_text

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # Performance settings
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        
        # Panning settings
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        
        self.background_item = None
        self.tool_mode = ToolMode.NONE
        
        # Interaction state
        self.temp_points = []
        self.temp_line = None
        self.temp_poly = None
        self.temp_circle = None
        self.drag_start = None  # For DRAW_CIRCLE_DRAG
        
        # Shape default properties (used by drawing tools)
        self.current_shape_color = "#7c4dff"
        self.current_shape_line_width = 2
        self.current_fill_color = ""
        self.continuous_shape = False  # Stay in same tool after completing a shape
        
        # Text default properties
        self.current_text_font = "Arial"
        self.current_text_size = 12
        self.current_text_color = "#ff0000"
        self.continuous_text_input = False
        self.editing_text_item = None
        self._base_zoom = self.DEFAULT_BASE_ZOOM

        # 中ボタンパン用の状態管理
        self._mid_pan_active = False
        self._mid_pan_last = None

    def set_text_defaults(self, font_family, font_size, color, continuous=False):
        self.current_text_font = font_family
        self.current_text_size = font_size
        self.current_text_color = color
        self.continuous_text_input = continuous

    def set_shape_defaults(self, line_color, line_width, fill_color=""):
        self.current_shape_color = line_color
        self.current_shape_line_width = line_width
        self.current_fill_color = fill_color

    def set_shape_continuous(self, continuous):
        self.continuous_shape = continuous

    def set_tool_mode(self, mode):
        self.tool_mode = mode
        self.temp_points = []
        self._clear_temp_items()

        if mode == ToolMode.SELECT:
            self.setDragMode(QGraphicsView.NoDrag)
            self.setCursor(Qt.ArrowCursor)
            self._set_items_interactive(True)
        elif mode == ToolMode.NONE:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.setCursor(Qt.ArrowCursor)
            self._set_items_interactive(False)
            self.scene.clearSelection()
        else:
            self.setDragMode(QGraphicsView.NoDrag)
            self.setCursor(Qt.CrossCursor)
            self._set_items_interactive(False)
            self.scene.clearSelection()

    def _set_items_interactive(self, interactive):
        for item in self.scene.items():
            if item == self.background_item: continue
            if item.data(0): # Check for item ID
                item.setFlag(QGraphicsItem.ItemIsSelectable, interactive)
                item.setFlag(QGraphicsItem.ItemIsMovable, interactive)
                # Visual effect for selectable items could go here

    def _clear_temp_items(self):
        if self.temp_line:
            self.scene.removeItem(self.temp_line)
            self.temp_line = None
        if self.temp_poly:
            self.scene.removeItem(self.temp_poly)
            self.temp_poly = None
        if self.temp_circle:
            self.scene.removeItem(self.temp_circle)
            self.temp_circle = None
        self.drag_start = None

    def set_page_image(self, pixmap):
        self.scene.clear()
        self.background_item = QGraphicsPixmapItem(pixmap)
        self.background_item.setZValue(-1)
        self.scene.addItem(self.background_item)
        self.scene.setSceneRect(self.background_item.boundingRect())

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            zoom_in_factor = 1.25
            zoom_out_factor = 1 / zoom_in_factor
            zoom_factor = zoom_in_factor if event.angleDelta().y() > 0 else zoom_out_factor
            self.scale(zoom_factor, zoom_factor)
            self._emit_zoom_changed()
        elif event.modifiers() & Qt.ShiftModifier:
            # Shift+スクロールで左右スクロール
            delta = event.angleDelta().y()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta)
        else:
            super().wheelEvent(event)

    def _emit_zoom_changed(self):
        """現在の拡大率をベース倍率比(%)で通知する。"""
        current_zoom = self.transform().m11()
        base_zoom = self._base_zoom if self._base_zoom > 0 else self.DEFAULT_BASE_ZOOM
        zoom_percent = (current_zoom / base_zoom) * 100.0
        self.zoom_changed.emit(zoom_percent)

    def drawForeground(self, painter, rect):
        # Draw selection boxes for selected items
        for item in self.scene.selectedItems():
            if item == self.background_item: continue
            painter.save()
            painter.setPen(QPen(QColor(255, 255, 255), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            # Map item's bounding rect to scene
            br = item.sceneBoundingRect()
            painter.drawRect(br.adjusted(-2, -2, 2, 2))
            
            # Draw handles at corners
            painter.setBrush(QColor(124, 77, 255))
            painter.setPen(Qt.NoPen)
            s = 6 / self.transform().m11() # Scale handle size with zoom
            for p in [br.topLeft(), br.topRight(), br.bottomLeft(), br.bottomRight()]:
                painter.drawRect(QRectF(p.x() - s/2, p.y() - s/2, s, s))
            painter.restore()
        super().drawForeground(painter, rect)

    def mousePressEvent(self, event):
        # 中ボタンでパン（どのツールでも有効）
        if event.button() == Qt.MiddleButton:
            self._mid_pan_active = True
            self._mid_pan_last = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        if self.tool_mode == ToolMode.SELECT:
            if event.button() == Qt.LeftButton:
                pos = self.mapToScene(event.pos())
                item = self.scene.itemAt(pos, self.transform())
                
                # Walk up to find the main item with ID
                while item and not item.data(0) and item.parentItem():
                    item = item.parentItem()
                
                if item and item != self.background_item and item.data(0):
                    # Our hit-test found the item — select it directly
                    self.scene.clearSelection()
                    item.setSelected(True)
                    self.item_selected.emit(item.data(0))
                    self.viewport().update()
                    super().mousePressEvent(event)
                    return
                # Our hit-test missed — clear and let Qt's built-in selection try
                self.scene.clearSelection()
            super().mousePressEvent(event)
            # After Qt's selection attempt, check what ended up selected
            if event.button() == Qt.LeftButton:
                selected = self.scene.selectedItems()
                if selected:
                    top = selected[0]
                    while top and not top.data(0) and top.parentItem():
                        top = top.parentItem()
                    if top and top.data(0) and top != self.background_item:
                        self.item_selected.emit(top.data(0))
                    else:
                        self.selection_cleared.emit()
                else:
                    self.selection_cleared.emit()
                self.viewport().update()
            return

        if self.tool_mode == ToolMode.NONE:
            super().mousePressEvent(event)
            return

        pos = self.mapToScene(event.pos())
        
        if event.button() == Qt.LeftButton:
            if self.tool_mode in [ToolMode.CALIBRATE, ToolMode.MEASURE_LINE]:
                self.temp_points.append(pos)
                if len(self.temp_points) == 1:
                    self.temp_line = QGraphicsLineItem(pos.x(), pos.y(), pos.x(), pos.y())
                    pen = QPen(QColor(124, 77, 255), 2)
                    pen.setCosmetic(True)
                    self.temp_line.setPen(pen)
                    self.scene.addItem(self.temp_line)
                elif len(self.temp_points) == 2:
                    p1, p2 = self.temp_points
                    if self.tool_mode == ToolMode.CALIBRATE:
                        self.calibration_points_selected.emit(p1, p2)
                    else:
                        self.measurement_complete.emit(p1, p2)
                    self._finish_tool()

            elif self.tool_mode == ToolMode.DRAW_LINE:
                # Shiftキー押下中：前点に対して水平・垂直・45度スナップ
                snap_pos = pos
                if (event.modifiers() & Qt.ShiftModifier) and self.temp_points:
                    snap_pos = self._apply_angle_snap(self.temp_points[-1], pos)
                self.temp_points.append(snap_pos)
                if not self.temp_poly:
                    self.temp_poly = QGraphicsPathItem()
                    pen = QPen(QColor(self.current_shape_color), self.current_shape_line_width)
                    pen.setCosmetic(True)
                    self.temp_poly.setPen(pen)
                    self.scene.addItem(self.temp_poly)
                self._update_temp_polyline_path()

            elif self.tool_mode == ToolMode.POLYGON_AREA:
                # Shiftキー押下中：前点に対して水平・垂直・45度スナップ
                if (event.modifiers() & Qt.ShiftModifier) and self.temp_points:
                    pos = self._apply_angle_snap(self.temp_points[-1], pos)
                self.temp_points.append(pos)
                if not self.temp_poly:
                    self.temp_poly = QGraphicsPolygonItem()
                    pen = QPen(QColor(self.current_shape_color), self.current_shape_line_width)
                    pen.setCosmetic(True)
                    self.temp_poly.setPen(pen)
                    fill = QColor(self.current_fill_color) if self.current_fill_color else QColor(self.current_shape_color)
                    fill.setAlpha(50)
                    self.temp_poly.setBrush(fill)
                    self.scene.addItem(self.temp_poly)
                self.temp_poly.setPolygon(QPolygonF(self.temp_points))

            elif self.tool_mode == ToolMode.DRAW_CIRCLE_DRAG:
                self.drag_start = pos

            elif self.tool_mode == ToolMode.CIRCLE_FIXED:
                self.point_selected.emit(pos)
                self._finish_tool(ToolMode.SELECT)
                
            elif self.tool_mode == ToolMode.TEXT:
                item = self.scene.itemAt(pos, self.transform())
                if item == self.editing_text_item:
                    super().mousePressEvent(event)
                    return
                
                if self.editing_text_item:
                    self.editing_text_item.clearFocus()
                    if not self.continuous_text_input:
                        super().mousePressEvent(event)
                        return
                        
                self._start_inline_text_editing(pos)
                super().mousePressEvent(event)
                return

        elif event.button() == Qt.RightButton:
            if self.tool_mode == ToolMode.POLYGON_AREA and len(self.temp_points) >= 3:
                self.polygon_complete.emit(self.temp_points)
                self._finish_tool(self.tool_mode if self.continuous_shape else ToolMode.SELECT)
            elif self.tool_mode == ToolMode.DRAW_LINE and len(self.temp_points) >= 2:
                self.polyline_complete.emit(self.temp_points[:])
                self._finish_tool(self.tool_mode if self.continuous_shape else ToolMode.SELECT)

    def _apply_angle_snap(self, start: QPointF, pos: QPointF) -> QPointF:
        """Shiftキー押下時に水平・垂直・45度スナップを適用する"""
        dx = pos.x() - start.x()
        dy = pos.y() - start.y()
        distance = math.sqrt(dx * dx + dy * dy)
        if distance < 0.001:
            return pos
        angle_deg = math.degrees(math.atan2(dy, dx))
        snapped_deg = round(angle_deg / 45.0) * 45.0
        snapped_rad = math.radians(snapped_deg)
        return QPointF(start.x() + distance * math.cos(snapped_rad),
                       start.y() + distance * math.sin(snapped_rad))

    def _update_temp_polyline_path(self, preview_end=None):
        if not self.temp_poly or not self.temp_points:
            return
        path = QPainterPath()
        path.moveTo(self.temp_points[0])
        for pt in self.temp_points[1:]:
            path.lineTo(pt)
        if preview_end:
            path.lineTo(preview_end)
        self.temp_poly.setPath(path)

    def _start_inline_text_editing(self, pos):
        if self.editing_text_item:
            self.scene.removeItem(self.editing_text_item)
            self.editing_text_item = None
            
        self.editing_text_item = CustomTextItem("")
        self.editing_text_item.setPos(pos)
        self.editing_text_item.setDefaultTextColor(QColor(self.current_text_color))
        font = QFont(self.current_text_font, self.current_text_size)
        self.editing_text_item.setFont(font)
        
        self.scene.addItem(self.editing_text_item)
        self.editing_text_item.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.editing_text_item.setFocus()
        
        self.editing_text_item.editing_finished.connect(self._on_inline_text_finished)

    def _on_inline_text_finished(self, text):
        if self.editing_text_item:
            pos = self.editing_text_item.pos()
            self.scene.removeItem(self.editing_text_item)
            self.editing_text_item = None
            
            if text.strip():
                self.text_editing_finished.emit(pos, text, "", self.current_text_font, self.current_text_size, self.current_text_color)
                
        if not self.continuous_text_input:
            self._finish_tool(ToolMode.SELECT)

    def _finish_tool(self, next_mode=ToolMode.NONE):
        self._clear_temp_items()
        self.temp_points = []
        self.request_tool_change.emit(next_mode)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and self.tool_mode == ToolMode.DRAW_LINE:
            # The single-click that fired before this double-click already appended a point;
            # remove it so the path ends at the previous point.
            if len(self.temp_points) >= 2:
                self.temp_points.pop()
            if len(self.temp_points) >= 2:
                self.polyline_complete.emit(self.temp_points[:])
                self._finish_tool(self.tool_mode if self.continuous_shape else ToolMode.SELECT)
            return
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        # 中ボタンパン処理
        if self._mid_pan_active:
            delta = event.pos() - self._mid_pan_last
            self._mid_pan_last = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return

        pos = self.mapToScene(event.pos())
        shift_held = bool(event.modifiers() & Qt.ShiftModifier)
        if self.temp_line and len(self.temp_points) == 1:
            # Shiftキー押下中：スナップしたプレビュー表示
            preview_pos = self._apply_angle_snap(self.temp_points[0], pos) if shift_held else pos
            self.temp_line.setLine(self.temp_points[0].x(), self.temp_points[0].y(),
                                   preview_pos.x(), preview_pos.y())
        elif self.temp_poly and self.tool_mode == ToolMode.DRAW_LINE and len(self.temp_points) >= 1:
            # Shiftキー押下中：直前の点に対してスナップしたプレビュー表示
            preview_pos = self._apply_angle_snap(self.temp_points[-1], pos) if shift_held else pos
            self._update_temp_polyline_path(preview_end=preview_pos)
        elif self.temp_poly and self.tool_mode == ToolMode.POLYGON_AREA and len(self.temp_points) >= 1:
            # Shiftキー押下中：直前の点に対してスナップしたプレビュー表示
            preview_pos = self._apply_angle_snap(self.temp_points[-1], pos) if shift_held else pos
            preview_points = self.temp_points + [preview_pos]
            self.temp_poly.setPolygon(QPolygonF(preview_points))
        elif self.tool_mode == ToolMode.DRAW_CIRCLE_DRAG and self.drag_start:
            radius = math.sqrt((pos.x() - self.drag_start.x()) ** 2 + (pos.y() - self.drag_start.y()) ** 2)
            if self.temp_circle:
                self.scene.removeItem(self.temp_circle)
            cx, cy = self.drag_start.x(), self.drag_start.y()
            self.temp_circle = QGraphicsEllipseItem(cx - radius, cy - radius, radius * 2, radius * 2)
            pen = QPen(QColor(self.current_shape_color), self.current_shape_line_width)
            pen.setCosmetic(True)
            self.temp_circle.setPen(pen)
            if self.current_fill_color:
                fill = QColor(self.current_fill_color)
                fill.setAlpha(50)
                self.temp_circle.setBrush(fill)
            self.scene.addItem(self.temp_circle)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        # 中ボタンパン終了
        if event.button() == Qt.MiddleButton and self._mid_pan_active:
            self._mid_pan_active = False
            self._mid_pan_last = None
            # ツールモードに応じてカーソルを復元
            if self.tool_mode == ToolMode.SELECT:
                self.setCursor(Qt.ArrowCursor)
            elif self.tool_mode == ToolMode.NONE:
                self.setCursor(Qt.ArrowCursor)
            else:
                self.setCursor(Qt.CrossCursor)
            event.accept()
            return

        if self.tool_mode == ToolMode.DRAW_CIRCLE_DRAG and self.drag_start and event.button() == Qt.LeftButton:
            pos = self.mapToScene(event.pos())
            radius = math.sqrt((pos.x() - self.drag_start.x()) ** 2 + (pos.y() - self.drag_start.y()) ** 2)
            center = self.drag_start
            self.drag_start = None
            if self.temp_circle:
                self.scene.removeItem(self.temp_circle)
                self.temp_circle = None
            # Emit even with small radius (0 means "use preset from tool options")
            self.circle_drag_complete.emit(center, radius)
            self._finish_tool(self.tool_mode if self.continuous_shape else ToolMode.SELECT)
            return
        if self.tool_mode == ToolMode.SELECT:
            # Check if any item moved
            for item in self.scene.selectedItems():
                item_id = item.data(0)
                last_pos = item.data(1)
                if item_id and last_pos is not None:
                    # ItemIsMovable handles the pos update, we calculate delta
                    delta = item.pos() - last_pos
                    if delta.x() != 0 or delta.y() != 0:
                        self.item_moved.emit(item_id, delta)
                        item.setData(1, item.pos())
        super().mouseReleaseEvent(event)

    def add_line_annotation(self, p1, p2, text="", color="red", item_id=None, font_family="Arial", font_size=12, line_width=2, stroke_opacity=100):
        line = QGraphicsLineItem(p1.x(), p1.y(), p2.x(), p2.y())
        stroke_c = QColor(color)
        stroke_c.setAlpha(round(stroke_opacity / 100.0 * 255))
        pen = QPen(stroke_c, line_width)
        pen.setCosmetic(True)
        line.setPen(pen)
        if item_id: 
            line.setData(0, item_id)
            line.setData(1, QPointF(0,0)) # Initial relative pos
        self.scene.addItem(line)
        
        txt_item = self._add_text_item(text, (p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2, color, font_family, font_size)
        if txt_item:
            txt_item.setParentItem(line)

    def add_polyline_annotation(self, points, text="", color="#7c4dff", item_id=None, font_family="Arial", font_size=12, line_width=2, stroke_opacity=100, start_marker="", end_marker=""):
        if not points:
            return
        path = QPainterPath()
        path.moveTo(points[0])
        for pt in points[1:]:
            path.lineTo(pt)
        item = QGraphicsPathItem(path)
        stroke_c = QColor(color)
        stroke_c.setAlpha(round(stroke_opacity / 100.0 * 255))
        pen = QPen(stroke_c, line_width)
        pen.setCosmetic(True)
        item.setPen(pen)
        item.setBrush(Qt.NoBrush)
        if item_id:
            item.setData(0, item_id)
            item.setData(1, QPointF(0, 0))
        self.scene.addItem(item)

        if len(points) >= 2:
            if start_marker:
                self._draw_endpoint_marker(item, points[0], points[1], start_marker, color)
            if end_marker:
                self._draw_endpoint_marker(item, points[-1], points[-2], end_marker, color)

        if text:
            mid_idx = len(points) // 2
            mid = points[mid_idx]
            txt_item = self._add_text_item(text, mid.x(), mid.y(), color, font_family, font_size)
            if txt_item:
                txt_item.setParentItem(item)

    def add_polygon_annotation(self, points, text="", color="blue", item_id=None, font_family="Arial", font_size=12, line_width=2, stroke_opacity=100, fill_opacity=30, fill_color=""):
        poly = QGraphicsPolygonItem(QPolygonF(points))
        stroke_c = QColor(color)
        stroke_c.setAlpha(round(stroke_opacity / 100.0 * 255))
        pen = QPen(stroke_c, line_width)
        pen.setCosmetic(True)
        poly.setPen(pen)
        if fill_opacity == 0:
            poly.setBrush(Qt.NoBrush)
        else:
            fill_base = QColor(fill_color) if fill_color else QColor(color)
            fill_base.setAlpha(round(fill_opacity / 100.0 * 255))
            poly.setBrush(fill_base)
        if item_id: 
            poly.setData(0, item_id)
            poly.setData(1, QPointF(0,0))
        self.scene.addItem(poly)
        
        avg_x = sum(p.x() for p in points) / len(points)
        avg_y = sum(p.y() for p in points) / len(points)
        txt_item = self._add_text_item(text, avg_x, avg_y, color, font_family, font_size)
        if txt_item:
            txt_item.setParentItem(poly)

    def add_circle_annotation(self, center, radius_px, text="", color="green", item_id=None, font_family="Arial", font_size=12, line_width=2, stroke_opacity=100, fill_opacity=30, fill_color="", center_marker=""):
        circle = QGraphicsEllipseItem(center.x() - radius_px, center.y() - radius_px, radius_px * 2, radius_px * 2)
        stroke_c = QColor(color)
        stroke_c.setAlpha(round(stroke_opacity / 100.0 * 255))
        pen = QPen(stroke_c, line_width)
        pen.setCosmetic(True)
        circle.setPen(pen)
        if fill_opacity == 0:
            circle.setBrush(Qt.NoBrush)
        else:
            fill_base = QColor(fill_color) if fill_color else QColor(color)
            fill_base.setAlpha(round(fill_opacity / 100.0 * 255))
            circle.setBrush(fill_base)
        if item_id: 
            circle.setData(0, item_id)
            circle.setData(1, QPointF(0,0))
        self.scene.addItem(circle)

        if center_marker:
            cx, cy = center.x(), center.y()
            self._draw_center_marker(circle, cx, cy, center_marker, color)
        
        txt_item = self._add_text_item(text, center.x(), center.y() - radius_px - 10, color, font_family, font_size)
        if txt_item:
            txt_item.setParentItem(circle)

    def _draw_center_marker(self, parent, cx, cy, marker_type, color, size=10):
        """Draw a center marker as a child of parent at local coords (cx, cy)."""
        if marker_type == "circle":
            s = size / 2
            item = QGraphicsEllipseItem(cx - s, cy - s, size, size, parent)
            pen = QPen(QColor(color), 1.5)
            pen.setCosmetic(True)
            item.setPen(pen)
            item.setBrush(QColor(color))
        elif marker_type == "cross":
            s = size / 2
            path = QPainterPath()
            path.moveTo(cx - s, cy)
            path.lineTo(cx + s, cy)
            path.moveTo(cx, cy - s)
            path.lineTo(cx, cy + s)
            item = QGraphicsPathItem(path, parent)
            pen = QPen(QColor(color), 2)
            pen.setCosmetic(True)
            item.setPen(pen)
        elif marker_type == "x":
            s = size / 2
            path = QPainterPath()
            path.moveTo(cx - s, cy - s)
            path.lineTo(cx + s, cy + s)
            path.moveTo(cx + s, cy - s)
            path.lineTo(cx - s, cy + s)
            item = QGraphicsPathItem(path, parent)
            pen = QPen(QColor(color), 2)
            pen.setCosmetic(True)
            item.setPen(pen)
        else:
            return
        item.setData(2, "marker")

    def _draw_endpoint_marker(self, parent, point, neighbor, marker_type, color, size=10):
        """Draw a start/end marker as a child of parent. point is where it goes, neighbor
        is the adjacent point used to compute arrow direction."""
        px, py = point.x(), point.y()
        if marker_type == "circle":
            s = size / 2
            item = QGraphicsEllipseItem(px - s, py - s, size, size, parent)
            pen = QPen(QColor(color), 1.5)
            pen.setCosmetic(True)
            item.setPen(pen)
            item.setBrush(QColor(color))
            item.setData(2, "marker")
        elif marker_type == "arrow":
            # Direction pointing away from the interior (outward)
            dx = px - neighbor.x()
            dy = py - neighbor.y()
            length = math.sqrt(dx * dx + dy * dy)
            if length == 0:
                return
            dx /= length
            dy /= length
            # Perpendicular
            perp_x, perp_y = -dy, dx
            # Arrow wings behind the tip
            bx = px - dx * size
            by = py - dy * size
            wing1 = QPointF(bx + perp_x * size * 0.45, by + perp_y * size * 0.45)
            wing2 = QPointF(bx - perp_x * size * 0.45, by - perp_y * size * 0.45)
            path = QPainterPath()
            path.moveTo(wing1)
            path.lineTo(QPointF(px, py))
            path.lineTo(wing2)
            path.closeSubpath()
            item = QGraphicsPathItem(path, parent)
            pen = QPen(QColor(color), 1)
            pen.setCosmetic(True)
            item.setPen(pen)
            item.setBrush(QColor(color))
            item.setData(2, "marker")

    def add_text_annotation(self, pos, text, color="black", item_id=None, font_family="Arial", font_size=12, stroke_opacity=100):
        txt_item = self._add_text_item(text, pos.x(), pos.y(), color, font_family, font_size)
        if txt_item:
            txt_item.setOpacity(stroke_opacity / 100.0)
            if item_id:
                txt_item.setData(0, item_id)
                txt_item.setData(1, QPointF(0,0))

    def _add_text_item(self, text, x, y, color, font_family="Arial", font_size=12):
        if not text: return None
        text_item = CustomTextItem(text)
        text_item.setDefaultTextColor(QColor(color))
        
        font = QFont(font_family, font_size)
        text_item.setFont(font)
        
        text_item.setPos(x, y)
        self.scene.addItem(text_item)
        
        text_item.editing_finished.connect(lambda txt, item=text_item: self._on_existing_text_edited(txt, item))
        return text_item

    def _on_existing_text_edited(self, new_text, item):
        item_id = item.data(0)
        if not item_id and item.parentItem():
            item_id = item.parentItem().data(0)
            
        if item_id:
            self.existing_text_edited.emit(item_id, new_text)

    def update_item_properties(self, item_id, attrs):
        for item in self.scene.items():
            if item.data(0) == item_id:
                if "color" in attrs or "line_width" in attrs or "stroke_opacity" in attrs:
                    if isinstance(item, (QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsPolygonItem, QGraphicsPathItem)):
                        pen = item.pen()
                        cur_pen_c = pen.color()
                        base_rgb = QColor(attrs["color"]) if "color" in attrs else QColor(cur_pen_c.red(), cur_pen_c.green(), cur_pen_c.blue())
                        new_alpha = round(attrs["stroke_opacity"] / 100.0 * 255) if "stroke_opacity" in attrs else cur_pen_c.alpha()
                        new_pen_c = QColor(base_rgb.red(), base_rgb.green(), base_rgb.blue(), new_alpha)
                        pen.setColor(new_pen_c)
                        if "line_width" in attrs:
                            pen.setWidth(attrs["line_width"])
                        item.setPen(pen)

                        # When stroke color changes, update brush on polygon if fill derives from stroke
                        if "color" in attrs and isinstance(item, QGraphicsPolygonItem):
                            cur_brush = item.brush()
                            if cur_brush.style() != Qt.NoBrush:
                                cur_fill_a = cur_brush.color().alpha()
                                item.setBrush(QColor(base_rgb.red(), base_rgb.green(), base_rgb.blue(), cur_fill_a))

                if "fill_color" in attrs or "fill_opacity" in attrs:
                    if isinstance(item, (QGraphicsPolygonItem, QGraphicsEllipseItem)):
                        cur_brush = item.brush()
                        # Determine fill alpha
                        if "fill_opacity" in attrs:
                            fill_alpha = round(attrs["fill_opacity"] / 100.0 * 255)
                        elif cur_brush.style() != Qt.NoBrush:
                            fill_alpha = cur_brush.color().alpha()
                        else:
                            fill_alpha = 0
                        # Determine fill RGB
                        if "fill_color" in attrs:
                            fill_base = QColor(attrs["fill_color"]) if attrs["fill_color"] else None
                        elif cur_brush.style() != Qt.NoBrush:
                            bc = cur_brush.color()
                            fill_base = QColor(bc.red(), bc.green(), bc.blue())
                        else:
                            fill_base = None
                        if fill_alpha == 0:
                            item.setBrush(Qt.NoBrush)
                        elif fill_base:
                            fill_base.setAlpha(fill_alpha)
                            item.setBrush(fill_base)
                        else:
                            # No explicit fill color — derive from stroke color
                            pen_c = item.pen().color()
                            item.setBrush(QColor(pen_c.red(), pen_c.green(), pen_c.blue(), fill_alpha))

                # Handle marker updates
                has_marker_change = any(k in attrs for k in ("center_marker", "start_marker", "end_marker"))
                if has_marker_change:
                    # Remove existing marker children
                    for child in list(item.childItems()):
                        if child.data(2) == "marker":
                            self.scene.removeItem(child)
                    color_str = item.pen().color().name() if hasattr(item, 'pen') else "#7c4dff"
                    if isinstance(item, QGraphicsEllipseItem) and "center_marker" in attrs:
                        r = item.rect()
                        cx, cy = r.center().x(), r.center().y()
                        self._draw_center_marker(item, cx, cy, attrs["center_marker"], color_str)
                    elif isinstance(item, QGraphicsPathItem):
                        path = item.path()
                        n = path.elementCount()
                        if n >= 2:
                            e0 = path.elementAt(0)
                            e1 = path.elementAt(1)
                            en = path.elementAt(n - 1)
                            en1 = path.elementAt(n - 2)
                            if "start_marker" in attrs and attrs["start_marker"]:
                                self._draw_endpoint_marker(item, QPointF(e0.x, e0.y), QPointF(e1.x, e1.y), attrs["start_marker"], color_str)
                            if "end_marker" in attrs and attrs["end_marker"]:
                                self._draw_endpoint_marker(item, QPointF(en.x, en.y), QPointF(en1.x, en1.y), attrs["end_marker"], color_str)

                text_items = [item] if isinstance(item, QGraphicsTextItem) else [child for child in item.childItems() if isinstance(child, QGraphicsTextItem)]

                for txt in text_items:
                    font = txt.font()
                    if "font_family" in attrs:
                        font.setFamily(attrs["font_family"])
                    if "font_size" in attrs:
                        font.setPointSize(attrs["font_size"])
                    txt.setFont(font)

                    if "text" in attrs:
                        txt.setPlainText(attrs["text"])
                    if "color" in attrs:
                        txt.setDefaultTextColor(QColor(attrs["color"]))
                    if "stroke_opacity" in attrs:
                        txt.setOpacity(attrs["stroke_opacity"] / 100.0)

                # If text is being set but no text child exists yet, create one
                if "text" in attrs and attrs["text"].strip() and not text_items and not isinstance(item, QGraphicsTextItem):
                    color_str = item.pen().color().name() if hasattr(item, 'pen') else "#7c4dff"
                    ff = attrs.get("font_family", "Arial")
                    fs = attrs.get("font_size", 12)
                    if isinstance(item, QGraphicsEllipseItem):
                        r = item.rect()
                        tx, ty = r.center().x(), r.top() - 15
                    elif isinstance(item, QGraphicsPolygonItem):
                        br = item.polygon().boundingRect()
                        tx, ty = br.center().x(), br.center().y()
                    elif isinstance(item, QGraphicsPathItem):
                        path = item.path()
                        n = path.elementCount()
                        mid = path.elementAt(n // 2)
                        tx, ty = mid.x, mid.y - 15
                    else:
                        br = item.boundingRect()
                        tx, ty = br.center().x(), br.top() - 15
                    txt_new = self._add_text_item(attrs["text"], tx, ty, color_str, ff, fs)
                    if txt_new:
                        txt_new.setParentItem(item)
                break

    def reset_view(self):
        self.resetTransform()
        if self.background_item:
            self.fitInView(self.background_item, Qt.KeepAspectRatio)
        self._base_zoom = self.transform().m11() if self.transform().m11() > 0 else self.DEFAULT_BASE_ZOOM
        self._emit_zoom_changed()
