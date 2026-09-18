import pytest
from firereview.controllers.tool_controller import ToolController
from firereview.ui.canvas.enums import ToolMode


class TestToolController:
    def test_default_values(self):
        tc = ToolController()
        assert tc.current_shape_color == "#7c4dff"
        assert tc.current_line_width == 2
        assert tc.current_fill_color == "#7c4dff"
        assert tc.current_fill_opacity == 30
        assert tc.current_marker_style == "square"
        assert tc.current_marker_color == "#ff1744"
        assert tc.current_text_font == "BIZ UDゴシック"
        assert tc.current_text_size == 12

    def test_options_line_width_changed(self):
        tc = ToolController()
        tc.on_options_line_width_changed(5)
        assert tc.current_line_width == 5

    def test_options_shape_color_changed(self):
        tc = ToolController()
        tc.on_options_shape_color_changed("#00ff00")
        assert tc.current_shape_color == "#00ff00"

    def test_options_fill_color_and_opacity_changed(self):
        tc = ToolController()
        tc.on_options_fill_color_changed("#0000ff")
        assert tc.current_fill_color == "#0000ff"
        tc.on_options_fill_opacity_changed(80)
        assert tc.current_fill_opacity == 80

    def test_marker_options_changed(self):
        updated = False

        def on_updated():
            nonlocal updated
            updated = True

        class DummyCanvas:
            def __init__(self):
                self.editing_item_id = "marker_1"
            def update_item_properties(self, item_id, attrs):
                pass
            def set_shape_defaults(self, color, width, fill):
                pass

        tc = ToolController(on_marker_updated_cb=on_updated)
        tc.canvas = DummyCanvas()
        tc.on_options_marker_color_changed("#123456")
        assert tc.current_marker_color == "#123456"

        tc.on_options_marker_style_changed("circle")
        assert tc.current_marker_style == "circle"
        assert updated is True

    def test_marker_start_end_center_values(self):
        tc = ToolController()
        tc.on_options_start_marker_changed(1)
        assert tc.current_start_marker == "circle"

        tc.on_options_end_marker_changed(2)
        assert tc.current_end_marker == "arrow"

        tc.on_options_center_marker_changed(2)
        assert tc.current_center_marker == "cross"

    def test_text_options_changed(self):
        tc = ToolController()
        tc.on_options_font_changed("Meiryo")
        assert tc.current_text_font == "Meiryo"
        tc.on_options_font_size_changed(16)
        assert tc.current_text_size == 16
        tc.on_options_text_color_changed("#ffffff")
        assert tc.current_text_color == "#ffffff"
