import pytest
from PySide6.QtCore import Qt, QPointF
from PySide6.QtWidgets import QPushButton

from firereview.ui.components.color_picker_popup import (
    ColorPickerPopup,
    STANDARD_PALETTE_COLORS,
    _RECENT_COLORS_HISTORY,
    add_to_recent_colors,
)
from firereview.ui.components.options_bar import ToolOptionsBar
from firereview.ui.panels.property_panel import PropertyPanel
from firereview.controllers.tool_controller import ToolController


class TestColorPickerPopup:
    def test_popup_initialization_standard_colors(self, qtbot):
        popup = ColorPickerPopup(current_color="#ff1744", allow_none=False)
        qtbot.addWidget(popup)

        assert len(STANDARD_PALETTE_COLORS) == 12
        chips = popup.findChildren(QPushButton, "")
        # Filter buttons that are color chips
        color_chips = [b for b in chips if b.property("class") == "colorChip"]
        assert len(color_chips) >= 12

        # allow_none=False なので塗りなしボタンが存在しない
        none_btn = popup.findChild(QPushButton, "noneBtn")
        assert none_btn is None

    def test_popup_allow_none(self, qtbot):
        popup = ColorPickerPopup(current_color="#2979ff", allow_none=True)
        qtbot.addWidget(popup)

        none_btn = popup.findChild(QPushButton, "noneBtn")
        assert none_btn is not None

        selected_colors = []
        popup.color_selected.connect(lambda c: selected_colors.append(c))

        qtbot.mouseClick(none_btn, Qt.LeftButton)
        assert len(selected_colors) == 1
        assert selected_colors[0] == ""

    def test_popup_select_color_chip_and_recent_history(self, qtbot):
        popup = ColorPickerPopup(current_color="#000000", allow_none=False)
        qtbot.addWidget(popup)

        selected_colors = []
        popup.color_selected.connect(lambda c: selected_colors.append(c))

        chips = [b for b in popup.findChildren(QPushButton) if b.property("class") == "colorChip"]
        # Click the first color chip (#ff1744)
        qtbot.mouseClick(chips[0], Qt.LeftButton)

        assert len(selected_colors) == 1
        assert selected_colors[0] == STANDARD_PALETTE_COLORS[0]
        assert _RECENT_COLORS_HISTORY[0] == STANDARD_PALETTE_COLORS[0].lower()

    def test_add_to_recent_colors_limit_and_deduplication(self):
        # Clear history
        _RECENT_COLORS_HISTORY.clear()

        for c in ["#111111", "#222222", "#333333", "#444444", "#555555", "#666666"]:
            add_to_recent_colors(c)

        # Max 5 items
        assert len(_RECENT_COLORS_HISTORY) == 5
        assert _RECENT_COLORS_HISTORY[0] == "#666666"

        # Duplicate should move to front
        add_to_recent_colors("#444444")
        assert len(_RECENT_COLORS_HISTORY) == 5
        assert _RECENT_COLORS_HISTORY[0] == "#444444"


class TestToolOptionsBarColorLinking:
    def test_options_bar_default_link_state(self, qtbot):
        bar = ToolOptionsBar()
        qtbot.addWidget(bar)

        assert bar.is_color_linked is True
        assert bar.tool_fill_link_check.isChecked() is True

    def test_shape_color_change_syncs_fill_when_linked(self, qtbot):
        bar = ToolOptionsBar()
        qtbot.addWidget(bar)

        fill_colors = []
        bar.fill_color_changed.connect(lambda c: fill_colors.append(c))

        # Change shape color
        bar._apply_shape_color("#2979ff")

        assert bar.current_shape_color == "#2979ff"
        assert bar.current_fill_color == "#2979ff"
        assert "#2979ff" in fill_colors

    def test_manual_fill_color_disconnects_link(self, qtbot):
        bar = ToolOptionsBar()
        qtbot.addWidget(bar)

        # Initial: linked with #7c4dff
        assert bar.is_color_linked is True

        # Manually change fill to a different color
        bar._apply_fill_color("#ffd600")

        assert bar.current_fill_color == "#ffd600"
        assert bar.is_color_linked is False
        assert bar.tool_fill_link_check.isChecked() is False

        # Changing shape color afterwards should NOT change fill color
        bar._apply_shape_color("#ff1744")
        assert bar.current_shape_color == "#ff1744"
        assert bar.current_fill_color == "#ffd600"

    def test_clear_fill_disconnects_link(self, qtbot):
        bar = ToolOptionsBar()
        qtbot.addWidget(bar)

        assert bar.is_color_linked is True
        bar._on_fill_color_cleared()

        assert bar.current_fill_color == ""
        assert bar.is_color_linked is False
        assert bar.tool_fill_link_check.isChecked() is False

    def test_relink_syncs_fill_to_stroke(self, qtbot):
        bar = ToolOptionsBar()
        qtbot.addWidget(bar)

        bar.current_shape_color = "#ff9100"
        bar.tool_fill_link_check.setChecked(False)
        bar.current_fill_color = "#000000"

        # Turn link ON
        bar.tool_fill_link_check.setChecked(True)

        assert bar.is_color_linked is True
        assert bar.current_fill_color == "#ff9100"

    def test_text_color_apply(self, qtbot):
        bar = ToolOptionsBar()
        qtbot.addWidget(bar)

        text_colors = []
        bar.text_color_changed.connect(lambda c: text_colors.append(c))

        bar._apply_text_color("#00e676")
        assert bar.current_text_color == "#00e676"
        assert text_colors == ["#00e676"]


class TestPropertyPanelColorLinking:
    def test_property_panel_link_checkbox(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)

        assert hasattr(panel, "fill_link_check")
        assert panel.fill_link_check is not None

    def test_property_panel_set_item_data_auto_detects_link(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)

        # 1. Circle with matching color & fill_color -> linked
        panel.set_item_data(
            item_id="item-1",
            item_type="circle",
            text="",
            color_hex="#2979ff",
            fill_color="#2979ff",
            fill_opacity=30,
        )
        assert panel.fill_link_check.isChecked() is True

        # 2. Polygon with different colors -> unlinked
        panel.set_item_data(
            item_id="item-2",
            item_type="polygon",
            text="",
            color_hex="#2979ff",
            fill_color="#ffd600",
            fill_opacity=30,
        )
        assert panel.fill_link_check.isChecked() is False

    def test_property_panel_stroke_color_syncs_fill_when_linked(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)

        panel.set_item_data(
            item_id="item-1",
            item_type="polygon",
            text="",
            color_hex="#ff1744",
            fill_color="#ff1744",
            fill_opacity=30,
        )
        assert panel.fill_link_check.isChecked() is True

        emitted_changes = []
        panel.attribute_changed.connect(lambda item_id, attrs: emitted_changes.append(attrs))

        # Change stroke color
        panel._apply_color("#00e676")

        assert len(emitted_changes) == 1
        attrs = emitted_changes[0]
        assert attrs["color"] == "#00e676"
        assert attrs["fill_color"] == "#00e676"
        assert panel.current_fill_color == "#00e676"

    def test_property_panel_manual_fill_unlinks(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)

        panel.set_item_data(
            item_id="item-1",
            item_type="polygon",
            text="",
            color_hex="#ff1744",
            fill_color="#ff1744",
            fill_opacity=30,
        )
        assert panel.fill_link_check.isChecked() is True

        # Manually change fill to different color
        panel._apply_fill_color("#2979ff")
        assert panel.fill_link_check.isChecked() is False


class TestToolControllerColorLinking:
    def test_tool_controller_shape_color_syncs_fill(self):
        controller = ToolController()
        assert controller.is_color_linked is True

        controller.on_options_shape_color_changed("#ff9100")
        assert controller.current_shape_color == "#ff9100"
        assert controller.current_fill_color == "#ff9100"

        # Disconnect link
        controller.on_options_color_link_changed(False)
        assert controller.is_color_linked is False

        controller.on_options_shape_color_changed("#00e5ff")
        assert controller.current_shape_color == "#00e5ff"
        # fill should remain unchanged
        assert controller.current_fill_color == "#ff9100"
