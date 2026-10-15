import pytest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF
from firereview.ui.canvas.view import PDFCanvas
from firereview.controllers.canvas_controller import CanvasController
from firereview.controllers.tool_controller import ToolController
from firereview.services.document_manager import DocumentManager
from firereview.services.measurement_service import MeasurementService
from firereview.ui.panels.navigator_panel import NavigatorPanel
from firereview.ui.panels.property_panel import PropertyPanel


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestNavigatorAutocenter:
    def test_navigator_selection_triggers_center_on_item(self, qapp):
        canvas = PDFCanvas()
        # centerOn メソッドの呼び出しをスパイ
        original_center_on = canvas.centerOn
        center_on_spy = MagicMock(side_effect=original_center_on)
        canvas.centerOn = center_on_spy

        dm = DocumentManager()
        ms = MeasurementService()
        tc = ToolController()
        navigator = NavigatorPanel()
        prop_panel = PropertyPanel()

        controller = CanvasController(
            canvas=canvas,
            document_manager=dm,
            measurement_service=ms,
            tool_controller=tc,
            prop_panel=prop_panel,
            navigator=navigator,
            get_current_page_fn=lambda: 0,
            get_current_scale_factor_fn=lambda: 1.0,
            is_current_page_calibrated_fn=lambda: True,
            set_tool_fn=lambda m: None,
        )

        # マーカー注釈を作成
        controller.on_marker_complete(QPointF(500, 800))
        assert len(dm.model.annotations) == 1
        ann_id = dm.model.annotations[0].id

        # ナビゲーターからオブジェクト選択をシミュレート
        controller.on_object_selected_from_panel(ann_id)

        # 対象アイテムがセンタリングされたことを検証
        assert center_on_spy.called is True
        centered_arg = center_on_spy.call_args[0][0]
        assert centered_arg == canvas.annotation_items[ann_id]
        assert centered_arg.isSelected() is True

        # ナビゲーターとプロパティパネルにも反映されていることを検証
        assert navigator.selected_id == ann_id
        assert prop_panel.current_item_id == ann_id
