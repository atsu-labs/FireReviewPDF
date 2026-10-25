from typing import Any, Callable, Dict, Optional
from PySide6.QtCore import QPointF
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QMessageBox

from firereview.models import Annotation, BaseAnnotation
from firereview.services.document_manager import DocumentManager
from firereview.services.measurement_service import MeasurementService
from firereview.controllers.tool_controller import ToolController
from firereview.controllers.undo_commands import (
    AddCommand,
    RemoveCommand,
    MoveCommand,
    PropertyChangeCommand,
    BatchMoveCommand,
    BatchRemoveCommand,
    _clone_points,
    _clone_value,
)
from firereview.ui.canvas.enums import ToolMode


class CanvasController:
    """描画キャンバスのイベント処理・アイテム生成・モデル同期を統括するコントローラー"""

    def __init__(
        self,
        canvas,
        document_manager: DocumentManager,
        measurement_service: MeasurementService,
        tool_controller: ToolController,
        prop_panel,
        navigator,
        get_current_page_fn: Callable[[], int],
        get_current_scale_factor_fn: Callable[[], float],
        is_current_page_calibrated_fn: Callable[[], bool],
        set_tool_fn: Callable[[ToolMode], None],
        go_to_page_fn: Optional[Callable[[int], None]] = None,
        undo_stack: Optional[QUndoStack] = None,
        parent_widget=None,
    ):
        self.canvas = canvas
        self.document_manager = document_manager
        self.measurement_service = measurement_service
        self.tool_controller = tool_controller
        self.prop_panel = prop_panel
        self.navigator = navigator
        self.get_current_page_fn = get_current_page_fn
        self.get_current_scale_factor_fn = get_current_scale_factor_fn
        self.is_current_page_calibrated_fn = is_current_page_calibrated_fn
        self.set_tool_fn = set_tool_fn
        self.go_to_page_fn = go_to_page_fn
        self.undo_stack = undo_stack if undo_stack is not None else QUndoStack()
        self.parent_widget = parent_widget

        self._tracked_model_id = id(self.document_manager.model)
        self.document_manager.document_changed.connect(self._on_document_changed)

    def _on_document_changed(self):
        """新規PDFやプロジェクト読込でDrawingModelインスタンスが置き換わった際にUndo履歴をクリアする"""
        current_model_id = id(self.document_manager.model)
        if current_model_id != self._tracked_model_id:
            self._tracked_model_id = current_model_id
            self.undo_stack.clear()

    @property
    def model(self):
        return self.document_manager.model

    @property
    def current_page(self) -> int:
        return self.get_current_page_fn()

    # --- Undo / Redo 操作 ---
    def undo(self):
        """直前の注釈操作を取り消す"""
        if self.undo_stack.canUndo():
            self.undo_stack.undo()

    def redo(self):
        """取り消した注釈操作をやり直す"""
        if self.undo_stack.canRedo():
            self.undo_stack.redo()

    def clear_undo_stack(self):
        """Undo/Redo履歴をすべてクリアする"""
        self.undo_stack.clear()

    def _ensure_page(self, target_page: int):
        """対象ページが現在のページと異なる場合、対象ページへ遷移する"""
        if self.current_page != target_page and self.go_to_page_fn is not None:
            self.go_to_page_fn(target_page)

    def _find_annotation(self, item_id: str) -> Optional[BaseAnnotation]:
        for ann in self.model.annotations:
            if ann.id == item_id:
                return ann
        return None

    def _create_annotation(
        self, type_name: str, points, real_value: float = 0.0, text: str = ""
    ) -> Annotation:
        ann = Annotation(type_name)
        ann.points = _clone_points(points) if points else []
        ann.real_value = real_value
        ann.text = text
        ann.page_num = self.current_page
        return ann

    def add_to_model(
        self, type_name: str, points, real_value: float = 0.0, text: str = ""
    ) -> Annotation:
        """モデルにアノテーションを追加し、ダーティフラグを立てる（Undo履歴対応）"""
        ann = self._create_annotation(type_name, points, real_value=real_value, text=text)
        self.undo_stack.push(AddCommand(self, ann, render_on_first_redo=False))
        return ann

    # --- 描画完了イベントハンドラ群 ---
    def on_polygon_complete(self, points):
        ann = self._create_annotation("polygon", points, real_value=0.0, text="")
        ann.color = self.tool_controller.current_shape_color
        ann.line_width = self.tool_controller.current_line_width
        ann.fill_color = self.tool_controller.current_fill_color
        ann.fill_opacity = self.tool_controller.current_fill_opacity
        self.undo_stack.push(AddCommand(self, ann, description="矩形・多角形の追加"))

    def on_cloud_complete(self, points):
        ann = self._create_annotation("cloud", points, real_value=0.0, text="")
        ann.color = self.tool_controller.current_cloud_color
        ann.line_width = self.tool_controller.current_cloud_line_width
        ann.fill_color = self.tool_controller.current_cloud_fill_color
        ann.fill_opacity = self.tool_controller.current_cloud_fill_opacity
        self.undo_stack.push(AddCommand(self, ann, description="雲マークの追加"))

    def on_polyline_complete(self, points):
        ann = self._create_annotation("polyline", points, real_value=0.0, text="")
        ann.color = self.tool_controller.current_shape_color
        ann.line_width = self.tool_controller.current_line_width
        ann.start_marker = self.tool_controller.current_start_marker
        ann.end_marker = self.tool_controller.current_end_marker
        self.undo_stack.push(AddCommand(self, ann, description="直線・折れ線の追加"))

    def on_circle_drag_complete(self, center, radius_px, spin_radius_val=None):
        current_scale_factor = self.get_current_scale_factor_fn()
        if radius_px < 3:
            if spin_radius_val is None and self.tool_controller and self.tool_controller.options_bar:
                spin_radius_val = self.tool_controller.options_bar.tool_radius_spin.value()
            if self.is_current_page_calibrated_fn() and current_scale_factor > 0 and spin_radius_val is not None:
                options_bar = getattr(self.tool_controller, "options_bar", None) if self.tool_controller else None
                radius_unit = getattr(options_bar, "unit", self.model.unit) if options_bar else self.model.unit
                if radius_unit == 'm':
                    radius_mm = spin_radius_val * 1000
                else:
                    radius_mm = spin_radius_val
                radius_px = radius_mm / current_scale_factor
            else:
                if self.parent_widget:
                    QMessageBox.warning(
                        self.parent_widget,
                        "警告",
                        "半径を指定して円を描画するには、先にキャリブレーションを行ってください。",
                    )
                return

        ann = self._create_annotation("circle", [center], real_value=0.0, text="")
        ann.color = self.tool_controller.current_shape_color
        ann.line_width = self.tool_controller.current_line_width
        ann.fill_color = self.tool_controller.current_fill_color
        ann.fill_opacity = self.tool_controller.current_fill_opacity
        ann.radius_px = radius_px
        ann.center_marker = self.tool_controller.current_center_marker
        self.undo_stack.push(AddCommand(self, ann, description="円の追加"))

    def on_arc_drag_complete(self, center, radius_px, drag_angle):
        ann = self._create_annotation("arc", [center], real_value=0.0, text="")
        ann.color = self.tool_controller.current_shape_color
        ann.line_width = self.tool_controller.current_line_width
        ann.radius_px = radius_px
        ann.center_marker = self.tool_controller.current_center_marker
        ann.drag_angle = drag_angle
        ann.arc_span = self.tool_controller.current_arc_span
        ann.show_radial_line = self.tool_controller.current_arc_show_radial_line
        self.undo_stack.push(AddCommand(self, ann, description="円弧の追加"))

    def on_marker_complete(self, pos, continuous: Optional[bool] = None):
        ann = self._create_annotation("marker", [pos])
        ann.color = self.tool_controller.current_marker_color
        ann.marker_style = self.tool_controller.current_marker_style
        ann.stroke_opacity = self.tool_controller.current_marker_opacity

        self.undo_stack.push(AddCommand(self, ann, description="マーカーの追加"))

        if continuous is None:
            if self.tool_controller and self.tool_controller.options_bar:
                continuous = self.tool_controller.options_bar.tool_marker_continuous_check.isChecked()
            else:
                continuous = False

        if not continuous:
            self.set_tool_fn(ToolMode.SELECT)

    def on_legend_complete(self, pos):
        ann = self._create_annotation("legend", [pos])
        ann.font_family = self.tool_controller.current_text_font
        ann.font_size = self.tool_controller.current_text_size
        ann.color = self.tool_controller.current_text_color

        self.undo_stack.push(AddCommand(self, ann, description="凡例の追加"))
        self.set_tool_fn(ToolMode.SELECT)

    def on_color_name_changed(self, page_num: int, color_hex: str, new_name: str):
        if not hasattr(self.model, 'page_color_names'):
            self.model.page_color_names = {}
        if page_num not in self.model.page_color_names:
            self.model.page_color_names[page_num] = {}

        color_key = color_hex.lower()
        old_name = self.model.page_color_names[page_num].get(color_key, "")
        if old_name == new_name:
            return

        self.model.page_color_names[page_num][color_key] = new_name

        # キャンバス上の凡例を再描画
        if self.canvas:
            marker_counts = {}
            for ann in self.model.annotations:
                if ann.page_num == self.current_page and ann.type == 'marker':
                    style = getattr(ann, 'marker_style', 'square')
                    color = (ann.color or "#7c4dff").lower()
                    key = (style, color)
                    marker_counts[key] = marker_counts.get(key, 0) + 1

            self.canvas.update_legends(marker_counts, self.model.page_color_names[page_num])

        self.update_object_panel()
        self.document_manager.set_dirty(True)

    def on_text_editing_finished(self, pos, text, item_id, font_family, font_size, color):
        if not item_id:
            ann = self._create_annotation("text", [pos], text=text)
            ann.font_family = font_family
            ann.font_size = font_size
            ann.color = color
            self.undo_stack.push(AddCommand(self, ann, description="テキストの追加"))
        else:
            ann = self._find_annotation(item_id)
            if not ann:
                return
            old_attrs = {
                "text": ann.text,
                "points": _clone_points(ann.points),
                "font_family": ann.font_family,
                "font_size": ann.font_size,
                "color": ann.color,
            }
            new_attrs = {
                "text": text,
                "points": [QPointF(pos.x(), pos.y())],
                "font_family": font_family,
                "font_size": font_size,
                "color": color,
            }
            self.undo_stack.push(
                PropertyChangeCommand(
                    self, item_id, old_attrs, new_attrs, allow_merge=False, description="テキストの編集"
                )
            )

    def on_existing_text_edited(self, item_id: str, new_text: str):
        ann = self._find_annotation(item_id)
        if not ann or ann.text == new_text:
            return

        old_attrs = {"text": ann.text}
        new_attrs = {"text": new_text}
        self.undo_stack.push(
            PropertyChangeCommand(
                self, item_id, old_attrs, new_attrs, allow_merge=False, description="テキストの編集"
            )
        )

        if hasattr(self.prop_panel, 'current_item_id') and self.prop_panel.current_item_id == item_id:
            self.prop_panel._block_signals = True
            if hasattr(self.prop_panel.text_edit, 'setPlainText'):
                self.prop_panel.text_edit.setPlainText(new_text)
            else:
                self.prop_panel.text_edit.setText(new_text)
            self.prop_panel._block_signals = False

    def _refresh_prop_panel_if_selected(self, ann: BaseAnnotation):
        """対象注釈がプロパティパネルで選択中の場合、パネル表示を最新状態に更新する"""
        if hasattr(self.prop_panel, "current_item_id") and self.prop_panel.current_item_id == ann.id:
            self.prop_panel.set_item_data(
                ann.id, ann.type, ann.text, ann.color,
                ann.font_family, ann.font_size, ann.line_width,
                stroke_opacity=ann.stroke_opacity, fill_opacity=ann.fill_opacity,
                fill_color=ann.fill_color,
                center_marker=ann.center_marker, start_marker=ann.start_marker, end_marker=ann.end_marker,
                has_border=getattr(ann, "has_border", False),
                border_color=getattr(ann, "border_color", "#ff0000"),
                border_width=getattr(ann, "border_width", 2),
                has_leader=getattr(ann, "has_leader", False),
                marker_style=getattr(ann, "marker_style", "square"),
                arc_span=getattr(ann, "arc_span", 30.0),
                show_radial_line=getattr(ann, "show_radial_line", False),
            )
            if getattr(self.canvas, "editing_node_item_id", None) == ann.id and hasattr(
                self.prop_panel, "set_node_edit_active"
            ):
                self.prop_panel.set_node_edit_active(True)

    def on_item_selected(self, item_id: str):
        ann = self._find_annotation(item_id)
        if ann:
            self.prop_panel.set_item_data(
                ann.id, ann.type, ann.text, ann.color,
                ann.font_family, ann.font_size, ann.line_width,
                stroke_opacity=ann.stroke_opacity, fill_opacity=ann.fill_opacity,
                fill_color=ann.fill_color,
                center_marker=ann.center_marker, start_marker=ann.start_marker, end_marker=ann.end_marker,
                has_border=getattr(ann, "has_border", False),
                border_color=getattr(ann, "border_color", "#ff0000"),
                border_width=getattr(ann, "border_width", 2),
                has_leader=getattr(ann, "has_leader", False),
                marker_style=getattr(ann, "marker_style", "square"),
                arc_span=getattr(ann, "arc_span", 30.0),
                show_radial_line=getattr(ann, "show_radial_line", False),
            )
            self.navigator.set_selected_object(item_id)

    def on_selection_cleared(self):
        self.prop_panel.clear_panel()
        self.navigator.set_selected_object(None)

    def on_selection_changed(self, item_ids: list):
        if not item_ids:
            self.on_selection_cleared()
        elif len(item_ids) == 1:
            self.on_item_selected(item_ids[0])
        else:
            if getattr(self.canvas, "editing_node_item_id", None):
                self.canvas.end_node_editing()
            if getattr(self.canvas, "editing_label_item_id", None):
                self.canvas.end_label_editing()
            if hasattr(self.prop_panel, "set_multi_selection"):
                self.prop_panel.set_multi_selection(item_ids)
            if hasattr(self.navigator, "set_selected_objects"):
                self.navigator.set_selected_objects(item_ids)

    def on_property_changed(self, item_id: str, attrs: dict):
        ann = self._find_annotation(item_id)
        if not ann or not attrs:
            return

        old_attrs: Dict[str, Any] = {}
        new_attrs: Dict[str, Any] = {}

        for key, val in attrs.items():
            if key == "leader_end_point":
                continue
            if hasattr(ann, key):
                old_attrs[key] = _clone_value(getattr(ann, key))
            new_attrs[key] = _clone_value(val)

        if "has_leader" in attrs:
            old_attrs["points"] = _clone_points(ann.points)
            pts = _clone_points(ann.points)
            if attrs["has_leader"] and not getattr(ann, "has_leader", False):
                if len(pts) == 0:
                    pts = [QPointF(0, 0), QPointF(50, 50)]
                elif len(pts) == 1:
                    pts.append(pts[0] + QPointF(50, 50))
            elif not attrs["has_leader"] and getattr(ann, "has_leader", False):
                if len(pts) >= 1:
                    pts = [pts[0]]
            new_attrs["points"] = pts

        if old_attrs == new_attrs:
            return

        self.undo_stack.push(
            PropertyChangeCommand(self, item_id, old_attrs, new_attrs, allow_merge=True)
        )

    def _apply_property_dict(
        self,
        item_id: str,
        attrs: Dict[str, Any],
        sync_page_and_panel: bool = False,
    ):
        """属性辞書を注釈モデルとキャンバスへ反映する内部ヘルパー"""
        ann = self._find_annotation(item_id)
        if not ann:
            return

        if sync_page_and_panel:
            self._ensure_page(ann.page_num)

        canvas_attrs = dict(attrs)

        if "points" in canvas_attrs:
            ann.points = _clone_points(canvas_attrs.pop("points"))

        if "text" in canvas_attrs:
            ann.text = canvas_attrs["text"]
        if "real_value" in canvas_attrs:
            ann.real_value = canvas_attrs["real_value"]
        if "is_calculated" in canvas_attrs:
            ann.is_calculated = canvas_attrs["is_calculated"]
        if "color" in canvas_attrs:
            ann.color = canvas_attrs["color"]
            if ann.type == "marker":
                self.tool_controller.current_marker_color = canvas_attrs["color"]
            elif ann.type == "cloud":
                self.tool_controller.current_cloud_color = canvas_attrs["color"]
            else:
                self.tool_controller.current_shape_color = canvas_attrs["color"]
        if "fill_color" in canvas_attrs:
            ann.fill_color = canvas_attrs["fill_color"]
        if "font_family" in canvas_attrs:
            ann.font_family = canvas_attrs["font_family"]
        if "font_size" in canvas_attrs:
            ann.font_size = canvas_attrs["font_size"]
        if "line_width" in canvas_attrs:
            ann.line_width = canvas_attrs["line_width"]
        if "stroke_opacity" in canvas_attrs:
            ann.stroke_opacity = canvas_attrs["stroke_opacity"]
        if "fill_opacity" in canvas_attrs:
            ann.fill_opacity = canvas_attrs["fill_opacity"]
        if "center_marker" in canvas_attrs:
            ann.center_marker = canvas_attrs["center_marker"]
        if "start_marker" in canvas_attrs:
            ann.start_marker = canvas_attrs["start_marker"]
        if "end_marker" in canvas_attrs:
            ann.end_marker = canvas_attrs["end_marker"]
        if "marker_style" in canvas_attrs:
            ann.marker_style = canvas_attrs["marker_style"]
        if "drag_angle" in canvas_attrs:
            ann.drag_angle = canvas_attrs["drag_angle"]
        if "arc_span" in canvas_attrs:
            ann.arc_span = canvas_attrs["arc_span"]
        if "show_radial_line" in canvas_attrs:
            ann.show_radial_line = canvas_attrs["show_radial_line"]
        if "has_border" in canvas_attrs:
            ann.has_border = canvas_attrs["has_border"]
        if "border_color" in canvas_attrs:
            ann.border_color = canvas_attrs["border_color"]
        if "border_width" in canvas_attrs:
            ann.border_width = canvas_attrs["border_width"]

        if "has_leader" in canvas_attrs:
            ann.has_leader = canvas_attrs["has_leader"]
            if ann.has_leader and len(ann.points) >= 2:
                canvas_attrs["leader_end_point"] = ann.points[1]
            elif not ann.has_leader and getattr(self.canvas, "editing_node_item_id", None) == item_id:
                if hasattr(self.canvas, "end_node_editing"):
                    self.canvas.end_node_editing()

        if any(k in canvas_attrs for k in ("start_marker", "end_marker", "center_marker")):
            canvas_attrs["start_marker"] = ann.start_marker
            canvas_attrs["end_marker"] = ann.end_marker
            canvas_attrs["center_marker"] = ann.center_marker
        if "color" in canvas_attrs:
            canvas_attrs["fill_color"] = ann.fill_color
        if "text" in canvas_attrs:
            canvas_attrs["label_offset"] = getattr(ann, "label_offset", [0.0, 0.0])

        needs_list_update = any(k in canvas_attrs for k in ("text", "color", "marker_style"))
        needs_summary_update = any(k in canvas_attrs for k in ("color", "marker_style"))

        if self.current_page == ann.page_num:
            if "points" in attrs and hasattr(self.canvas, "sync_annotation_geometry"):
                self.canvas.sync_annotation_geometry(ann)
            self.canvas.update_item_properties(item_id, canvas_attrs)

        if sync_page_and_panel:
            self._refresh_prop_panel_if_selected(ann)

        if needs_list_update:
            self.update_object_panel()
        if needs_summary_update:
            self.update_marker_summary()
        self.document_manager.set_dirty(True)

    def on_item_moved(self, item_id: str, delta: QPointF):
        if delta.isNull():
            return
        ann = self._find_annotation(item_id)
        if not ann:
            return

        old_points = _clone_points(ann.points)
        if ann.type == "text":
            new_points = _clone_points(ann.points)
            if len(new_points) >= 1:
                new_points[0] = new_points[0] + delta
        else:
            new_points = [p + delta for p in ann.points]

        self.undo_stack.push(
            MoveCommand(
                self,
                item_id,
                old_points=old_points,
                new_points=new_points,
                description="注釈の移動",
            )
        )

    def on_items_moved(self, item_ids: list, delta: QPointF):
        if delta.isNull() or not item_ids:
            return
        if len(item_ids) == 1:
            self.on_item_moved(item_ids[0], delta)
            return

        moves = []
        for iid in item_ids:
            ann = self._find_annotation(iid)
            if not ann:
                continue
            old_points = _clone_points(ann.points)
            if ann.type == "text":
                new_points = _clone_points(ann.points)
                if len(new_points) >= 1:
                    new_points[0] = new_points[0] + delta
            else:
                new_points = [p + delta for p in ann.points]
            moves.append(
                {
                    "item_id": iid,
                    "old_points": old_points,
                    "new_points": new_points,
                }
            )

        if moves:
            self.undo_stack.push(
                BatchMoveCommand(self, moves, description="複数注釈の移動")
            )

    def on_label_moved(self, item_id: str, delta: QPointF):
        if delta.isNull():
            return
        ann = self._find_annotation(item_id)
        if not ann:
            return

        old_offset = list(getattr(ann, "label_offset", None) or [0.0, 0.0])
        new_offset = [old_offset[0] + delta.x(), old_offset[1] + delta.y()]
        self.undo_stack.push(
            MoveCommand(
                self,
                item_id,
                old_label_offset=old_offset,
                new_label_offset=new_offset,
                description="ラベル位置の移動",
            )
        )

    def on_node_edit_toggled(self, item_id: str, active: bool):
        if active:
            self.canvas.start_node_editing(item_id)
        else:
            self.canvas.end_node_editing()

    def on_canvas_node_edit_ended(self, item_id: str):
        self.prop_panel.set_node_edit_active(False)

    def on_canvas_item_points_updated(self, item_id: str, points):
        ann = self._find_annotation(item_id)
        if not ann:
            return

        old_points = _clone_points(ann.points)
        new_points = _clone_points(points)
        if old_points == new_points:
            return

        old_real_value = None
        new_real_value = None
        old_text = None
        new_text = None

        if self.is_current_page_calibrated_fn() and ann.is_calculated:
            sf = self.get_current_scale_factor_fn()
            if sf > 0:
                old_real_value = ann.real_value
                old_text = ann.text
                ann.points = _clone_points(new_points)
                self.measurement_service.calculate_annotation_values(ann, sf, self.model)
                new_real_value = ann.real_value
                new_text = ann.text
                ann.points = old_points
                ann.real_value = old_real_value
                ann.text = old_text

        self.undo_stack.push(
            MoveCommand(
                self,
                item_id,
                old_points=old_points,
                new_points=new_points,
                old_real_value=old_real_value,
                new_real_value=new_real_value,
                old_text=old_text,
                new_text=new_text,
                description="頂点の編集",
            )
        )

    def _remove_annotation_internal(self, item_id: str):
        """モデルおよびキャンバスから指定IDの注釈を削除し、関連UIを更新する"""
        if (
            hasattr(self.canvas, "active_edit_mode")
            and self.canvas.active_edit_mode
            and self.canvas.editing_item_id == item_id
        ):
            self.on_object_edit_toggled_from_panel(item_id, False)

        is_selected = (
            hasattr(self.prop_panel, "current_item_id")
            and self.prop_panel.current_item_id == item_id
        )

        self.model.annotations = [a for a in self.model.annotations if a.id != item_id]
        self.canvas.remove_annotation(item_id)

        if is_selected:
            self.on_selection_cleared()

        self.update_object_panel()
        self.update_marker_summary()
        self.document_manager.set_dirty(True)

    def on_delete_item(self, item_id: str):
        for idx, ann in enumerate(self.model.annotations):
            if ann.id == item_id:
                self.undo_stack.push(RemoveCommand(self, ann, index=idx))
                break

    def on_delete_multiple_items(self, item_ids: list):
        if not item_ids:
            return
        if len(item_ids) == 1:
            self.on_delete_item(item_ids[0])
            return

        target_set = set(item_ids)
        entries = [
            (idx, ann)
            for idx, ann in enumerate(self.model.annotations)
            if ann.id in target_set
        ]
        if entries:
            self.undo_stack.push(
                BatchRemoveCommand(self, entries, description="複数注釈の削除")
            )
            self.on_selection_cleared()

    def on_calculate_requested(self, item_id: str):
        if not self.is_current_page_calibrated_fn():
            if self.parent_widget:
                QMessageBox.warning(
                    self.parent_widget,
                    "警告",
                    "キャリブレーションが完了していません。先にキャリブレーションを行ってください。",
                )
            return
        sf = self.get_current_scale_factor_fn()
        if sf <= 0:
            return
        ann = self._find_annotation(item_id)
        if not ann:
            return

        old_attrs = {
            "is_calculated": ann.is_calculated,
            "real_value": ann.real_value,
            "text": ann.text,
        }
        ann.is_calculated = True
        self.measurement_service.calculate_annotation_values(ann, sf, self.model)
        new_attrs = {
            "is_calculated": True,
            "real_value": ann.real_value,
            "text": ann.text,
        }
        # 一旦元の値に戻してからコマンド経由で適用する
        ann.is_calculated = old_attrs["is_calculated"]
        ann.real_value = old_attrs["real_value"]
        ann.text = old_attrs["text"]

        self.undo_stack.push(
            PropertyChangeCommand(
                self,
                item_id,
                old_attrs,
                new_attrs,
                allow_merge=False,
                description="計測値の計算",
            )
        )
        self._refresh_prop_panel_if_selected(ann)

    def on_object_selected_from_panel(self, item_id: str):
        if hasattr(self.canvas, "scene") and self.canvas.scene:
            self.canvas.scene.clearSelection()

        target_item = None
        if hasattr(self.canvas, "annotation_items") and isinstance(self.canvas.annotation_items, dict):
            target_item = self.canvas.annotation_items.get(item_id)

        if not target_item and hasattr(self.canvas, "scene") and self.canvas.scene:
            for item in self.canvas.scene.items():
                if item.data(0) == item_id:
                    target_item = item
                    break

        if target_item:
            target_item.setSelected(True)
            if hasattr(self.canvas, "centerOn"):
                self.canvas.centerOn(target_item)
            self.on_item_selected(item_id)

    def on_object_edit_toggled_from_panel(self, item_id: str, active: bool):
        self.canvas.set_active_edit_item(item_id, active)
        self.navigator.set_editing_object(item_id, active)

        if active:
            self.set_tool_fn(ToolMode.SELECT)

        if hasattr(self.tool_controller, 'toolbar') and self.tool_controller.toolbar:
            for btn in getattr(self.tool_controller.toolbar, 'tool_btns', []):
                mode = btn.property("tool_mode")
                if mode != ToolMode.SELECT:
                    btn.setEnabled(not active)

        if hasattr(self.prop_panel, 'node_edit_btn'):
            self.prop_panel.node_edit_btn.setEnabled(not active)

    def render_single_annotation(
        self, ann: BaseAnnotation, current_scale_factor: Optional[float] = None
    ):
        """単一の注釈オブジェクトをキャンバスに描画する"""
        if current_scale_factor is None:
            current_scale_factor = self.get_current_scale_factor_fn()

        if ann.type == "line":
            self.canvas.add_line_annotation(
                ann.points[0], ann.points[1], text=ann.text, color=ann.color, item_id=ann.id,
                font_family=ann.font_family, font_size=ann.font_size, line_width=ann.line_width,
                stroke_opacity=ann.stroke_opacity, label_offset=getattr(ann, "label_offset", [0.0, 0.0]),
            )
        elif ann.type == "polyline":
            self.canvas.add_polyline_annotation(
                ann.points, text=ann.text, color=ann.color, item_id=ann.id,
                font_family=ann.font_family, font_size=ann.font_size,
                line_width=ann.line_width, stroke_opacity=ann.stroke_opacity,
                start_marker=ann.start_marker, end_marker=ann.end_marker,
                label_offset=getattr(ann, "label_offset", [0.0, 0.0]),
            )
        elif ann.type == "polygon":
            self.canvas.add_polygon_annotation(
                ann.points, text=ann.text, color=ann.color, item_id=ann.id,
                font_family=ann.font_family, font_size=ann.font_size,
                line_width=ann.line_width, stroke_opacity=ann.stroke_opacity,
                fill_opacity=ann.fill_opacity, fill_color=ann.fill_color,
                label_offset=getattr(ann, "label_offset", [0.0, 0.0]),
            )
        elif ann.type == "cloud":
            self.canvas.add_cloud_annotation(
                ann.points, color=ann.color, item_id=ann.id,
                line_width=ann.line_width, stroke_opacity=ann.stroke_opacity,
                fill_opacity=ann.fill_opacity, fill_color=ann.fill_color,
            )
        elif ann.type == "circle":
            radius_px = ann.radius_px
            if radius_px <= 0 and ann.real_value > 0 and current_scale_factor > 0:
                radius_px = ann.real_value / current_scale_factor
            self.canvas.add_circle_annotation(
                ann.points[0], radius_px, text=ann.text, color=ann.color, item_id=ann.id,
                font_family=ann.font_family, font_size=ann.font_size,
                line_width=ann.line_width, stroke_opacity=ann.stroke_opacity,
                fill_opacity=ann.fill_opacity, fill_color=ann.fill_color,
                center_marker=ann.center_marker,
                label_offset=getattr(ann, "label_offset", [0.0, 0.0]),
            )
        elif ann.type == "arc":
            radius_px = getattr(ann, "radius_px", 0.0)
            if radius_px <= 0 and ann.real_value > 0 and current_scale_factor > 0:
                radius_px = ann.real_value / current_scale_factor
            self.canvas.add_arc_annotation(
                ann.points[0], radius_px, getattr(ann, "drag_angle", 0.0),
                getattr(ann, "arc_span", 30.0), text=ann.text, color=ann.color,
                item_id=ann.id, font_family=ann.font_family, font_size=ann.font_size,
                line_width=ann.line_width, stroke_opacity=ann.stroke_opacity,
                center_marker=ann.center_marker,
                show_radial_line=getattr(ann, "show_radial_line", False),
                label_offset=getattr(ann, "label_offset", [0.0, 0.0]),
            )
        elif ann.type == "text":
            leader_end = ann.points[1] if len(ann.points) >= 2 else None
            self.canvas.add_text_annotation(
                ann.points[0], ann.text, color=ann.color, item_id=ann.id,
                font_family=ann.font_family, font_size=ann.font_size,
                stroke_opacity=ann.stroke_opacity,
                has_border=getattr(ann, "has_border", False),
                border_color=getattr(ann, "border_color", "#ff0000"),
                border_width=getattr(ann, "border_width", 2),
                has_leader=getattr(ann, "has_leader", False),
                leader_end_point=leader_end,
            )
        elif ann.type == "marker":
            self.canvas.add_marker_annotation(
                ann.points[0], marker_style=getattr(ann, "marker_style", "square"),
                color=ann.color, stroke_opacity=ann.stroke_opacity, item_id=ann.id,
            )
        elif ann.type == "legend":
            self.canvas.add_legend_annotation(
                ann.points[0], item_id=ann.id,
                font_family=getattr(ann, "font_family", "Arial"),
                font_size=getattr(ann, "font_size", 12),
                color=getattr(ann, "color", "#7c4dff"),
            )
            self.update_marker_summary()

    def render_page_annotations(self, page_num: int, current_scale_factor: float):
        """現在のページの注釈一覧を走査し、キャンバスにQGraphicsItemを生成・描画する"""
        for ann in self.model.annotations:
            if ann.page_num == page_num:
                self.render_single_annotation(ann, current_scale_factor)

    def update_marker_summary(self):
        """左側ナビゲーターパネルのマーカー集計リストを更新する"""
        if not hasattr(self, 'navigator') or not self.navigator or not self.model:
            return

        marker_counts = {}
        total_markers = 0
        for ann in self.model.annotations:
            if ann.page_num == self.current_page and ann.type == 'marker':
                style = getattr(ann, 'marker_style', 'square')
                color_hex = (ann.color or "#7c4dff").lower()
                key = (style, color_hex)
                marker_counts[key] = marker_counts.get(key, 0) + 1
                total_markers += 1

        page_names = self.model.page_color_names.get(self.current_page, {}) if hasattr(self.model, 'page_color_names') else {}
        self.navigator.update_marker_summary(self.model.annotations, self.current_page, page_names)

        if self.canvas:
            self.canvas.update_legends(marker_counts, page_names)

        # 凡例ツールの有効/無効制御
        if hasattr(self.tool_controller, 'toolbar') and self.tool_controller.toolbar:
            has_markers = (total_markers > 0)
            self.tool_controller.toolbar.set_tool_enabled(ToolMode.DRAW_LEGEND, has_markers)
            if not has_markers and self.canvas and self.canvas.tool_mode == ToolMode.DRAW_LEGEND:
                self.set_tool_fn(ToolMode.SELECT)

    def update_object_panel(self):
        """左側ナビゲーターパネルのオブジェクト一覧を更新する"""
        if not hasattr(self, 'navigator') or not self.navigator or not self.model:
            return
        page_anns = [ann for ann in self.model.annotations if ann.page_num == self.current_page]
        page_names = self.model.page_color_names.get(self.current_page, {}) if hasattr(self.model, 'page_color_names') else {}
        self.navigator.update_objects(page_anns, page_names)
