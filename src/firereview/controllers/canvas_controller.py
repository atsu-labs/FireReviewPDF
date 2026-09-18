import math
from typing import Callable, Optional
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QMessageBox

from firereview.models import Annotation
from firereview.services.document_manager import DocumentManager
from firereview.services.measurement_service import MeasurementService
from firereview.controllers.tool_controller import ToolController
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
        self.parent_widget = parent_widget

    @property
    def model(self):
        return self.document_manager.model

    @property
    def current_page(self) -> int:
        return self.get_current_page_fn()

    def add_to_model(self, type_name: str, points, real_value: float = 0.0, text: str = "") -> Annotation:
        """モデルにアノテーションを追加し、ダーティフラグを立てる"""
        ann = Annotation(type_name)
        ann.points = points
        ann.real_value = real_value
        ann.text = text
        ann.page_num = self.current_page
        self.model.annotations.append(ann)
        self.document_manager.set_dirty(True)
        return ann

    # --- 描画完了イベントハンドラ群 ---
    def on_polygon_complete(self, points):
        ann = self.add_to_model("polygon", points, real_value=0.0, text="")
        ann.color = self.tool_controller.current_shape_color
        ann.line_width = self.tool_controller.current_line_width
        ann.fill_color = self.tool_controller.current_fill_color
        ann.fill_opacity = self.tool_controller.current_fill_opacity
        self.canvas.add_polygon_annotation(
            points, text="", color=ann.color, item_id=ann.id,
            font_family=ann.font_family, font_size=ann.font_size,
            line_width=ann.line_width, stroke_opacity=ann.stroke_opacity,
            fill_opacity=ann.fill_opacity, fill_color=ann.fill_color,
        )
        self.update_object_panel()

    def on_polyline_complete(self, points):
        ann = self.add_to_model("polyline", points, real_value=0.0, text="")
        ann.color = self.tool_controller.current_shape_color
        ann.line_width = self.tool_controller.current_line_width
        ann.start_marker = self.tool_controller.current_start_marker
        ann.end_marker = self.tool_controller.current_end_marker
        self.canvas.add_polyline_annotation(
            points, text="", color=ann.color, item_id=ann.id,
            font_family=ann.font_family, font_size=ann.font_size,
            line_width=ann.line_width,
            start_marker=ann.start_marker,
            end_marker=ann.end_marker,
        )
        self.update_object_panel()

    def on_circle_drag_complete(self, center, radius_px, spin_radius_val=None):
        current_scale_factor = self.get_current_scale_factor_fn()
        if radius_px < 3:
            if spin_radius_val is None and self.tool_controller and self.tool_controller.options_bar:
                spin_radius_val = self.tool_controller.options_bar.tool_radius_spin.value()
            if self.is_current_page_calibrated_fn() and current_scale_factor > 0 and spin_radius_val is not None:
                if self.model.unit == 'm':
                    radius_mm = spin_radius_val * 1000
                else:
                    radius_mm = spin_radius_val
                radius_px = radius_mm / current_scale_factor
            else:
                if self.parent_widget:
                    QMessageBox.warning(self.parent_widget, "警告", "半径を指定して円を描画するには、先にキャリブレーションを行ってください。")
                return

        ann = self.add_to_model("circle", [center], real_value=0.0, text="")
        ann.color = self.tool_controller.current_shape_color
        ann.line_width = self.tool_controller.current_line_width
        ann.fill_color = self.tool_controller.current_fill_color
        ann.fill_opacity = self.tool_controller.current_fill_opacity
        ann.radius_px = radius_px
        ann.center_marker = self.tool_controller.current_center_marker
        self.canvas.add_circle_annotation(
            center, radius_px, text="", color=ann.color, item_id=ann.id,
            font_family=ann.font_family, font_size=ann.font_size,
            line_width=ann.line_width, stroke_opacity=ann.stroke_opacity,
            fill_opacity=ann.fill_opacity, fill_color=ann.fill_color,
            center_marker=ann.center_marker,
        )
        self.update_object_panel()

    def on_arc_drag_complete(self, center, radius_px, drag_angle):
        ann = self.add_to_model("arc", [center], real_value=0.0, text="")
        ann.color = self.tool_controller.current_shape_color
        ann.line_width = self.tool_controller.current_line_width
        ann.radius_px = radius_px
        ann.center_marker = self.tool_controller.current_center_marker
        ann.drag_angle = drag_angle
        ann.arc_span = self.tool_controller.current_arc_span
        ann.show_radial_line = self.tool_controller.current_arc_show_radial_line

        self.canvas.add_arc_annotation(
            center, radius_px, drag_angle, ann.arc_span,
            text="", color=ann.color, item_id=ann.id,
            font_family=ann.font_family, font_size=ann.font_size,
            line_width=ann.line_width, stroke_opacity=ann.stroke_opacity,
            center_marker=ann.center_marker,
            show_radial_line=ann.show_radial_line,
        )
        self.update_object_panel()

    def on_marker_complete(self, pos, continuous: Optional[bool] = None):
        ann = self.add_to_model("marker", [pos])
        ann.color = self.tool_controller.current_marker_color
        ann.marker_style = self.tool_controller.current_marker_style
        ann.stroke_opacity = self.tool_controller.current_marker_opacity

        self.canvas.add_marker_annotation(
            pos, marker_style=ann.marker_style, color=ann.color,
            stroke_opacity=ann.stroke_opacity, item_id=ann.id,
        )

        if continuous is None:
            if self.tool_controller and self.tool_controller.options_bar:
                continuous = self.tool_controller.options_bar.tool_marker_continuous_check.isChecked()
            else:
                continuous = False

        if not continuous:
            self.set_tool_fn(ToolMode.SELECT)

        self.update_marker_summary()
        self.update_object_panel()

    def on_legend_complete(self, pos):
        ann = self.add_to_model("legend", [pos])
        ann.font_family = self.tool_controller.current_text_font
        ann.font_size = self.tool_controller.current_text_size
        ann.color = self.tool_controller.current_text_color

        self.canvas.add_legend_annotation(
            pos, item_id=ann.id,
            font_family=ann.font_family,
            font_size=ann.font_size,
            color=ann.color,
        )
        self.set_tool_fn(ToolMode.SELECT)
        self.update_marker_summary()
        self.update_object_panel()

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
            ann = self.add_to_model("text", [pos], text=text)
            ann.font_family = font_family
            ann.font_size = font_size
            ann.color = color
            self.canvas.add_text_annotation(
                pos, text, color=color, item_id=ann.id,
                font_family=font_family, font_size=font_size,
            )
            self.update_object_panel()
        else:
            for ann in self.model.annotations:
                if ann.id == item_id:
                    ann.text = text
                    ann.points = [pos]
                    ann.font_family = font_family
                    ann.font_size = font_size
                    ann.color = color
                    break
            self.update_object_panel()
            self.document_manager.set_dirty(True)

    def on_existing_text_edited(self, item_id: str, new_text: str):
        for ann in self.model.annotations:
            if ann.id == item_id:
                ann.text = new_text
                break

        if hasattr(self.prop_panel, 'current_item_id') and self.prop_panel.current_item_id == item_id:
            self.prop_panel._block_signals = True
            if hasattr(self.prop_panel.text_edit, 'setPlainText'):
                self.prop_panel.text_edit.setPlainText(new_text)
            else:
                self.prop_panel.text_edit.setText(new_text)
            self.prop_panel._block_signals = False
        self.document_manager.set_dirty(True)

    def on_item_selected(self, item_id: str):
        for ann in self.model.annotations:
            if ann.id == item_id:
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
                break

    def on_selection_cleared(self):
        self.prop_panel.clear_panel()
        self.navigator.set_selected_object(None)

    def on_property_changed(self, item_id: str, attrs: dict):
        for ann in self.model.annotations:
            if ann.id == item_id:
                if "text" in attrs: ann.text = attrs["text"]
                if "color" in attrs:
                    ann.color = attrs["color"]
                    if ann.type == "marker":
                        self.tool_controller.current_marker_color = attrs["color"]
                    else:
                        self.tool_controller.current_shape_color = attrs["color"]
                if "fill_color" in attrs: ann.fill_color = attrs["fill_color"]
                if "font_family" in attrs: ann.font_family = attrs["font_family"]
                if "font_size" in attrs: ann.font_size = attrs["font_size"]
                if "line_width" in attrs: ann.line_width = attrs["line_width"]
                if "stroke_opacity" in attrs: ann.stroke_opacity = attrs["stroke_opacity"]
                if "fill_opacity" in attrs: ann.fill_opacity = attrs["fill_opacity"]
                if "center_marker" in attrs: ann.center_marker = attrs["center_marker"]
                if "start_marker" in attrs: ann.start_marker = attrs["start_marker"]
                if "end_marker" in attrs: ann.end_marker = attrs["end_marker"]
                if "marker_style" in attrs: ann.marker_style = attrs["marker_style"]
                if "drag_angle" in attrs: ann.drag_angle = attrs["drag_angle"]
                if "arc_span" in attrs: ann.arc_span = attrs["arc_span"]
                if "show_radial_line" in attrs: ann.show_radial_line = attrs["show_radial_line"]

                if "has_border" in attrs: ann.has_border = attrs["has_border"]
                if "border_color" in attrs: ann.border_color = attrs["border_color"]
                if "border_width" in attrs: ann.border_width = attrs["border_width"]

                if "has_leader" in attrs:
                    if attrs["has_leader"] and not getattr(ann, "has_leader", False):
                        if len(ann.points) == 0:
                            ann.points = [QPointF(0, 0), QPointF(50, 50)]
                        elif len(ann.points) == 1:
                            end_pt = ann.points[0] + QPointF(50, 50)
                            ann.points.append(end_pt)

                        if len(ann.points) >= 2:
                            attrs["leader_end_point"] = ann.points[1]
                    elif not attrs["has_leader"] and getattr(ann, "has_leader", False):
                        if len(ann.points) >= 1:
                            ann.points = [ann.points[0]]
                    ann.has_leader = attrs["has_leader"]

                if any(k in attrs for k in ("start_marker", "end_marker", "center_marker")):
                    attrs["start_marker"] = ann.start_marker
                    attrs["end_marker"] = ann.end_marker
                    attrs["center_marker"] = ann.center_marker
                if "color" in attrs:
                    attrs["fill_color"] = ann.fill_color

                needs_list_update = any(k in attrs for k in ("text", "color", "marker_style"))
                needs_summary_update = any(k in attrs for k in ("color", "marker_style"))

                self.canvas.update_item_properties(item_id, attrs)

                if needs_list_update:
                    self.update_object_panel()
                if needs_summary_update:
                    self.update_marker_summary()
                self.document_manager.set_dirty(True)
                break

    def on_item_moved(self, item_id: str, delta: QPointF):
        for ann in self.model.annotations:
            if ann.id == item_id:
                if ann.type == "text":
                    if len(ann.points) >= 1:
                        ann.points[0] = ann.points[0] + delta
                else:
                    ann.points = [p + delta for p in ann.points]

                attrs = {}
                if hasattr(ann, 'start_marker') and ann.start_marker is not None:
                    attrs['start_marker'] = ann.start_marker
                if hasattr(ann, 'end_marker') and ann.end_marker is not None:
                    attrs['end_marker'] = ann.end_marker
                if hasattr(ann, 'center_marker') and ann.center_marker is not None:
                    attrs['center_marker'] = ann.center_marker

                if attrs:
                    self.canvas.update_item_properties(item_id, attrs)
                self.document_manager.set_dirty(True)
                break

    def on_label_moved(self, item_id: str, delta: QPointF):
        for ann in self.model.annotations:
            if ann.id == item_id:
                offset = getattr(ann, "label_offset", None) or [0.0, 0.0]
                ann.label_offset = [offset[0] + delta.x(), offset[1] + delta.y()]
                self.document_manager.set_dirty(True)
                break

    def on_node_edit_toggled(self, item_id: str, active: bool):
        if active:
            self.canvas.start_node_editing(item_id)
        else:
            self.canvas.end_node_editing()

    def on_canvas_node_edit_ended(self, item_id: str):
        self.prop_panel.set_node_edit_active(False)

    def on_canvas_item_points_updated(self, item_id: str, points):
        for ann in self.model.annotations:
            if ann.id == item_id:
                ann.points = points
                if self.is_current_page_calibrated_fn() and ann.is_calculated:
                    self.on_calculate_requested(item_id)

                if ann.type == "polyline":
                    self.canvas.update_item_properties(
                        item_id, {"start_marker": ann.start_marker, "end_marker": ann.end_marker}
                    )
                self.update_object_panel()
                self.document_manager.set_dirty(True)
                break

    def on_delete_item(self, item_id: str):
        if hasattr(self.canvas, 'active_edit_mode') and self.canvas.active_edit_mode and self.canvas.editing_item_id == item_id:
            self.on_object_edit_toggled_from_panel(item_id, False)

        is_selected = False
        if hasattr(self.prop_panel, 'current_item_id') and self.prop_panel.current_item_id == item_id:
            is_selected = True

        self.model.annotations = [a for a in self.model.annotations if a.id != item_id]
        self.canvas.remove_annotation(item_id)

        if is_selected:
            self.on_selection_cleared()

        self.update_object_panel()
        self.update_marker_summary()
        self.document_manager.set_dirty(True)

    def on_calculate_requested(self, item_id: str):
        if not self.is_current_page_calibrated_fn():
            if self.parent_widget:
                QMessageBox.warning(self.parent_widget, "警告", "キャリブレーションが完了していません。先にキャリブレーションを行ってください。")
            return
        sf = self.get_current_scale_factor_fn()
        if sf <= 0:
            return
        for ann in self.model.annotations:
            if ann.id == item_id:
                ann.is_calculated = True
                self.measurement_service.calculate_annotation_values(ann, sf, self.model)
                self.canvas.update_item_properties(item_id, {"text": ann.text})
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
                if getattr(self.canvas, 'editing_node_item_id', None) == ann.id:
                    self.prop_panel.set_node_edit_active(True)
                self.update_object_panel()
                self.document_manager.set_dirty(True)
                break

    def on_object_selected_from_panel(self, item_id: str):
        self.canvas.scene.clearSelection()
        target_item = None
        for item in self.canvas.scene.items():
            if item.data(0) == item_id:
                target_item = item
                break
        if target_item:
            target_item.setSelected(True)
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

    def render_page_annotations(self, page_num: int, current_scale_factor: float):
        """現在のページの注釈一覧を走査し、キャンバスにQGraphicsItemを生成・描画する"""
        for ann in self.model.annotations:
            if ann.page_num == page_num:
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

