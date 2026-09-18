import pytest
from PySide6.QtCore import QPointF
from firereview.controllers.canvas_controller import CanvasController
from firereview.controllers.tool_controller import ToolController
from firereview.services.document_manager import DocumentManager
from firereview.services.measurement_service import MeasurementService
from firereview.ui.canvas.enums import ToolMode


class DummyCanvas:
    def __init__(self):
        self.annotations = []
        self.tool_mode = ToolMode.SELECT
        self.editing_item_id = None
        self.active_edit_mode = False

    def add_polygon_annotation(self, *args, **kwargs):
        self.annotations.append(("polygon", args, kwargs))

    def add_polyline_annotation(self, *args, **kwargs):
        self.annotations.append(("polyline", args, kwargs))

    def add_circle_annotation(self, *args, **kwargs):
        self.annotations.append(("circle", args, kwargs))

    def add_arc_annotation(self, *args, **kwargs):
        self.annotations.append(("arc", args, kwargs))

    def add_marker_annotation(self, *args, **kwargs):
        self.annotations.append(("marker", args, kwargs))

    def add_legend_annotation(self, *args, **kwargs):
        self.annotations.append(("legend", args, kwargs))

    def add_text_annotation(self, *args, **kwargs):
        self.annotations.append(("text", args, kwargs))

    def remove_annotation(self, item_id):
        pass

    def update_item_properties(self, item_id, attrs):
        pass

    def update_legends(self, *args, **kwargs):
        pass


class DummyNavigator:
    def __init__(self):
        self.selected_object = None
        self.summary_updated = False
        self.objects_updated = False

    def update_marker_summary(self, *args, **kwargs):
        self.summary_updated = True

    def update_objects(self, *args, **kwargs):
        self.objects_updated = True

    def set_selected_object(self, item_id):
        self.selected_object = item_id

    def set_editing_object(self, item_id, active):
        pass


class DummyPropPanel:
    def __init__(self):
        self.item_data = None
        self.cleared = False

    def set_item_data(self, *args, **kwargs):
        self.item_data = (args, kwargs)

    def clear_panel(self):
        self.cleared = True


class TestCanvasController:
    @pytest.fixture
    def setup_controller(self):
        canvas = DummyCanvas()
        dm = DocumentManager()
        ms = MeasurementService()
        tc = ToolController()
        prop_panel = DummyPropPanel()
        navigator = DummyNavigator()
        current_page = 0
        current_scale = 1.0
        calibrated = True
        active_tool = ToolMode.SELECT

        def set_tool(mode):
            nonlocal active_tool
            active_tool = mode

        cc = CanvasController(
            canvas=canvas,
            document_manager=dm,
            measurement_service=ms,
            tool_controller=tc,
            prop_panel=prop_panel,
            navigator=navigator,
            get_current_page_fn=lambda: current_page,
            get_current_scale_factor_fn=lambda: current_scale,
            is_current_page_calibrated_fn=lambda: calibrated,
            set_tool_fn=set_tool,
        )
        return cc, dm, canvas, navigator, prop_panel

    def test_add_to_model(self, setup_controller):
        cc, dm, canvas, navigator, prop_panel = setup_controller
        ann = cc.add_to_model("line", [QPointF(0, 0), QPointF(10, 10)], real_value=5.0)
        assert ann.type == "line"
        assert len(dm.model.annotations) == 1
        assert dm.is_dirty is True

    def test_on_polygon_complete(self, setup_controller):
        cc, dm, canvas, navigator, prop_panel = setup_controller
        points = [QPointF(0, 0), QPointF(10, 0), QPointF(10, 10)]
        cc.on_polygon_complete(points)
        assert len(dm.model.annotations) == 1
        assert dm.model.annotations[0].type == "polygon"
        assert len(canvas.annotations) == 1
        assert canvas.annotations[0][0] == "polygon"
        assert navigator.objects_updated is True

    def test_on_polyline_complete(self, setup_controller):
        cc, dm, canvas, navigator, prop_panel = setup_controller
        points = [QPointF(0, 0), QPointF(20, 20)]
        cc.on_polyline_complete(points)
        assert len(dm.model.annotations) == 1
        assert dm.model.annotations[0].type == "polyline"
        assert len(canvas.annotations) == 1

    def test_on_delete_item(self, setup_controller):
        cc, dm, canvas, navigator, prop_panel = setup_controller
        ann = cc.add_to_model("marker", [QPointF(5, 5)])
        assert len(dm.model.annotations) == 1
        cc.on_delete_item(ann.id)
        assert len(dm.model.annotations) == 0

    def test_on_item_moved(self, setup_controller):
        cc, dm, canvas, navigator, prop_panel = setup_controller
        ann = cc.add_to_model("text", [QPointF(10, 10)], text="sample")
        dm.set_dirty(False)
        cc.on_item_moved(ann.id, QPointF(5, -3))
        assert ann.points[0] == QPointF(15, 7)
        assert dm.is_dirty is True

    def test_on_selection(self, setup_controller):
        cc, dm, canvas, navigator, prop_panel = setup_controller
        ann = cc.add_to_model("marker", [QPointF(0, 0)])
        cc.on_item_selected(ann.id)
        assert navigator.selected_object == ann.id
        assert prop_panel.item_data is not None

        cc.on_selection_cleared()
        assert navigator.selected_object is None
        assert prop_panel.cleared is True
