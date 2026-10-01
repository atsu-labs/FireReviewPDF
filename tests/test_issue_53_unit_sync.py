import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF
from firereview.ui.components.options_bar import ToolOptionsBar
from firereview.models import DrawingModel
from firereview.services.document_manager import DocumentManager
from firereview.controllers.tool_controller import ToolController
from firereview.controllers.canvas_controller import CanvasController


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestToolOptionsBarUnitSync:
    def test_default_unit_is_meter(self, qapp):
        bar = ToolOptionsBar()
        assert bar.unit == "m"
        assert bar.tool_radius_spin.suffix() == " m"
        assert bar.tool_radius_spin.value() == 15.0
        assert bar.tool_radius_spin.decimals() == 3

    def test_explicit_mm_unit_init(self, qapp):
        bar = ToolOptionsBar(unit="mm")
        assert bar.unit == "mm"
        assert bar.tool_radius_spin.suffix() == " mm"
        assert bar.tool_radius_spin.value() == 15000.0
        assert bar.tool_radius_spin.decimals() == 1

    def test_set_unit_switches_properly(self, qapp):
        bar = ToolOptionsBar()
        assert bar.unit == "m"

        bar.set_unit("mm")
        assert bar.unit == "mm"
        assert bar.tool_radius_spin.suffix() == " mm"
        assert bar.tool_radius_spin.value() == 15000.0

        bar.set_unit("m")
        assert bar.unit == "m"
        assert bar.tool_radius_spin.suffix() == " m"
        assert bar.tool_radius_spin.value() == 15.0

    def test_apply_unit_change_converts_value(self, qapp):
        bar = ToolOptionsBar(unit="m")
        bar.tool_radius_spin.setValue(20.0)

        bar.apply_unit_change("mm", "m")
        assert bar.unit == "mm"
        assert bar.tool_radius_spin.suffix() == " mm"
        assert bar.tool_radius_spin.value() == 20000.0

        bar.apply_unit_change("m", "mm")
        assert bar.unit == "m"
        assert bar.tool_radius_spin.suffix() == " m"
        assert bar.tool_radius_spin.value() == 20.0


class DummyCanvas:
    def __init__(self):
        self.annotations = []

    def add_circle_annotation(self, *args, **kwargs):
        self.annotations.append(("circle", args, kwargs))


class TestCircleUnitCalculation:
    def test_circle_radius_calculation_with_options_bar_unit(self, qapp):
        doc_mgr = DocumentManager()
        canvas = DummyCanvas()
        bar = ToolOptionsBar(unit="m")
        tc = ToolController(options_bar=bar)

        # 1ピクセル = 10mm にキャリブレーション (scale_factor = 10.0)
        doc_mgr.model.scale_factor = 10.0
        doc_mgr.model.is_calibrated = True

        from firereview.services.measurement_service import MeasurementService

        ms = MeasurementService()
        prop_panel = type("DummyPropPanel", (), {"clear_panel": lambda self: None, "set_item_data": lambda *a, **k: None})()
        navigator = type("DummyNavigator", (), {"update_marker_summary": lambda *a, **k: None, "update_objects": lambda *a, **k: None})()

        cc = CanvasController(
            canvas=canvas,
            document_manager=doc_mgr,
            measurement_service=ms,
            tool_controller=tc,
            prop_panel=prop_panel,
            navigator=navigator,
            get_current_page_fn=lambda: 0,
            get_current_scale_factor_fn=lambda: 10.0,
            is_current_page_calibrated_fn=lambda: True,
            set_tool_fn=lambda mode: None,
        )

        # メートル単位時: 半径 15.0 m -> 15,000 mm -> 1,500 px
        bar.tool_radius_spin.setValue(15.0)
        cc.on_circle_drag_complete(QPointF(100, 100), radius_px=1)
        assert len(canvas.annotations) == 1
        assert doc_mgr.model.annotations[0].radius_px == 1500.0

        # mm単位に切り替え: 半径 15000.0 mm -> 15,000 mm -> 1,500 px
        bar.set_unit("mm")
        assert bar.tool_radius_spin.value() == 15000.0
        cc.on_circle_drag_complete(QPointF(200, 200), radius_px=1)
        assert len(canvas.annotations) == 2
        assert doc_mgr.model.annotations[1].radius_px == 1500.0

        # どちらも15km（15,000,000 mm）ではなく15m（15,000 mm）として正しく作図される
        assert doc_mgr.model.annotations[0].radius_px == doc_mgr.model.annotations[1].radius_px


class TestMainWindowUnitSync:
    def test_main_window_initial_unit_sync(self, qapp):
        from firereview.main_window import MainWindow
        win = MainWindow()
        # 初期状態でモデルとオプションバーの単位が完全に一致していること
        assert win.model.unit == "m"
        assert win.options_bar.unit == "m"
        assert win.options_bar.tool_radius_spin.suffix() == " m"
        assert win.options_bar.tool_radius_spin.value() == 15.0
        win.close()
