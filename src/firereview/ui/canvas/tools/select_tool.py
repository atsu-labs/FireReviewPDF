from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPen, QColor, QBrush
from PySide6.QtWidgets import (
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsPolygonItem,
    QGraphicsItem,
    QGraphicsEllipseItem,
    QGraphicsRectItem,
)
from .base_tool import BaseCanvasTool
from ..items import VertexHandleItem, CustomTextItem


class SelectTool(BaseCanvasTool):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.rubberband_item = None
        self.rubberband_start_pos = None
        self.rubberband_mode = "replace"  # "replace" | "add" | "exclude"
        self.rubberband_initial_ids = set()
        self._dragging_items = False
        self._drag_start_scene_pos = None
        self._drag_initial_positions = {}
        self._pending_single_select_item = None

    def _clear_rubberband(self, scene=None):
        target_scene = scene or getattr(self.canvas, "scene", None)
        if self.rubberband_item is not None:
            if target_scene is not None:
                try:
                    target_scene.removeItem(self.rubberband_item)
                except RuntimeError:
                    pass
            self.rubberband_item = None
        self.rubberband_start_pos = None
        self.rubberband_initial_ids = set()

    def _reset_drag_state(self, scene=None):
        self._clear_rubberband(scene)
        self._dragging_items = False
        self._drag_start_scene_pos = None
        self._drag_initial_positions = {}
        self._pending_single_select_item = None

    def _item_at(self, scene, pos: QPointF):
        items = scene.items(pos, Qt.IntersectsItemShape, Qt.DescendingOrder, self.canvas.transform())
        for it in items:
            if it == self.rubberband_item or it == self.canvas.hover_connection_line:
                continue
            if self.canvas._is_background_layer_item(it):
                continue
            return it
        return None

    def _resolve_selectable_item(self, item):
        if (
            item is None
            or self.canvas._is_background_layer_item(item)
            or item == self.rubberband_item
            or item == self.canvas.hover_connection_line
        ):
            return None
        if isinstance(item, VertexHandleItem):
            return item

        if isinstance(item, CustomTextItem) and item.data(3) == "label":
            if self.canvas.editing_label_item_id == item.data(0):
                return item
            item = item.parentItem()

        while item and item.parentItem():
            if (
                self.canvas.editing_label_item_id
                and isinstance(item, CustomTextItem)
                and item.data(3) == "label"
                and item.data(0) == self.canvas.editing_label_item_id
            ):
                break
            item = item.parentItem()

        if item and not self.canvas._is_background_layer_item(item) and item.data(0):
            return item
        return None

    def _store_selected_initial_positions(self, scene):
        for sel in scene.selectedItems():
            if not self.canvas._is_background_layer_item(sel):
                sel.setData(1, sel.pos())

    def _emit_selection_state(self):
        selected_ids = self.canvas.get_selected_annotation_ids()
        self.canvas.selection_changed.emit(selected_ids)
        if len(selected_ids) == 1:
            self.canvas.item_selected.emit(selected_ids[0])
        elif len(selected_ids) == 0:
            self.canvas.selection_cleared.emit()

    def _get_annotation_ids_in_rect(self, scene, rect: QRectF) -> set:
        hit_ids = set()
        if rect.isEmpty():
            return hit_ids
        items = scene.items(rect, Qt.IntersectsItemShape, Qt.DescendingOrder, self.canvas.transform())
        for raw_item in items:
            target = self._resolve_selectable_item(raw_item)
            if target is None or isinstance(target, VertexHandleItem):
                continue
            if isinstance(target, CustomTextItem) and target.data(3) == "label":
                continue
            if not (target.flags() & QGraphicsItem.ItemIsSelectable):
                continue
            iid = target.data(0)
            if iid:
                hit_ids.add(iid)
        return hit_ids

    def _apply_selection_ids(self, scene, target_ids: set):
        scene.clearSelection()
        for iid, item in self.canvas.annotation_items.items():
            if iid in target_ids and (item.flags() & QGraphicsItem.ItemIsSelectable):
                item.setSelected(True)

    def mouse_press(self, event, scene):
        pos = self.canvas.mapToScene(event.pos())

        if event.button() == Qt.RightButton:
            if self.canvas.editing_node_item_id:
                clicked_item = self._item_at(scene, pos)
                if isinstance(clicked_item, VertexHandleItem):
                    self.canvas._show_vertex_context_menu(event.globalPosition().toPoint(), clicked_item)
                    event.accept()
                    return True

                # Check closest edge to insert node
                target_item = self.canvas.annotation_items.get(self.canvas.editing_node_item_id)
                if target_item:
                    best_idx, best_proj, _best_dist = self.canvas._find_closest_edge(target_item, pos)
                    if best_idx != -1:
                        self.canvas._show_edge_context_menu(
                            event.globalPosition().toPoint(), target_item, best_idx, best_proj
                        )
                        event.accept()
                        return True

                self.canvas._show_edit_exit_context_menu(event.globalPosition().toPoint())
                event.accept()
                return True
            else:
                raw_item = self._item_at(scene, pos)
                item = self._resolve_selectable_item(raw_item)
                if item and not isinstance(item, VertexHandleItem) and item.data(0):
                    item_id = item.data(0)
                    selected_ids = self.canvas.get_selected_annotation_ids()
                    if item.isSelected() and len(selected_ids) > 1:
                        self.canvas._show_multi_object_context_menu(
                            event.globalPosition().toPoint(), selected_ids
                        )
                        event.accept()
                        return True
                    else:
                        if not item.isSelected() or len(selected_ids) != 1:
                            scene.clearSelection()
                            item.setSelected(True)
                            self._store_selected_initial_positions(scene)
                            self._emit_selection_state()
                            self.canvas.viewport().update()
                        self.canvas._show_object_context_menu(event.globalPosition().toPoint(), item_id)
                        event.accept()
                        return True

        elif event.button() == Qt.LeftButton:
            self._reset_drag_state(scene)
            item = self._item_at(scene, pos)

            # Clear text editor focus if clicking outside the focused CustomTextItem
            focus_item = scene.focusItem()
            if isinstance(focus_item, CustomTextItem) and item != focus_item:
                focus_item.clearFocus()

            # If editing label and clicked outside, finish label editing
            if self.canvas.editing_label_item_id:
                clicked_target = item
                is_label_target = False
                while clicked_target:
                    if (
                        clicked_target.data(3) == "label"
                        and clicked_target.data(0) == self.canvas.editing_label_item_id
                    ):
                        is_label_target = True
                        break
                    clicked_target = clicked_target.parentItem()
                if not is_label_target:
                    self.canvas.end_label_editing()
                    item = self._item_at(scene, pos)

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
                    item = self._item_at(scene, pos)

            # VertexHandleItem or active text editor should be handled by standard QGraphicsScene
            if isinstance(item, VertexHandleItem):
                return False
            if isinstance(item, CustomTextItem) and (
                item.textInteractionFlags() & Qt.TextEditorInteraction
            ):
                return False

            target_item = self._resolve_selectable_item(item)
            modifiers = event.modifiers()
            is_toggle_mod = bool(modifiers & (Qt.ShiftModifier | Qt.ControlModifier))
            is_alt_mod = bool(modifiers & Qt.AltModifier)

            # 1. Clicked on an annotation item (or active label)
            if target_item is not None and (target_item.flags() & QGraphicsItem.ItemIsSelectable):
                if is_toggle_mod:
                    target_item.setSelected(not target_item.isSelected())
                    self._store_selected_initial_positions(scene)
                    self._emit_selection_state()
                    self.canvas.viewport().update()
                    return True

                if is_alt_mod:
                    if target_item.isSelected():
                        target_item.setSelected(False)
                        self._store_selected_initial_positions(scene)
                        self._emit_selection_state()
                        self.canvas.viewport().update()
                    return True

                # Normal click / press without modifier
                selected_ids = self.canvas.get_selected_annotation_ids()
                if target_item.isSelected() and len(selected_ids) > 1:
                    # Keep multi-selection for potential group drag; collapse on release if not moved
                    self._pending_single_select_item = target_item
                else:
                    scene.clearSelection()
                    target_item.setSelected(True)
                    self._emit_selection_state()

                self._store_selected_initial_positions(scene)
                self._dragging_items = True
                self._drag_start_scene_pos = pos
                self._drag_initial_positions = {
                    sel: sel.pos()
                    for sel in scene.selectedItems()
                    if not self.canvas._is_background_layer_item(sel)
                    and (sel.flags() & QGraphicsItem.ItemIsMovable)
                }
                self.canvas.viewport().update()
                return True

            # 2. Clicked on empty background / PDF background -> start rubberband selection
            if is_toggle_mod:
                self.rubberband_mode = "add"
            elif is_alt_mod:
                self.rubberband_mode = "exclude"
            else:
                self.rubberband_mode = "replace"
                if scene.selectedItems():
                    scene.clearSelection()
                    self._emit_selection_state()

            self.rubberband_start_pos = pos
            self.rubberband_initial_ids = set(self.canvas.get_selected_annotation_ids())

            self.rubberband_item = QGraphicsRectItem(QRectF(pos, pos))
            if self.rubberband_mode == "exclude":
                pen = QPen(QColor("#ff5252"), 1.5, Qt.DashLine)
                brush = QBrush(QColor(255, 82, 82, 35))
            else:
                pen = QPen(QColor("#7c4dff"), 1.5, Qt.DashLine)
                brush = QBrush(QColor(124, 77, 255, 35))
            pen.setCosmetic(True)
            self.rubberband_item.setPen(pen)
            self.rubberband_item.setBrush(brush)
            self.rubberband_item.setZValue(1000)
            self.rubberband_item.setFlag(QGraphicsItem.ItemIsSelectable, False)
            self.rubberband_item.setFlag(QGraphicsItem.ItemIsMovable, False)
            self.rubberband_item.setAcceptedMouseButtons(Qt.NoButton)
            scene.addItem(self.rubberband_item)

            self.canvas.viewport().update()
            return True

        return False

    def mouse_move(self, event, scene):
        pos = self.canvas.mapToScene(event.pos())

        # 1. Dragging selected items
        if self._dragging_items and self._drag_start_scene_pos is not None:
            if not (event.buttons() & Qt.LeftButton):
                return False
            delta = pos - self._drag_start_scene_pos
            for item, init_pos in self._drag_initial_positions.items():
                item.setPos(init_pos + delta)
            self.canvas.viewport().update()
            return True

        # 2. Updating rubberband selection rectangle
        if self.rubberband_start_pos is not None and self.rubberband_item is not None:
            rect = QRectF(self.rubberband_start_pos, pos).normalized()
            self.rubberband_item.setRect(rect)

            hit_ids = self._get_annotation_ids_in_rect(scene, rect)
            if self.rubberband_mode == "replace":
                new_ids = hit_ids
            elif self.rubberband_mode == "add":
                new_ids = self.rubberband_initial_ids | hit_ids
            elif self.rubberband_mode == "exclude":
                new_ids = self.rubberband_initial_ids - hit_ids
            else:
                new_ids = hit_ids

            self._apply_selection_ids(scene, new_ids)
            self.canvas.viewport().update()
            return True

        return False

    def mouse_release(self, event, scene):
        if event.button() == Qt.LeftButton:
            # 1. Finish rubberband selection
            if self.rubberband_item is not None and self.rubberband_start_pos is not None:
                pos = self.canvas.mapToScene(event.pos())
                rect = QRectF(self.rubberband_start_pos, pos).normalized()
                mode = self.rubberband_mode
                initial_ids = set(self.rubberband_initial_ids)
                self._clear_rubberband(scene)

                if rect.width() > 2 or rect.height() > 2:
                    hit_ids = self._get_annotation_ids_in_rect(scene, rect)
                    if mode == "replace":
                        new_ids = hit_ids
                    elif mode == "add":
                        new_ids = initial_ids | hit_ids
                    elif mode == "exclude":
                        new_ids = initial_ids - hit_ids
                    else:
                        new_ids = hit_ids
                    self._apply_selection_ids(scene, new_ids)
                else:
                    if mode == "replace":
                        scene.clearSelection()
                    else:
                        self._apply_selection_ids(scene, initial_ids)

                self._store_selected_initial_positions(scene)
                self._emit_selection_state()
                self._reset_drag_state(scene)
                scene.update()
                self.canvas.viewport().update()
                return True

            # 2. Check if any selected item moved and emit signals
            moved_items = []
            moved_labels = []
            selected_list = [
                it for it in scene.selectedItems() if not self.canvas._is_background_layer_item(it)
            ]

            for item in selected_list:
                item_id = item.data(0)
                last_pos = item.data(1)
                if item_id and last_pos is not None:
                    delta = item.pos() - last_pos
                    if not delta.isNull():
                        if isinstance(item, CustomTextItem) and item.data(3) == "label":
                            item.label_offset = getattr(item, "label_offset", QPointF(0, 0)) + delta
                            item.setData(1, item.pos())
                            moved_labels.append((item_id, delta))
                        else:
                            if isinstance(
                                item, (QGraphicsLineItem, QGraphicsPathItem, QGraphicsPolygonItem)
                            ):
                                points = self.canvas._get_item_points(item)
                                if points:
                                    moved_points = [p + delta for p in points]
                                    item.setPos(0, 0)
                                    self.canvas._update_item_geometry(item, moved_points)
                                if item.data(4) == "arc":
                                    center = item.data(5)
                                    item.setData(5, center + delta)
                                    item.setPos(0, 0)
                                    self.canvas.update_item_properties(
                                        item_id, {"center_marker": item.data(10) or ""}
                                    )
                                item.setData(1, QPointF(0, 0))
                            else:
                                item.setData(1, item.pos())

                            moved_items.append((item_id, delta))

            for item_id, delta in moved_labels:
                self.canvas.label_moved.emit(item_id, delta)

            if len(moved_items) == 1:
                self.canvas.item_moved.emit(moved_items[0][0], moved_items[0][1])
            elif len(moved_items) > 1:
                # Preserve deterministic order according to canvas.annotation_items
                moved_map = {iid: d for iid, d in moved_items}
                ordered_ids = [
                    iid for iid in self.canvas.annotation_items.keys() if iid in moved_map
                ]
                for iid, _ in moved_items:
                    if iid not in ordered_ids:
                        ordered_ids.append(iid)
                self.canvas.items_moved.emit(ordered_ids, moved_items[0][1])

            # 3. If clicked on one item of a multi-selection without dragging, collapse to single selection
            if not moved_items and not moved_labels and self._pending_single_select_item is not None:
                target = self._pending_single_select_item
                scene.clearSelection()
                target.setSelected(True)
                self._store_selected_initial_positions(scene)
                self._emit_selection_state()

            self._reset_drag_state(scene)
            scene.update()
            self.canvas.viewport().update()
            return True

        return False

    def double_click(self, event, scene):
        if event.button() == Qt.LeftButton:
            pos = self.canvas.mapToScene(event.pos())
            if self.canvas.editing_node_item_id:
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
            else:
                raw_item = self._item_at(scene, pos)
                if isinstance(raw_item, CustomTextItem) and (
                    raw_item.flags() & QGraphicsItem.ItemIsSelectable
                ):
                    raw_item.setTextInteractionFlags(Qt.TextEditorInteraction)
                    raw_item.setFocus()
                    event.accept()
                    return True
        return False
