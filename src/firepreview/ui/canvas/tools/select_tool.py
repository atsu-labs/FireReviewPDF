from PySide6.QtCore import Qt, QPointF
from PySide6.QtWidgets import QGraphicsLineItem, QGraphicsPathItem, QGraphicsPolygonItem, QGraphicsItem, QGraphicsEllipseItem
from .base_tool import BaseCanvasTool
from ..items import VertexHandleItem, CustomTextItem

class SelectTool(BaseCanvasTool):
    def mouse_press(self, event, scene):
        pos = self.canvas.mapToScene(event.pos())

        if event.button() == Qt.RightButton:
            if self.canvas.editing_node_item_id:
                clicked_item = scene.itemAt(pos, self.canvas.transform())
                if isinstance(clicked_item, VertexHandleItem):
                    self.canvas._show_vertex_context_menu(event.globalPosition().toPoint(), clicked_item)
                    event.accept()
                    return True
                
                # Check closest edge to insert node
                target_item = self.canvas.annotation_items.get(self.canvas.editing_node_item_id)
                if target_item:
                    best_idx, best_proj, best_dist = self.canvas._find_closest_edge(target_item, pos)
                    if best_idx != -1:
                        self.canvas._show_edge_context_menu(event.globalPosition().toPoint(), target_item, best_idx, best_proj)
                        event.accept()
                        return True
                
                self.canvas._show_edit_exit_context_menu(event.globalPosition().toPoint())
                event.accept()
                return True
            else:
                item = scene.itemAt(pos, self.canvas.transform())
                while item and not item.data(0) and item.parentItem():
                    item = item.parentItem()
                if item and item != self.canvas.background_item and item.data(0):
                    if isinstance(item, (QGraphicsLineItem, QGraphicsPathItem, QGraphicsPolygonItem, QGraphicsEllipseItem)):
                        self.canvas._show_object_context_menu(event.globalPosition().toPoint(), item.data(0))
                        event.accept()
                        return True

        elif event.button() == Qt.LeftButton:
            item = scene.itemAt(pos, self.canvas.transform())
            
            # If editing label and clicked outside, finish label editing
            if self.canvas.editing_label_item_id:
                clicked_target = item
                is_label_target = False
                while clicked_target:
                    if clicked_target.data(3) == "label" and clicked_target.data(0) == self.canvas.editing_label_item_id:
                        is_label_target = True
                        break
                    clicked_target = clicked_target.parentItem()
                if not is_label_target:
                    self.canvas.end_label_editing()
                    item = scene.itemAt(pos, self.canvas.transform())

            # If editing nodes and clicked outside, finish node editing
            if self.canvas.editing_node_item_id:
                clicked_target = item
                is_edit_target = False
                while clicked_target:
                    if isinstance(clicked_target, VertexHandleItem):
                        is_edit_target = True
                        break
                    if clicked_target.data(0) == self.canvas.editing_node_item_id:
                        is_edit_target = True
                        break
                    clicked_target = clicked_target.parentItem()
                
                if not is_edit_target:
                    target_item = self.canvas.annotation_items.get(self.canvas.editing_node_item_id)
                    if target_item:
                        best_idx, _, _ = self.canvas._find_closest_edge(target_item, pos)
                        if best_idx != -1:
                            is_edit_target = True
                                    
                if not is_edit_target:
                    self.canvas.end_node_editing()
                    item = scene.itemAt(pos, self.canvas.transform())
            
            # If the clicked item is a label, check if we are in label editing state
            if item and isinstance(item, CustomTextItem) and item.data(3) == "label":
                if self.canvas.editing_label_item_id != item.data(0):
                    # Redirect to parent shape in normal select mode!
                    item = item.parentItem()

            # Select item directly if hit
            while item and not item.data(0) and item.parentItem():
                item = item.parentItem()
            
            if item and item != self.canvas.background_item and item.data(0):
                scene.clearSelection()
                item.setSelected(True)
                self.canvas.item_selected.emit(item.data(0))
                self.canvas.viewport().update()
                
                # Check for moving support: store initial position for delta calculation
                item.setData(1, item.pos())
                return False  # Let standard QGraphicsView handle drag initiation

            scene.clearSelection()
            self.canvas.selection_cleared.emit()
            self.canvas.viewport().update()

        return False

    def mouse_release(self, event, scene):
        if event.button() == Qt.LeftButton:
            # Check if any item moved and emit signals
            for item in scene.selectedItems():
                item_id = item.data(0)
                last_pos = item.data(1)
                if item_id and last_pos is not None:
                    delta = item.pos() - last_pos
                    if not delta.isNull():
                        if isinstance(item, CustomTextItem) and item.data(3) == "label":
                            item.label_offset = getattr(item, "label_offset", QPointF(0, 0)) + delta
                            item.setData(1, item.pos())
                            self.canvas.label_moved.emit(item_id, delta)
                        else:
                            if isinstance(item, (QGraphicsLineItem, QGraphicsPathItem, QGraphicsPolygonItem)):
                                points = self.canvas._get_item_points(item)
                                if points:
                                    moved_points = [p + delta for p in points]
                                    item.setPos(0, 0)
                                    self.canvas._update_item_geometry(item, moved_points)
                                if item.data(4) == "arc":
                                    center = item.data(5)
                                    item.setData(5, center + delta)
                                    item.setPos(0, 0)
                                    self.canvas.update_item_properties(item_id, {})
                                item.setData(1, QPointF(0, 0))
                            else:
                                item.setData(1, item.pos())
                            
                            self.canvas.item_moved.emit(item_id, delta)
            
            scene.update()
            self.canvas.viewport().update()

    def double_click(self, event, scene):
        if self.canvas.editing_node_item_id and event.button() == Qt.LeftButton:
            pos = self.canvas.mapToScene(event.pos())
            item = self.canvas.annotation_items.get(self.canvas.editing_node_item_id)
            if item:
                best_idx, best_proj, _ = self.canvas._find_closest_edge(item, pos)
                if best_idx != -1:
                    points = self.canvas._get_item_points(item)
                    points.insert(best_idx + 1, best_proj)
                    self.canvas._update_item_geometry(item, points)
                    self.canvas.start_node_editing(self.canvas.editing_node_item_id)
                    self.canvas.item_points_updated.emit(self.canvas.editing_node_item_id, points)
                    event.accept()
                    return True
        return False
