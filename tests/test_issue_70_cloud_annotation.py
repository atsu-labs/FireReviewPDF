import os
import math
import fitz
import pytest
from PySide6.QtCore import Qt, QPointF, QPoint, QEvent
from PySide6.QtGui import QMouseEvent, QKeyEvent

from firereview.models import (
    DrawingModel,
    Annotation,
    CloudAnnotation,
    ANNOTATION_REGISTRY,
)
from firereview.services.project_store import save_project, load_project
from firereview.services.pdf_exporter import export_pdf_document
from firereview.services.pdf_renderers import get_renderer, CloudPdfRenderer, CloudRenderer
from firereview.ui.canvas import PDFCanvas, ToolMode
from firereview.ui.canvas.items import CloudItem
from firereview.ui.canvas.utils import compute_cloud_beziers, build_cloud_path
from firereview.ui.components import MainToolBar, ToolOptionsBar
from firereview.ui.panels.property_panel import PropertyPanel
from firereview.ui.panels.navigator_panel import NavigatorPanel
from firereview.controllers import ToolController, CanvasController
from firereview.services import DocumentManager, MeasurementService
from firereview.services.pdf_handler import PDFHandler


class TestCloudModelAndPersistence:
    def test_cloud_annotation_defaults_and_registry(self):
        assert "cloud" in ANNOTATION_REGISTRY
        assert ANNOTATION_REGISTRY["cloud"] is CloudAnnotation

        ann = Annotation("cloud")
        assert isinstance(ann, CloudAnnotation)
        assert ann.type == "cloud"
        assert ann.color == "#ff0000"
        assert ann.fill_color == ""
        assert ann.fill_opacity == 0
        assert ann.line_width == 2
        assert ann.stroke_opacity == 100

    def test_cloud_project_store_roundtrip(self, tmp_path):
        model = DrawingModel()
        cloud = Annotation("cloud")
        cloud.points = [
            QPointF(10.0, 20.0),
            QPointF(110.0, 20.0),
            QPointF(110.0, 80.0),
            QPointF(10.0, 80.0),
        ]
        cloud.color = "#ff0000"
        cloud.fill_color = "#ff0000"
        cloud.fill_opacity = 20
        cloud.line_width = 3
        model.annotations.append(cloud)

        json_path = str(tmp_path / "cloud_project.json")
        save_project(model, json_path)
        loaded = load_project(json_path)

        assert len(loaded.annotations) == 1
        restored = loaded.annotations[0]
        assert isinstance(restored, CloudAnnotation)
        assert restored.type == "cloud"
        assert restored.color == "#ff0000"
        assert restored.fill_color == "#ff0000"
        assert restored.fill_opacity == 20
        assert restored.line_width == 3
        assert len(restored.points) == 4
        assert restored.points[0] == QPointF(10.0, 20.0)
        assert restored.points[2] == QPointF(110.0, 80.0)


class TestCloudGeometry:
    def test_outward_bulge_for_cw_and_ccw_polygons(self):
        # Clockwise on screen (y down)
        cw_pts = [
            QPointF(0, 0),
            QPointF(100, 0),
            QPointF(100, 100),
            QPointF(0, 100),
        ]
        # Counter-clockwise on screen
        ccw_pts = list(reversed(cw_pts))

        center = QPointF(50, 50)
        for pts in (cw_pts, ccw_pts):
            beziers = compute_cloud_beziers(pts)
            assert len(beziers) >= 8
            for start_pt, ctrl1, ctrl2, end_pt in beziers:
                mid_chord = QPointF(
                    (start_pt.x() + end_pt.x()) / 2.0,
                    (start_pt.y() + end_pt.y()) / 2.0,
                )
                mid_ctrl = QPointF(
                    (ctrl1.x() + ctrl2.x()) / 2.0,
                    (ctrl1.y() + ctrl2.y()) / 2.0,
                )
                dist_chord = math.hypot(mid_chord.x() - center.x(), mid_chord.y() - center.y())
                dist_ctrl = math.hypot(mid_ctrl.x() - center.x(), mid_ctrl.y() - center.y())
                # Control points must bulge strictly outward from the polygon center
                assert dist_ctrl > dist_chord

    def test_alternating_large_small_rhythm(self):
        pts = [
            QPointF(0, 0),
            QPointF(120, 0),
            QPointF(120, 80),
            QPointF(0, 80),
        ]
        beziers = compute_cloud_beziers(pts)
        # First two segments along top edge should have different chord lengths (large vs small)
        c0 = math.hypot(
            beziers[0][3].x() - beziers[0][0].x(),
            beziers[0][3].y() - beziers[0][0].y(),
        )
        c1 = math.hypot(
            beziers[1][3].x() - beziers[1][0].x(),
            beziers[1][3].y() - beziers[1][0].y(),
        )
        assert c0 > c1 * 1.3

        path = build_cloud_path(pts)
        assert not path.isEmpty()


class TestCloudCanvasAndTool:
    def test_cloud_tool_drag_and_shift_square_and_min_size(self, qapp):
        canvas = PDFCanvas()
        canvas.resize(800, 600)
        canvas.set_tool_mode(ToolMode.DRAW_CLOUD)

        completed_clouds = []
        canvas.cloud_complete.connect(lambda pts: completed_clouds.append(pts))

        tool = canvas.tools[ToolMode.DRAW_CLOUD]

        # 1. Tiny drag (< 5px) should be ignored
        press_ev = QMouseEvent(
            QEvent.MouseButtonPress, QPointF(100, 100), QPointF(100, 100), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
        )
        release_tiny = QMouseEvent(
            QEvent.MouseButtonRelease, QPointF(102, 103), QPointF(102, 103), Qt.LeftButton, Qt.NoButton, Qt.NoModifier
        )
        tool.mouse_press(press_ev, canvas.scene)
        tool.mouse_release(release_tiny, canvas.scene)
        assert len(completed_clouds) == 0

        # 2. Normal drag with live preview
        canvas.set_tool_mode(ToolMode.DRAW_CLOUD)
        tool.mouse_press(press_ev, canvas.scene)
        move_ev = QMouseEvent(
            QEvent.MouseMove, QPointF(220, 180), QPointF(220, 180), Qt.NoButton, Qt.LeftButton, Qt.NoModifier
        )
        tool.mouse_move(move_ev, canvas.scene)
        assert isinstance(canvas.temp_cloud, CloudItem)

        release_ev = QMouseEvent(
            QEvent.MouseButtonRelease, QPointF(220, 180), QPointF(220, 180), Qt.LeftButton, Qt.NoButton, Qt.NoModifier
        )
        tool.mouse_release(release_ev, canvas.scene)
        assert canvas.temp_cloud is None
        assert len(completed_clouds) == 1
        pts = completed_clouds[0]
        assert len(pts) == 4
        assert abs((pts[1].x() - pts[0].x()) - 120.0) < 1e-3
        assert abs((pts[2].y() - pts[1].y()) - 80.0) < 1e-3

        # 3. Shift-drag constrains to a square
        canvas.set_tool_mode(ToolMode.DRAW_CLOUD)
        tool.mouse_press(press_ev, canvas.scene)
        release_shift = QMouseEvent(
            QEvent.MouseButtonRelease, QPointF(220, 160), QPointF(220, 160), Qt.LeftButton, Qt.NoButton, Qt.ShiftModifier
        )

        tool.mouse_release(release_shift, canvas.scene)
        assert len(completed_clouds) == 2
        sq_pts = completed_clouds[1]
        w = sq_pts[1].x() - sq_pts[0].x()
        h = sq_pts[2].y() - sq_pts[1].y()
        assert abs(w - h) < 1e-3
        assert abs(w - 120.0) < 1e-3

    def test_cloud_node_editing_and_freeform_polygon(self, qapp):
        canvas = PDFCanvas()
        pts = [
            QPointF(50, 50),
            QPointF(150, 50),
            QPointF(150, 150),
            QPointF(50, 150),
        ]
        canvas.add_cloud_annotation(pts, color="#ff0000", item_id="cloud-1")
        item = canvas.annotation_items["cloud-1"]
        assert isinstance(item, CloudItem)

        # Start node editing: should create 4 vertex handles
        canvas.start_node_editing("cloud-1")
        assert len(canvas.vertex_handles) == 4

        # Move vertex 2
        canvas.on_vertex_moved(item, 2, QPointF(200, 200))
        updated_pts = canvas._get_item_points(item)
        assert updated_pts[2] == QPointF(200, 200)

        # Delete a vertex (4 -> 3 allowed)
        canvas.on_vertex_double_clicked(item, 3)
        assert len(canvas._get_item_points(item)) == 3

        # Deleting when at 3 vertices should be blocked (minimum 3 vertices)
        canvas.on_vertex_double_clicked(item, 0)
        assert len(canvas._get_item_points(item)) == 3
        canvas.end_node_editing()

    def test_cloud_isolated_defaults_and_ui_panels(self, qapp):
        toolbar = MainToolBar()
        options_bar = ToolOptionsBar()
        canvas = PDFCanvas()
        prop_panel = PropertyPanel()
        navigator = NavigatorPanel()
        doc_mgr = DocumentManager(PDFHandler())
        meas = MeasurementService()
        tool_ctrl = ToolController(canvas=canvas, options_bar=options_bar, toolbar=toolbar)
        canvas_ctrl = CanvasController(
            canvas=canvas,
            document_manager=doc_mgr,
            measurement_service=meas,
            tool_controller=tool_ctrl,
            prop_panel=prop_panel,
            navigator=navigator,
            get_current_page_fn=lambda: 0,
            get_current_scale_factor_fn=lambda: 1.0,
            is_current_page_calibrated_fn=lambda: False,
            set_tool_fn=tool_ctrl.set_tool,
        )

        # Standard shape defaults are purple (#7c4dff) and fill opacity 30%
        tool_ctrl.set_tool(ToolMode.POLYGON_AREA)
        assert canvas.current_shape_color == "#7c4dff"
        assert canvas.current_fill_opacity == 30

        # Switching to Cloud tool applies dedicated defaults (#ff0000, fill="", opacity=0%)
        tool_ctrl.set_tool(ToolMode.DRAW_CLOUD)
        assert canvas.current_shape_color == "#ff0000"
        assert canvas.current_fill_color == ""
        assert canvas.current_fill_opacity == 0

        # Switching back to Polygon restores purple (#7c4dff)
        tool_ctrl.set_tool(ToolMode.POLYGON_AREA)
        assert canvas.current_shape_color == "#7c4dff"
        assert canvas.current_fill_opacity == 30

        # Complete a cloud and select it
        pts = [QPointF(10, 10), QPointF(110, 10), QPointF(110, 90), QPointF(10, 90)]
        canvas_ctrl.on_cloud_complete(pts)
        assert len(doc_mgr.model.annotations) == 1
        cloud_ann = doc_mgr.model.annotations[0]
        assert cloud_ann.type == "cloud"
        assert cloud_ann.color == "#ff0000"
        assert cloud_ann.fill_opacity == 0

        canvas_ctrl.on_item_selected(cloud_ann.id)
        assert prop_panel.type_title.text() == "雲マーク"
        assert not prop_panel.calc_container.isHidden() is False  # calc_container is hidden
        assert prop_panel.calc_container.isHidden() is True
        assert prop_panel.text_container.isHidden() is True
        assert prop_panel.node_edit_container.isHidden() is False
        assert prop_panel.fill_container.isHidden() is False

        # K key shortcut on canvas switches to DRAW_CLOUD
        requested_modes = []
        canvas.request_tool_change.connect(lambda m: requested_modes.append(m))
        key_ev = QKeyEvent(QEvent.KeyPress, Qt.Key_K, Qt.NoModifier)
        canvas.keyPressEvent(key_ev)
        assert requested_modes == [ToolMode.DRAW_CLOUD]


class TestCloudPdfExport:
    def test_cloud_renderer_registered_and_exports_pdf(self, tmp_path):
        renderer = get_renderer("cloud")
        assert isinstance(renderer, CloudPdfRenderer)
        assert CloudRenderer is CloudPdfRenderer

        pdf_path = str(tmp_path / "source.pdf")
        doc = fitz.open()
        doc.new_page(width=595, height=842)
        doc.save(pdf_path)
        doc.close()

        model = DrawingModel()
        model.pdf_path = pdf_path

        # Cloud without fill
        c1 = Annotation("cloud")
        c1.points = [QPointF(50, 50), QPointF(200, 50), QPointF(200, 150), QPointF(50, 150)]
        model.annotations.append(c1)

        # Cloud with fill
        c2 = Annotation("cloud")
        c2.points = [QPointF(250, 50), QPointF(400, 50), QPointF(400, 180), QPointF(250, 180)]
        c2.fill_color = "#ff0000"
        c2.fill_opacity = 25
        model.annotations.append(c2)

        out_path = str(tmp_path / "exported_cloud.pdf")
        export_pdf_document(model, out_path)

        assert os.path.exists(out_path)
        out_doc = fitz.open(out_path)
        assert len(out_doc) == 1
        drawings = out_doc[0].get_drawings()
        assert len(drawings) >= 2
        out_doc.close()
