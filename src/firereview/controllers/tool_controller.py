from typing import Callable, Optional
from firereview.ui.canvas.enums import ToolMode


class ToolController:
    """描画ツールのデフォルト設定およびオプションバーとのインタラクションを管理するコントローラー"""

    def __init__(
        self,
        canvas=None,
        options_bar=None,
        toolbar=None,
        on_marker_updated_cb: Optional[Callable[[], None]] = None,
    ):
        self.canvas = canvas
        self.options_bar = options_bar
        self.toolbar = toolbar
        self.on_marker_updated_cb = on_marker_updated_cb

        # Text defaults
        self.current_text_font = "BIZ UDゴシック"
        self.current_text_size = 12
        self.current_text_color = "#ff0000"

        # Shape tool defaults
        self.current_shape_color = "#7c4dff"
        self.current_fill_color = "#7c4dff"
        self.current_fill_opacity = 30
        self.current_line_width = 2
        self.current_start_marker = ""
        self.current_end_marker = ""
        self.current_center_marker = ""
        self._start_marker_values = ["", "circle", "arrow"]
        self._end_marker_values = ["", "circle", "arrow"]
        self._center_marker_values = ["", "circle", "cross", "x"]
        self.current_arc_span = 30.0
        self.current_arc_show_radial_line = False

        # Marker defaults
        self.current_marker_style = "square"
        self.current_marker_color = "#ff1744"
        self.current_marker_opacity = 70

    def update_canvas_shape_defaults(self):
        """現在の図形描画設定をキャンバスに反映する"""
        if self.canvas:
            self.canvas.set_shape_defaults(
                self.current_shape_color, self.current_line_width, self.current_fill_color
            )

    def set_tool(self, mode, is_calibrated: bool = False):
        """アクティブな描画ツールを切り替え、オプションバーとキャンバスを更新する"""
        if self.toolbar:
            self.toolbar.set_tool_mode(mode)
        if self.canvas:
            self.canvas.set_tool_mode(mode)
        if self.options_bar:
            self.options_bar.update_options_visibility(mode, is_calibrated)

        is_shape_tool = mode in [
            ToolMode.DRAW_LINE,
            ToolMode.POLYGON_AREA,
            ToolMode.DRAW_CIRCLE_DRAG,
            ToolMode.DRAW_ARC,
        ]

        if not self.canvas or not self.options_bar:
            return

        if mode == ToolMode.TEXT:
            self.canvas.set_text_defaults(
                self.current_text_font,
                self.current_text_size,
                self.current_text_color,
                self.options_bar.tool_continuous_check.isChecked(),
            )
        elif mode == ToolMode.DRAW_MARKER:
            self.canvas.set_shape_defaults(self.current_marker_color, 2, "")
            self.canvas.set_shape_continuous(
                self.options_bar.tool_marker_continuous_check.isChecked()
            )
        elif is_shape_tool:
            self.update_canvas_shape_defaults()
            self.canvas.set_shape_continuous(
                self.options_bar.tool_shape_continuous_check.isChecked()
            )

    # --- オプションバーからの各種シグナルハンドラ ---
    def on_options_line_width_changed(self, width: int):
        self.current_line_width = width
        self.update_canvas_shape_defaults()

    def on_options_shape_color_changed(self, color: str):
        self.current_shape_color = color
        self.update_canvas_shape_defaults()
        if self.canvas and self.canvas.editing_item_id:
            self.canvas.update_item_properties(self.canvas.editing_item_id, {"color": color})

    def on_options_fill_color_changed(self, color: str):
        self.current_fill_color = color
        self.update_canvas_shape_defaults()

    def on_options_fill_opacity_changed(self, opacity: int):
        self.current_fill_opacity = opacity
        if self.canvas and self.canvas.editing_item_id:
            self.canvas.update_item_properties(self.canvas.editing_item_id, {"fill_opacity": opacity})

    def on_options_start_marker_changed(self, index: int):
        if 0 <= index < len(self._start_marker_values):
            self.current_start_marker = self._start_marker_values[index]
            if self.canvas and self.canvas.editing_item_id:
                self.canvas.update_item_properties(
                    self.canvas.editing_item_id, {"start_marker": self.current_start_marker}
                )

    def on_options_end_marker_changed(self, index: int):
        if 0 <= index < len(self._end_marker_values):
            self.current_end_marker = self._end_marker_values[index]
            if self.canvas and self.canvas.editing_item_id:
                self.canvas.update_item_properties(
                    self.canvas.editing_item_id, {"end_marker": self.current_end_marker}
                )

    def on_options_center_marker_changed(self, index: int):
        if 0 <= index < len(self._center_marker_values):
            self.current_center_marker = self._center_marker_values[index]
            if self.canvas and self.canvas.editing_item_id:
                self.canvas.update_item_properties(
                    self.canvas.editing_item_id, {"center_marker": self.current_center_marker}
                )

    def on_options_shape_continuous_changed(self, checked: bool):
        if self.canvas:
            self.canvas.set_shape_continuous(checked)

    def on_options_marker_style_changed(self, style: str):
        self.current_marker_style = style
        if self.canvas and self.canvas.editing_item_id:
            self.canvas.update_item_properties(self.canvas.editing_item_id, {"marker_style": style})
            if self.on_marker_updated_cb:
                self.on_marker_updated_cb()

    def on_options_marker_continuous_changed(self, checked: bool):
        if self.canvas:
            self.canvas.set_shape_continuous(checked)

    def on_options_marker_opacity_changed(self, value: int):
        self.current_marker_opacity = value
        if self.canvas and self.canvas.editing_item_id:
            self.canvas.update_item_properties(self.canvas.editing_item_id, {"stroke_opacity": value})

    def on_options_marker_color_changed(self, color: str):
        self.current_marker_color = color
        if self.canvas:
            self.canvas.set_shape_defaults(color, 2, "")
            if self.canvas.editing_item_id:
                self.canvas.update_item_properties(self.canvas.editing_item_id, {"color": color})

    def on_options_font_changed(self, family: str):
        self.current_text_font = family
        is_cont = self.options_bar.tool_continuous_check.isChecked() if self.options_bar else False
        if self.canvas:
            self.canvas.set_text_defaults(self.current_text_font, self.current_text_size, self.current_text_color, is_cont)
            if self.canvas.editing_item_id:
                self.canvas.update_item_properties(self.canvas.editing_item_id, {"font_family": family})

    def on_options_font_size_changed(self, size: int):
        self.current_text_size = size
        is_cont = self.options_bar.tool_continuous_check.isChecked() if self.options_bar else False
        if self.canvas:
            self.canvas.set_text_defaults(self.current_text_font, self.current_text_size, self.current_text_color, is_cont)
            if self.canvas.editing_item_id:
                self.canvas.update_item_properties(self.canvas.editing_item_id, {"font_size": size})

    def on_options_text_color_changed(self, color: str):
        self.current_text_color = color
        is_cont = self.options_bar.tool_continuous_check.isChecked() if self.options_bar else False
        if self.canvas:
            self.canvas.set_text_defaults(self.current_text_font, self.current_text_size, self.current_text_color, is_cont)
            if self.canvas.editing_item_id:
                self.canvas.update_item_properties(self.canvas.editing_item_id, {"color": color})

    def on_options_text_continuous_changed(self, checked: bool):
        if self.canvas:
            self.canvas.set_text_defaults(self.current_text_font, self.current_text_size, self.current_text_color, checked)

    def on_options_arc_span_changed(self, value: float):
        self.current_arc_span = value
        if self.canvas:
            self.canvas.current_arc_span = value

    def on_options_arc_radial_line_changed(self, checked: bool):
        self.current_arc_show_radial_line = checked
        if self.canvas:
            self.canvas.current_arc_show_radial_line = checked
