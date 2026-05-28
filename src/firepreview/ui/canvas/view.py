import math
from PySide6.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, 
                                 QGraphicsLineItem, QGraphicsTextItem, QGraphicsEllipseItem, 
                                 QGraphicsPolygonItem, QGraphicsPathItem, QMenu, QGraphicsItem)
from PySide6.QtCore import Qt, Signal, QPointF, QRectF, QEvent
from PySide6.QtGui import QPainter, QPen, QColor, QPolygonF, QAction, QFont, QPainterPath

from .items import CustomTextItem, VertexHandleItem
from .utils import point_to_segment_distance, apply_angle_snap
from .enums import ToolMode

class PDFCanvas(QGraphicsView):
    calibration_points_selected = Signal(QPointF, QPointF)
    polygon_complete = Signal(list) # list of QPointF
    polyline_complete = Signal(list)  # list of QPointF for polyline tool
    circle_drag_complete = Signal(QPointF, float)  # center, radius_px
    marker_complete = Signal(QPointF)
    legend_complete = Signal(QPointF)

    
    # Selection/Editing signals
    item_selected = Signal(str) # id
    selection_cleared = Signal()
    item_moved = Signal(str, QPointF) # id, delta
    label_moved = Signal(str, QPointF) # id, delta
    request_delete = Signal(str) # id
    request_tool_change = Signal(int) # next_mode
    zoom_changed = Signal(float)  # 現在のキャンバス拡大率（1.0 = 等倍）
    
    text_editing_finished = Signal(QPointF, str, str, str, int, str) # pos, text, item_id, font_family, font_size, color
    existing_text_edited = Signal(str, str) # item_id, new_text
    
    # Node editing signals
    item_points_updated = Signal(str, list)  # id, list of QPointF
    node_edit_ended = Signal(str)            # id

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

        # 中ボタンパン用の状態管理
        self._mid_pan_active = False
        self._mid_pan_last = None

        # 頂点編集用の状態管理
        self.editing_node_item_id = None
        self.vertex_handles = []
        self.editing_label_item_id = None

        # 個別オブジェクト移動・編集モード用の状態管理
        self.active_edit_mode = False
        self.editing_item_id = None

        self.annotation_items = {}
        self._original_accepted_buttons = {}

        # Instantiate modular drawing tools
        from .tools import SelectTool, DrawLineTool, PolygonTool, CircleTool, TextTool, CalibrationTool, MarkerTool, LegendTool
        self.tools = {
            ToolMode.SELECT: SelectTool(self),
            ToolMode.DRAW_LINE: DrawLineTool(self),
            ToolMode.POLYGON_AREA: PolygonTool(self),
            ToolMode.DRAW_CIRCLE_DRAG: CircleTool(self),
            ToolMode.TEXT: TextTool(self),
            ToolMode.CALIBRATE: CalibrationTool(self),
            ToolMode.DRAW_MARKER: MarkerTool(self),
            ToolMode.DRAW_LEGEND: LegendTool(self)
        }
        
        self.hover_connection_line = None
        self.scene.installEventFilter(self)

    def _get_active_tool(self):
        return self.tools.get(self.tool_mode)

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
        if self.tool_mode == ToolMode.SELECT and mode != ToolMode.SELECT:
            self.end_node_editing()
            self.end_label_editing()
        elif mode != ToolMode.SELECT:
            self.end_label_editing()
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

    def set_active_edit_item(self, item_id, active):
        """特定のオブジェクトのみを編集可能にし、他のオブジェクトを半透明・操作不可にする"""
        if active:
            if self.active_edit_mode and self.editing_item_id != item_id:
                self.set_active_edit_item(self.editing_item_id, False)

        self.active_edit_mode = active
        self.editing_item_id = item_id if active else None

        if active:
            self._original_accepted_buttons.clear()
            for item in self.scene.items():
                if item == self.background_item:
                    continue
                
                iid = item.data(0)
                if iid and item.parentItem() is None:
                    if iid == item_id:
                        item.setEnabled(True)
                        item.setOpacity(1.0)
                        item.setFlag(QGraphicsItem.ItemIsSelectable, True)
                        item.setFlag(QGraphicsItem.ItemIsMovable, True)
                    else:
                        item.setEnabled(True)
                        item.setOpacity(0.25)
                        item.setFlag(QGraphicsItem.ItemIsSelectable, False)
                        item.setFlag(QGraphicsItem.ItemIsMovable, False)
                        
                        self._original_accepted_buttons[item] = item.acceptedMouseButtons()
                        item.setAcceptedMouseButtons(Qt.NoButton)
        else:
            for item in self.scene.items():
                if item == self.background_item:
                    continue
                
                iid = item.data(0)
                if iid and item.parentItem() is None:
                    item.setEnabled(True)
                    item.setOpacity(1.0)
                    interactive = (self.tool_mode == ToolMode.SELECT)
                    item.setFlag(QGraphicsItem.ItemIsSelectable, interactive)
                    item.setFlag(QGraphicsItem.ItemIsMovable, interactive)
            
            for item, buttons in self._original_accepted_buttons.items():
                try:
                    item.setAcceptedMouseButtons(buttons)
                except RuntimeError:
                    pass
            self._original_accepted_buttons.clear()
        self.scene.clearSelection()
        if active:
            target_item = self.annotation_items.get(item_id)
            if target_item:
                target_item.setSelected(True)
        self.viewport().update()

    def _set_items_interactive(self, interactive):
        for item in self.scene.items():
            if item == self.background_item: continue
            if item.data(0):
                if item.data(3) == "label":
                    is_editing = (self.editing_label_item_id == item.data(0))
                    item.setFlag(QGraphicsItem.ItemIsSelectable, interactive and is_editing)
                    item.setFlag(QGraphicsItem.ItemIsMovable, interactive and is_editing)
                else:
                    item.setFlag(QGraphicsItem.ItemIsSelectable, interactive)
                    item.setFlag(QGraphicsItem.ItemIsMovable, interactive)

    def _clear_temp_items(self):
        def _safe_remove(item):
            if item:
                try:
                    self.scene.removeItem(item)
                except RuntimeError:
                    pass
            return None

        self.temp_line = _safe_remove(self.temp_line)
        self.temp_poly = _safe_remove(self.temp_poly)
        self.temp_circle = _safe_remove(self.temp_circle)
        self.drag_start = None

    def set_page_image(self, pixmap):
        self.temp_line = None
        self.temp_poly = None
        self.temp_circle = None
        self.annotation_items.clear()
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
            delta = event.angleDelta().y()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta)
        else:
            super().wheelEvent(event)

    def _emit_zoom_changed(self):
        current_zoom = self.transform().m11()
        if current_zoom <= 0:
            self.zoom_changed.emit(0.0)
            return
        self.zoom_changed.emit(current_zoom)

    def drawForeground(self, painter, rect):
        for item in self.scene.selectedItems():
            if item == self.background_item: continue
            painter.save()
            painter.setPen(QPen(QColor(255, 255, 255), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            
            # Map item's local bounding rect via sceneTransform() to accurately handle ItemIgnoresTransformations
            transform = item.sceneTransform()
            local_rect = item.boundingRect()
            scene_poly = transform.map(QPolygonF(local_rect))
            br = scene_poly.boundingRect()
            
            painter.drawRect(br.adjusted(-2, -2, 2, 2))
            
            painter.setBrush(QColor(124, 77, 255))
            painter.setPen(Qt.NoPen)
            s = 6 / self.transform().m11()
            for p in [br.topLeft(), br.topRight(), br.bottomLeft(), br.bottomRight()]:
                painter.drawRect(QRectF(p.x() - s/2, p.y() - s/2, s, s))
            painter.restore()
        super().drawForeground(painter, rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._mid_pan_active = True
            self._mid_pan_last = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        # ★最優先: 個別オブジェクト編集モード中のガード＆貫通処理★
        if self.active_edit_mode:
            if event.button() == Qt.LeftButton:
                pos = self.mapToScene(event.pos())
                clicked_edit_item = False
                
                items_at_pos = self.scene.items(pos, Qt.IntersectsItemShape, Qt.DescendingOrder, self.transform())
                for item_at_pos in items_at_pos:
                    temp_item = item_at_pos
                    while temp_item:
                        if temp_item.data(0) == self.editing_item_id:
                            clicked_edit_item = True
                            break
                        temp_item = temp_item.parentItem()
                    if clicked_edit_item:
                        break
                
                if clicked_edit_item:
                    target_item = self.annotation_items.get(self.editing_item_id)
                    if target_item:
                        self.scene.clearSelection()
                        target_item.setSelected(True)
                    super().mousePressEvent(event)
                else:
                    event.accept()
                return
            elif event.button() == Qt.RightButton:
                pos = self.mapToScene(event.pos())
                item = self.scene.itemAt(pos, self.transform())
                while item and not item.data(0) and item.parentItem():
                    item = item.parentItem()
                if item and item.data(0) == self.editing_item_id:
                    self._show_object_context_menu(event.globalPosition().toPoint(), item.data(0))
                    event.accept()
                    return
                event.accept()
                return

        # Delegate event handling to current tool
        tool = self._get_active_tool()
        if tool and tool.mouse_press(event, self.scene):
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._mid_pan_active:
            delta = event.pos() - self._mid_pan_last
            self._mid_pan_last = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return

        tool = self._get_active_tool()
        if tool and tool.mouse_move(event, self.scene):
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton and self._mid_pan_active:
            self._mid_pan_active = False
            self._mid_pan_last = None
            if self.tool_mode in [ToolMode.SELECT, ToolMode.NONE]:
                self.setCursor(Qt.ArrowCursor)
            else:
                self.setCursor(Qt.CrossCursor)
            event.accept()
            return

        tool = self._get_active_tool()
        if tool and tool.mouse_release(event, self.scene):
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        tool = self._get_active_tool()
        if tool and tool.double_click(event, self.scene):
            return

        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        if self.tool_mode == ToolMode.SELECT:
            if self.editing_node_item_id:
                if event.key() in [Qt.Key_Delete, Qt.Key_Backspace]:
                    selected = self.scene.selectedItems()
                    for sel in selected:
                        if isinstance(sel, VertexHandleItem):
                            self.on_vertex_double_clicked(sel.parent_item, sel.index)
                            event.accept()
                            return
                elif event.key() == Qt.Key_Escape:
                    self.end_node_editing()
                    event.accept()
                    return
            elif self.editing_label_item_id:
                if event.key() == Qt.Key_Escape:
                    self.end_label_editing()
                    event.accept()
                    return
        super().keyPressEvent(event)

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

    # === Annotation rendering API methods ===

    def add_line_annotation(self, p1, p2, text="", color="red", item_id=None, font_family="Arial", font_size=12, line_width=2, stroke_opacity=100, label_offset=None):
        line = QGraphicsLineItem(p1.x(), p1.y(), p2.x(), p2.y())
        line.setAcceptHoverEvents(True)
        stroke_c = QColor(color)
        stroke_c.setAlpha(round(stroke_opacity / 100.0 * 255))
        pen = QPen(stroke_c, line_width)
        pen.setCosmetic(True)
        line.setPen(pen)
        if item_id: 
            line.setData(0, item_id)
            line.setData(1, QPointF(0,0))
        self.scene.addItem(line)
        
        offset = QPointF(label_offset[0], label_offset[1]) if label_offset else QPointF(0, 0)
        ref_pos = QPointF((p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2)
        txt_item = self._add_text_item(text, ref_pos.x() + offset.x(), ref_pos.y() + offset.y(), color, font_family, font_size)
        if txt_item:
            txt_item.setParentItem(line)
            txt_item.label_offset = offset
            txt_item.setData(0, item_id)
            txt_item.setData(3, "label")
            interactive = (self.tool_mode == ToolMode.SELECT)
            is_editing = (self.editing_label_item_id == item_id)
            txt_item.setFlag(QGraphicsItem.ItemIsSelectable, interactive and is_editing)
            txt_item.setFlag(QGraphicsItem.ItemIsMovable, interactive and is_editing)
            
        if item_id:
            self.annotation_items[item_id] = line

    def add_polyline_annotation(self, points, text="", color="#7c4dff", item_id=None, font_family="Arial", font_size=12, line_width=2, stroke_opacity=100, start_marker="", end_marker="", label_offset=None):
        if not points:
            return
        path = QPainterPath()
        path.moveTo(points[0])
        for pt in points[1:]:
            path.lineTo(pt)
        item = QGraphicsPathItem(path)
        item.setAcceptHoverEvents(True)
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
            offset = QPointF(label_offset[0], label_offset[1]) if label_offset else QPointF(0, 0)
            avg_x = sum(p.x() for p in points) / len(points)
            avg_y = sum(p.y() for p in points) / len(points)
            ref_pos = QPointF(avg_x, avg_y)
            txt_item = self._add_text_item(text, ref_pos.x() + offset.x(), ref_pos.y() + offset.y(), color, font_family, font_size)
            if txt_item:
                txt_item.setParentItem(item)
                txt_item.label_offset = offset
                txt_item.setData(0, item_id)
                txt_item.setData(3, "label")
                interactive = (self.tool_mode == ToolMode.SELECT)
                is_editing = (self.editing_label_item_id == item_id)
                txt_item.setFlag(QGraphicsItem.ItemIsSelectable, interactive and is_editing)
                txt_item.setFlag(QGraphicsItem.ItemIsMovable, interactive and is_editing)
                
        if item_id:
            self.annotation_items[item_id] = item

    def add_polygon_annotation(self, points, text="", color="blue", item_id=None, font_family="Arial", font_size=12, line_width=2, stroke_opacity=100, fill_opacity=30, fill_color="", label_offset=None):
        poly = QGraphicsPolygonItem(QPolygonF(points))
        poly.setAcceptHoverEvents(True)
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
        
        offset = QPointF(label_offset[0], label_offset[1]) if label_offset else QPointF(0, 0)
        avg_x = sum(p.x() for p in points) / len(points)
        avg_y = sum(p.y() for p in points) / len(points)
        txt_item = self._add_text_item(text, avg_x + offset.x(), avg_y + offset.y(), color, font_family, font_size)
        if txt_item:
            txt_item.setParentItem(poly)
            txt_item.label_offset = offset
            txt_item.setData(0, item_id)
            txt_item.setData(3, "label")
            interactive = (self.tool_mode == ToolMode.SELECT)
            is_editing = (self.editing_label_item_id == item_id)
            txt_item.setFlag(QGraphicsItem.ItemIsSelectable, interactive and is_editing)
            txt_item.setFlag(QGraphicsItem.ItemIsMovable, interactive and is_editing)
            
        if item_id:
            self.annotation_items[item_id] = poly

    def add_circle_annotation(self, center, radius_px, text="", color="green", item_id=None, font_family="Arial", font_size=12, line_width=2, stroke_opacity=100, fill_opacity=30, fill_color="", center_marker="", label_offset=None):
        circle = QGraphicsEllipseItem(center.x() - radius_px, center.y() - radius_px, radius_px * 2, radius_px * 2)
        circle.setAcceptHoverEvents(True)
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
        
        offset = QPointF(label_offset[0], label_offset[1]) if label_offset else QPointF(0, 0)
        ref_pos = QPointF(center.x(), center.y() - radius_px - 10)
        txt_item = self._add_text_item(text, ref_pos.x() + offset.x(), ref_pos.y() + offset.y(), color, font_family, font_size)
        if txt_item:
            txt_item.setParentItem(circle)
            txt_item.label_offset = offset
            txt_item.setData(0, item_id)
            txt_item.setData(3, "label")
            interactive = (self.tool_mode == ToolMode.SELECT)
            is_editing = (self.editing_label_item_id == item_id)
            txt_item.setFlag(QGraphicsItem.ItemIsSelectable, interactive and is_editing)
            txt_item.setFlag(QGraphicsItem.ItemIsMovable, interactive and is_editing)
            
        if item_id:
            self.annotation_items[item_id] = circle

    def _draw_center_marker(self, parent, cx, cy, marker_type, color, size=10):
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
            dx = px - neighbor.x()
            dy = py - neighbor.y()
            length = math.sqrt(dx * dx + dy * dy)
            if length == 0:
                return
            dx /= length
            dy /= length
            perp_x, perp_y = -dy, dx
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

    def add_text_annotation(self, pos, text, color="black", item_id=None, font_family="Arial", font_size=12, stroke_opacity=100,
                            has_border=False, border_color="#ff0000", border_width=2, has_leader=False, leader_end_point=None):
        txt_item = self._add_text_item(text, pos.x(), pos.y(), color, font_family, font_size)
        if txt_item:
            txt_item.setOpacity(stroke_opacity / 100.0)
            txt_item.set_border(has_border, border_color, border_width)
            if leader_end_point:
                txt_item.set_leader(has_leader, leader_end_point)
            else:
                txt_item.set_leader(has_leader, pos + QPointF(50, 50))
            if item_id:
                txt_item.setData(0, item_id)
                txt_item.setData(1, QPointF(0,0))
                self.annotation_items[item_id] = txt_item

    def add_marker_annotation(self, pos, marker_style="square", color="#7c4dff", stroke_opacity=100, item_id=None):
        from .items import MarkerItem
        item = MarkerItem(marker_style, color, stroke_opacity)
        item.setPos(pos)
        if item_id:
            item.setData(0, item_id)
            item.setData(1, QPointF(0, 0))
            self.annotation_items[item_id] = item
        self.scene.addItem(item)

    def add_legend_annotation(self, pos, item_id=None):
        from .items import LegendItem
        item = LegendItem(self)
        item.setPos(pos)
        if item_id:
            item.setData(0, item_id)
            item.setData(1, QPointF(0, 0))
            self.annotation_items[item_id] = item
        self.scene.addItem(item)

    def update_legends(self, marker_counts, color_names):
        from .items import LegendItem
        for item in self.scene.items():
            if isinstance(item, LegendItem):
                item.update_data(marker_counts, color_names)

    def _add_text_item(self, text, x, y, color, font_family="Arial", font_size=12):
        if not text: return None
        text_item = CustomTextItem(text)
        text_item.setAcceptHoverEvents(True)
        text_item.setDefaultTextColor(QColor(color))
        
        if font_size <= 0:
            font_size = 12
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
                if item.parentItem() and item.parentItem().data(0) == item_id:
                    continue
                from .items import MarkerItem
                if isinstance(item, MarkerItem):
                    if "color" in attrs:
                        item.color = QColor(attrs["color"])
                    if "marker_style" in attrs:
                        item.marker_style = attrs["marker_style"]
                    if "stroke_opacity" in attrs:
                        item.opacity = attrs["stroke_opacity"]
                    item.update()
                    self.scene.update()
                    self.viewport().update()
                    break

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

                        if "color" in attrs and isinstance(item, QGraphicsPolygonItem) and "fill_color" not in attrs:
                            cur_brush = item.brush()
                            if cur_brush.style() != Qt.NoBrush:
                                cur_fill_a = cur_brush.color().alpha()
                                item.setBrush(QColor(base_rgb.red(), base_rgb.green(), base_rgb.blue(), cur_fill_a))

                if "fill_color" in attrs or "fill_opacity" in attrs:
                    if isinstance(item, (QGraphicsPolygonItem, QGraphicsEllipseItem)):
                        cur_brush = item.brush()
                        if "fill_opacity" in attrs:
                            fill_alpha = round(attrs["fill_opacity"] / 100.0 * 255)
                        elif cur_brush.style() != Qt.NoBrush:
                            fill_alpha = cur_brush.color().alpha()
                        else:
                            fill_alpha = 0
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
                            pen_c = item.pen().color()
                            item.setBrush(QColor(pen_c.red(), pen_c.green(), pen_c.blue(), fill_alpha))

                has_marker_change = any(k in attrs for k in ("center_marker", "start_marker", "end_marker"))
                if has_marker_change:
                    for child in list(item.childItems()):
                        if child.data(2) == "marker":
                            child.setParentItem(None)
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
                        fs = attrs["font_size"]
                        if fs > 0:
                            font.setPointSize(fs)
                    txt.setFont(font)

                    if "text" in attrs:
                        txt.setPlainText(attrs["text"])
                    if "color" in attrs:
                        txt.setDefaultTextColor(QColor(attrs["color"]))
                    if "stroke_opacity" in attrs:
                        txt.setOpacity(attrs["stroke_opacity"] / 100.0)

                    if isinstance(txt, CustomTextItem):
                        has_b = attrs.get("has_border", txt.has_border)
                        b_col = attrs.get("border_color", txt.border_color)
                        b_wid = attrs.get("border_width", txt.border_width)
                        txt.set_border(has_b, b_col, b_wid)
                        
                        has_l = attrs.get("has_leader", txt.has_leader)
                        l_end = attrs.get("leader_end_point", txt.leader_end_point)
                        txt.set_leader(has_l, l_end)

                if "text" in attrs and attrs["text"].strip() and not text_items and not isinstance(item, QGraphicsTextItem):
                    color_str = item.pen().color().name() if hasattr(item, 'pen') else "#7c4dff"
                    ff = attrs.get("font_family", "Arial")
                    fs = attrs.get("font_size", 12)
                    if fs <= 0:
                        fs = 12
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
                        txt_new.label_offset = QPointF(0, 0)
                        txt_new.setData(0, item_id)
                        txt_new.setData(3, "label")
                        interactive = (self.tool_mode == ToolMode.SELECT)
                        is_editing = (self.editing_label_item_id == item_id)
                        txt_new.setFlag(QGraphicsItem.ItemIsSelectable, interactive and is_editing)
                        txt_new.setFlag(QGraphicsItem.ItemIsMovable, interactive and is_editing)
                
                self.scene.update()
                self.viewport().update()
                break

    def reset_view(self):
        self.resetTransform()
        if self.background_item:
            self.fitInView(self.background_item, Qt.KeepAspectRatio)
        self._emit_zoom_changed()

    def set_zoom_scale(self, target_scale):
        current_zoom = self.transform().m11()
        if current_zoom <= 0 or target_scale <= 0:
            return
        factor = target_scale / current_zoom
        self.scale(factor, factor)
        self._emit_zoom_changed()

    # === Node Editing Implementation ===

    def start_node_editing(self, item_id):
        self.end_node_editing()
        self.editing_node_item_id = item_id
        
        target_item = None
        for item in self.scene.items():
            if item.data(0) == item_id:
                if item.parentItem() and item.parentItem().data(0) == item_id:
                    continue
                target_item = item
                break
        if not target_item:
            return
            
        points = self._get_item_points(target_item)
        if not points:
            return
            
        for i, pt in enumerate(points):
            # Skip the first node (text box position itself) for CustomTextItem
            if isinstance(target_item, CustomTextItem) and i == 0:
                continue
            handle = VertexHandleItem(target_item, i, self)
            local_pt = target_item.mapFromScene(pt)
            handle.setPos(local_pt)
            self.vertex_handles.append(handle)
            
        target_item.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.viewport().update()

    def end_node_editing(self):
        if not self.editing_node_item_id:
            return
        ended_id = self.editing_node_item_id
        self.editing_node_item_id = None
        
        for handle in self.vertex_handles:
            try:
                handle.setParentItem(None)
                self.scene.removeItem(handle)
            except RuntimeError:
                pass
        self.vertex_handles = []
        
        for item in self.scene.items():
            if item.data(0) == ended_id:
                if item.parentItem() and item.parentItem().data(0) == ended_id:
                    continue
                if self.tool_mode == ToolMode.SELECT:
                    item.setFlag(QGraphicsItem.ItemIsMovable, True)
                break
        self.node_edit_ended.emit(ended_id)
        self.viewport().update()

    def start_label_editing(self, item_id):
        self.end_label_editing()
        self.end_node_editing()
        self.editing_label_item_id = item_id
        
        self.scene.clearSelection()
        self._set_items_interactive(False)
        
        target_label = None
        for item in self.scene.items():
            if item.data(0) == item_id:
                if isinstance(item, CustomTextItem) and item.data(3) == "label":
                    target_label = item
                    break
        
        if target_label:
            target_label.setFlag(QGraphicsItem.ItemIsSelectable, True)
            target_label.setFlag(QGraphicsItem.ItemIsMovable, True)
            target_label.setSelected(True)
            target_label.set_border(True, "#7c4dff", 2)
            
        self.viewport().update()

    def end_label_editing(self):
        if not self.editing_label_item_id:
            return
        ended_id = self.editing_label_item_id
        self.editing_label_item_id = None
        
        for item in self.scene.items():
            if item.data(0) == ended_id:
                if isinstance(item, CustomTextItem) and item.data(3) == "label":
                    item.set_border(False)
                    item.setSelected(False)
                    break
                    
        interactive = (self.tool_mode == ToolMode.SELECT)
        self._set_items_interactive(interactive)
        self.viewport().update()

    def _get_item_points(self, item):
        if isinstance(item, QGraphicsLineItem):
            line = item.line()
            return [line.p1(), line.p2()]
        elif isinstance(item, QGraphicsPolygonItem):
            return [p for p in item.polygon()]
        elif isinstance(item, QGraphicsPathItem):
            path = item.path()
            pts = []
            for i in range(path.elementCount()):
                elem = path.elementAt(i)
                pts.append(QPointF(elem.x, elem.y))
            return pts
        elif isinstance(item, CustomTextItem):
            if item.has_leader:
                return [item.pos(), item.leader_end_point]
            else:
                return [item.pos()]
        return []

    def on_vertex_moved(self, item, index, new_pos):
        points = self._get_item_points(item)
        if not points or index >= len(points):
            return
        points[index] = new_pos
        self._update_item_geometry(item, points)

    def _update_item_geometry(self, item, points):
        if isinstance(item, QGraphicsLineItem):
            if len(points) >= 2:
                item.setLine(points[0].x(), points[0].y(), points[1].x(), points[1].y())
                ref_pos = QPointF((points[0].x() + points[1].x()) / 2, (points[0].y() + points[1].y()) / 2)
                for child in item.childItems():
                    if isinstance(child, CustomTextItem) and child.data(3) == "label":
                        offset = getattr(child, "label_offset", QPointF(0, 0))
                        child.setPos(ref_pos + offset)
        elif isinstance(item, QGraphicsPolygonItem):
            item.setPolygon(QPolygonF(points))
            avg_x = sum(p.x() for p in points) / len(points)
            avg_y = sum(p.y() for p in points) / len(points)
            ref_pos = QPointF(avg_x, avg_y)
            for child in item.childItems():
                if isinstance(child, CustomTextItem) and child.data(3) == "label":
                    offset = getattr(child, "label_offset", QPointF(0, 0))
                    child.setPos(ref_pos + offset)
        elif isinstance(item, QGraphicsPathItem):
            path = QPainterPath()
            path.moveTo(points[0])
            for pt in points[1:]:
                path.lineTo(pt)
            item.setPath(path)
            avg_x = sum(p.x() for p in points) / len(points)
            avg_y = sum(p.y() for p in points) / len(points)
            ref_pos = QPointF(avg_x, avg_y)
            for child in item.childItems():
                if isinstance(child, CustomTextItem) and child.data(3) == "label":
                    offset = getattr(child, "label_offset", QPointF(0, 0))
                    child.setPos(ref_pos + offset)
        elif isinstance(item, CustomTextItem):
            if len(points) >= 1:
                item.setPos(points[0])
            if len(points) >= 2 and item.has_leader:
                item.set_leader(True, points[1])

    def on_vertex_double_clicked(self, item, index):
        points = self._get_item_points(item)
        if not points:
            return
        is_polygon = isinstance(item, QGraphicsPolygonItem)
        min_pts = 3 if is_polygon else 2
        if len(points) <= min_pts:
            return
        points.pop(index)
        self._update_item_geometry(item, points)
        self.start_node_editing(item.data(0))
        self.item_points_updated.emit(item.data(0), points)

    def _show_object_context_menu(self, global_pos, item_id):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #1e1e2f; color: white; border: 1px solid #333344; } QMenu::item:selected { background-color: #7c4dff; }")
        edit_action = QAction("📐 頂点を編集", self)
        edit_action.triggered.connect(lambda: self.start_node_editing(item_id))
        menu.addAction(edit_action)
        
        label_action = QAction("🏷️ ラベル位置を調整", self)
        label_action.triggered.connect(lambda: self.start_label_editing(item_id))
        menu.addAction(label_action)
        
        delete_action = QAction("❌ 削除", self)
        delete_action.triggered.connect(lambda: self.request_delete.emit(item_id))
        menu.addAction(delete_action)
        menu.exec(global_pos)

    def _show_vertex_context_menu(self, global_pos, handle_item):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #1e1e2f; color: white; border: 1px solid #333344; } QMenu::item:selected { background-color: #7c4dff; }")
        points = self._get_item_points(handle_item.parent_item)
        is_polygon = isinstance(handle_item.parent_item, QGraphicsPolygonItem)
        min_pts = 3 if is_polygon else 2
        can_delete = len(points) > min_pts
        del_action = QAction("❌ 頂点を削除", self)
        del_action.setEnabled(can_delete)
        del_action.triggered.connect(lambda: self.on_vertex_double_clicked(handle_item.parent_item, handle_item.index))
        menu.addAction(del_action)
        menu.exec(global_pos)

    def _show_edge_context_menu(self, global_pos, item, insert_idx, proj_point):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #1e1e2f; color: white; border: 1px solid #333344; } QMenu::item:selected { background-color: #7c4dff; }")
        add_action = QAction("➕ 頂点を追加", self)
        def do_add():
            pts = self._get_item_points(item)
            pts.insert(insert_idx + 1, proj_point)
            self._update_item_geometry(item, pts)
            self.start_node_editing(item.data(0))
            self.item_points_updated.emit(item.data(0), pts)
        add_action.triggered.connect(do_add)
        menu.addAction(add_action)
        menu.exec(global_pos)

    def _show_edit_exit_context_menu(self, global_pos):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #1e1e2f; color: white; border: 1px solid #333344; } QMenu::item:selected { background-color: #7c4dff; }")
        exit_action = QAction("✅ 編集を終了", self)
        exit_action.triggered.connect(self.end_node_editing)
        menu.addAction(exit_action)
        menu.exec(global_pos)

    def on_vertex_move_finished(self, item):
        points = self._get_item_points(item)
        if points:
            self.item_points_updated.emit(item.data(0), points)

    def _find_closest_edge(self, item, scene_pos):
        points = self._get_item_points(item)
        if not points:
            return -1, None, float('inf')
        
        local_pos = item.mapFromScene(scene_pos)
        best_dist = 15.0 / self.transform().m11()
        best_idx = -1
        best_proj = None
        n = len(points)
        is_polygon = isinstance(item, QGraphicsPolygonItem)
        limit = n if is_polygon else n - 1
        
        for i in range(limit):
            s1 = points[i]
            s2 = points[(i+1)%n]
            dist, proj = point_to_segment_distance(local_pos, s1, s2)
            if dist < best_dist:
                best_dist = dist
                best_idx = i
                best_proj = proj
                
        return best_idx, best_proj, best_dist

    def eventFilter(self, watched, event):
        if self.hover_connection_line is not None:
            try:
                self.hover_connection_line.scene()
            except RuntimeError:
                self.hover_connection_line = None
        if watched == self.scene:
            if event.type() in (QEvent.GraphicsSceneHoverEnter, QEvent.GraphicsSceneHoverMove):
                pos = event.scenePos()
                item = self.scene.itemAt(pos, self.transform())
                
                shape_item = None
                label_item = None
                
                if item and item != self.background_item:
                    if isinstance(item, CustomTextItem) and item.data(3) == "label":
                        label_item = item
                        shape_item = item.parentItem()
                    elif item.data(0):
                        shape_item = item
                        for child in item.childItems():
                            if isinstance(child, CustomTextItem) and child.data(3) == "label":
                                label_item = child
                                break
                                
                if shape_item and label_item:
                    ref_pos = self._get_shape_ref_pos(shape_item)
                    if ref_pos is not None:
                        offset = getattr(label_item, "label_offset", QPointF(0, 0))
                        if offset.x() != 0 or offset.y() != 0:
                            ref_scene_pos = shape_item.mapToScene(ref_pos)
                            label_br = label_item.boundingRect()
                            label_scene_center = label_item.mapToScene(label_br.center())
                            
                            if not self.hover_connection_line:
                                self.hover_connection_line = QGraphicsLineItem()
                                pen = QPen(label_item.defaultTextColor(), 1.25, Qt.DashLine)
                                pen.setCosmetic(True)
                                self.hover_connection_line.setPen(pen)
                                self.hover_connection_line.setZValue(10)
                                self.scene.addItem(self.hover_connection_line)
                            
                            self.hover_connection_line.setLine(
                                label_scene_center.x(), label_scene_center.y(),
                                ref_scene_pos.x(), ref_scene_pos.y()
                            )
                            self.hover_connection_line.setVisible(True)
                            return super().eventFilter(watched, event)
                            
                if self.hover_connection_line:
                    self.hover_connection_line.setVisible(False)
                    
            elif event.type() == QEvent.GraphicsSceneHoverLeave:
                if self.hover_connection_line:
                    self.hover_connection_line.setVisible(False)
                    
        return super().eventFilter(watched, event)

    def _get_shape_ref_pos(self, item):
        if isinstance(item, QGraphicsLineItem):
            line = item.line()
            return QPointF((line.x1() + line.x2()) / 2, (line.y1() + line.y2()) / 2)
        elif isinstance(item, QGraphicsPolygonItem):
            poly = item.polygon()
            if poly.isEmpty():
                return None
            avg_x = sum(p.x() for p in poly) / len(poly)
            avg_y = sum(p.y() for p in poly) / len(poly)
            return QPointF(avg_x, avg_y)
        elif isinstance(item, QGraphicsPathItem):
            path = item.path()
            n = path.elementCount()
            if n == 0:
                return None
            pts = []
            for i in range(n):
                elem = path.elementAt(i)
                pts.append(QPointF(elem.x, elem.y))
            avg_x = sum(p.x() for p in pts) / len(pts)
            avg_y = sum(p.y() for p in pts) / len(pts)
            return QPointF(avg_x, avg_y)
        elif isinstance(item, QGraphicsEllipseItem):
            r = item.rect()
            cx = r.center().x()
            cy = r.center().y()
            radius = r.width() / 2
            return QPointF(cx, cy - radius - 10)
        return None
