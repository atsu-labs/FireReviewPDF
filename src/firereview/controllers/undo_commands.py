"""アノテーション操作のUndo/Redo用コマンドクラス群 (Command Pattern)"""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import QPointF
from PySide6.QtGui import QUndoCommand

from firereview.models import BaseAnnotation


def _clone_points(points: List[QPointF]) -> List[QPointF]:
    """QPointFリストのディープコピーを生成する"""
    result = []
    for p in points:
        if isinstance(p, QPointF):
            result.append(QPointF(p.x(), p.y()))
        else:
            result.append(QPointF(float(p[0]), float(p[1])))
    return result


def _clone_value(val: Any) -> Any:
    """属性値の安全なコピーを生成する"""
    if isinstance(val, QPointF):
        return QPointF(val.x(), val.y())
    if isinstance(val, list):
        return [_clone_value(v) for v in val]
    if isinstance(val, dict):
        return {k: _clone_value(v) for k, v in val.items()}
    return val


class AddCommand(QUndoCommand):
    """注釈追加の履歴コマンド"""

    def __init__(
        self,
        controller,
        annotation: BaseAnnotation,
        render_on_first_redo: bool = True,
        description: str = "注釈の追加",
    ):
        super().__init__(description)
        self.controller = controller
        self.annotation = annotation
        self.render_on_first_redo = render_on_first_redo
        self._first_redo = True

    def redo(self):
        first = self._first_redo
        self._first_redo = False

        if not first:
            self.controller._ensure_page(self.annotation.page_num)

        if self.annotation not in self.controller.model.annotations:
            self.controller.model.annotations.append(self.annotation)

        should_render = self.render_on_first_redo or not first
        if should_render and self.controller.current_page == self.annotation.page_num:
            ann_items = getattr(self.controller.canvas, "annotation_items", None)
            if not isinstance(ann_items, dict) or self.annotation.id not in ann_items:
                self.controller.render_single_annotation(self.annotation)

        if self.annotation.type in ("marker", "legend"):
            self.controller.update_marker_summary()
        self.controller.update_object_panel()
        self.controller.document_manager.set_dirty(True)

    def undo(self):
        self.controller._ensure_page(self.annotation.page_num)
        self.controller._remove_annotation_internal(self.annotation.id)


class RemoveCommand(QUndoCommand):
    """注釈削除の履歴コマンド"""

    def __init__(
        self,
        controller,
        annotation: BaseAnnotation,
        index: Optional[int] = None,
        description: str = "注釈の削除",
    ):
        super().__init__(description)
        self.controller = controller
        self.annotation = annotation
        self.index = index
        self._first_redo = True

    def redo(self):
        first = self._first_redo
        self._first_redo = False

        if not first:
            self.controller._ensure_page(self.annotation.page_num)

        self.controller._remove_annotation_internal(self.annotation.id)

    def undo(self):
        self.controller._ensure_page(self.annotation.page_num)

        if self.annotation not in self.controller.model.annotations:
            if self.index is not None and 0 <= self.index <= len(self.controller.model.annotations):
                self.controller.model.annotations.insert(self.index, self.annotation)
            else:
                self.controller.model.annotations.append(self.annotation)

        if self.controller.current_page == self.annotation.page_num:
            ann_items = getattr(self.controller.canvas, "annotation_items", None)
            if not isinstance(ann_items, dict) or self.annotation.id not in ann_items:
                self.controller.render_single_annotation(self.annotation)

        if self.annotation.type in ("marker", "legend"):
            self.controller.update_marker_summary()
        self.controller.update_object_panel()
        self.controller.document_manager.set_dirty(True)


class MoveCommand(QUndoCommand):
    """注釈の移動・頂点編集・ラベル位置変更の履歴コマンド"""

    def __init__(
        self,
        controller,
        item_id: str,
        old_points: Optional[List[QPointF]] = None,
        new_points: Optional[List[QPointF]] = None,
        old_label_offset: Optional[List[float]] = None,
        new_label_offset: Optional[List[float]] = None,
        old_real_value: Optional[float] = None,
        new_real_value: Optional[float] = None,
        old_text: Optional[str] = None,
        new_text: Optional[str] = None,
        description: str = "注釈の移動・変形",
    ):
        super().__init__(description)
        self.controller = controller
        self.item_id = item_id
        self.old_points = _clone_points(old_points) if old_points is not None else None
        self.new_points = _clone_points(new_points) if new_points is not None else None
        self.old_label_offset = list(old_label_offset) if old_label_offset is not None else None
        self.new_label_offset = list(new_label_offset) if new_label_offset is not None else None
        self.old_real_value = old_real_value
        self.new_real_value = new_real_value
        self.old_text = old_text
        self.new_text = new_text
        self._first_redo = True

    def _apply_state(
        self,
        points: Optional[List[QPointF]],
        label_offset: Optional[List[float]],
        real_value: Optional[float],
        text: Optional[str],
        sync_canvas: bool,
    ):
        ann = self.controller._find_annotation(self.item_id)
        if not ann:
            return

        if not sync_canvas:
            # 初回push時: キャンバス上は既にマウス操作で移動済み
            if points is not None:
                ann.points = _clone_points(points)
            if label_offset is not None:
                ann.label_offset = list(label_offset)
            if real_value is not None:
                ann.real_value = real_value
            if text is not None:
                ann.text = text

            if self.controller.current_page == ann.page_num:
                attrs = {}
                if getattr(ann, "start_marker", None):
                    attrs["start_marker"] = ann.start_marker
                if getattr(ann, "end_marker", None):
                    attrs["end_marker"] = ann.end_marker
                if getattr(ann, "center_marker", None):
                    attrs["center_marker"] = ann.center_marker
                if text is not None:
                    attrs["text"] = ann.text
                if attrs:
                    self.controller.canvas.update_item_properties(self.item_id, attrs)

            if text is not None:
                self.controller._refresh_prop_panel_if_selected(ann)
                self.controller.update_object_panel()
            elif points is not None and self.old_points is not None and len(points) != len(self.old_points):
                self.controller.update_object_panel()

            self.controller.document_manager.set_dirty(True)
            return

        # Undo / 2回目以降のRedo時: ページ遷移とキャンバス座標同期を行う
        self.controller._ensure_page(ann.page_num)

        if points is not None:
            ann.points = _clone_points(points)
        if label_offset is not None:
            ann.label_offset = list(label_offset)
        if real_value is not None:
            ann.real_value = real_value
        if text is not None:
            ann.text = text

        if self.controller.current_page == ann.page_num:
            if hasattr(self.controller.canvas, "sync_annotation_geometry"):
                self.controller.canvas.sync_annotation_geometry(ann)
            attrs = {}
            if getattr(ann, "start_marker", None):
                attrs["start_marker"] = ann.start_marker
            if getattr(ann, "end_marker", None):
                attrs["end_marker"] = ann.end_marker
            if getattr(ann, "center_marker", None):
                attrs["center_marker"] = ann.center_marker
            if text is not None:
                attrs["text"] = ann.text
                attrs["label_offset"] = getattr(ann, "label_offset", [0.0, 0.0])
            if attrs:
                self.controller.canvas.update_item_properties(self.item_id, attrs)

        if text is not None:
            self.controller._refresh_prop_panel_if_selected(ann)
        self.controller.update_object_panel()
        self.controller.document_manager.set_dirty(True)

    def redo(self):
        first = self._first_redo
        self._first_redo = False
        self._apply_state(
            self.new_points,
            self.new_label_offset,
            self.new_real_value,
            self.new_text,
            sync_canvas=not first,
        )

    def undo(self):
        self._apply_state(
            self.old_points,
            self.old_label_offset,
            self.old_real_value,
            self.old_text,
            sync_canvas=True,
        )


class PropertyChangeCommand(QUndoCommand):
    """属性変更・テキスト編集・計測計算の履歴コマンド（連続変更のマージ対応）"""

    MERGE_COMMAND_ID = 1001

    def __init__(
        self,
        controller,
        item_id: str,
        old_attrs: Dict[str, Any],
        new_attrs: Dict[str, Any],
        allow_merge: bool = True,
        description: str = "プロパティの変更",
    ):
        super().__init__(description)
        self.controller = controller
        self.item_id = item_id
        self.old_attrs = _clone_value(old_attrs)
        self.new_attrs = _clone_value(new_attrs)
        self.allow_merge = allow_merge
        self._first_redo = True

    def id(self) -> int:
        return self.MERGE_COMMAND_ID if self.allow_merge else -1

    def mergeWith(self, other: QUndoCommand) -> bool:
        if not isinstance(other, PropertyChangeCommand):
            return False
        if not self.allow_merge or not other.allow_merge:
            return False
        if self.item_id != other.item_id:
            return False
        if set(self.new_attrs.keys()) != set(other.new_attrs.keys()):
            return False
        self.new_attrs = _clone_value(other.new_attrs)
        return True

    def redo(self):
        first = self._first_redo
        self._first_redo = False
        self.controller._apply_property_dict(
            self.item_id,
            self.new_attrs,
            sync_page_and_panel=not first,
        )

    def undo(self):
        self.controller._apply_property_dict(
            self.item_id,
            self.old_attrs,
            sync_page_and_panel=True,
        )


class BatchMoveCommand(QUndoCommand):
    """複数注釈の一括移動の履歴コマンド"""

    def __init__(
        self,
        controller,
        moves: List[Dict[str, Any]],
        description: str = "複数注釈の移動",
    ):
        super().__init__(description)
        self.controller = controller
        self.commands = [
            MoveCommand(
                controller,
                m["item_id"],
                old_points=m.get("old_points"),
                new_points=m.get("new_points"),
                old_label_offset=m.get("old_label_offset"),
                new_label_offset=m.get("new_label_offset"),
                old_real_value=m.get("old_real_value"),
                new_real_value=m.get("new_real_value"),
                old_text=m.get("old_text"),
                new_text=m.get("new_text"),
            )
            for m in moves
        ]

    def redo(self):
        for cmd in self.commands:
            cmd.redo()

    def undo(self):
        for cmd in reversed(self.commands):
            cmd.undo()


class BatchRemoveCommand(QUndoCommand):
    """複数注釈の一括削除の履歴コマンド"""

    def __init__(
        self,
        controller,
        entries: List[tuple],
        description: str = "複数注釈の削除",
    ):
        super().__init__(description)
        self.controller = controller
        # entries: List[(index, BaseAnnotation)]
        self.entries = sorted(list(entries), key=lambda x: x[0])
        self._first_redo = True

    def redo(self):
        first = self._first_redo
        self._first_redo = False

        if not first and self.entries:
            self.controller._ensure_page(self.entries[0][1].page_num)

        for _idx, ann in self.entries:
            self.controller._remove_annotation_internal(ann.id)

    def undo(self):
        if not self.entries:
            return
        self.controller._ensure_page(self.entries[0][1].page_num)

        has_marker_or_legend = False
        for idx, ann in self.entries:
            if ann not in self.controller.model.annotations:
                if idx is not None and 0 <= idx <= len(self.controller.model.annotations):
                    self.controller.model.annotations.insert(idx, ann)
                else:
                    self.controller.model.annotations.append(ann)

            if self.controller.current_page == ann.page_num:
                ann_items = getattr(self.controller.canvas, "annotation_items", None)
                if not isinstance(ann_items, dict) or ann.id not in ann_items:
                    self.controller.render_single_annotation(ann)

            if ann.type in ("marker", "legend"):
                has_marker_or_legend = True

        if has_marker_or_legend:
            self.controller.update_marker_summary()
        self.controller.update_object_panel()
        self.controller.document_manager.set_dirty(True)
