import pytest
import sys
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPointF
from world_studio.widgets.screen_canvas import ScreenCanvasWidget
from world_studio.models import ScreenDef, ObjectDefinition, ObjectSize, ObjectFlags
from world_studio.project_manager import ProjectManager

@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

def test_screen_canvas_coordinate_snapping(qapp):
    # Set up ScreenCanvasWidget
    canvas = ScreenCanvasWidget()
    
    # Set up project manager and a dummy object definition (non-interactive, non-secret)
    pm = ProjectManager()
    obj_def = ObjectDefinition(
        id="TREE_SMALL",
        code=2,
        size=ObjectSize(width=2, height=2),
        flags=ObjectFlags(blocking=True, interactive=False, secret=False),
        tiles=[20],
        tags=["las"]
    )
    pm.objects = [obj_def]
    
    # Set up a dummy screen definition
    screen_def = ScreenDef(
        id="TEST_SCREEN",
        grid_x=0,
        grid_y=0,
        exits={"north": None, "south": None, "east": None, "west": None},
        objects=[],
        enemies=[]
    )
    
    canvas.set_data(screen_def=screen_def, project=pm, charset=None, region_id="TEST_REGION")
    canvas.active_tool = "TREE_SMALL"
    
    # Zoom = 4, tile_w_px = 4, tile_h_px = 8
    # A click at tile position (3, 3) -> pixel (3 * 4 * 4, 3 * 8 * 4) = (48, 96)
    # The float coordinates will be click_x = 3.0, click_y = 3.0.
    # Snapped to nearest even coordinates:
    # x = (3.0 + 1.0) // 2 * 2 = 4
    # y = (3.0 + 1.0) // 2 * 2 = 4
    event = MagicMock()
    event.position.return_value = QPointF(48.0, 96.0)
    event.button.return_value = Qt.LeftButton
    
    canvas.mousePressEvent(event)
    
    # Verify the object was placed and its coordinates are snapped to (4, 4)
    assert len(screen_def.objects) == 1
    placed_obj = screen_def.objects[0]
    assert placed_obj.object == "TREE_SMALL"
    assert placed_obj.x == 4
    assert placed_obj.y == 4
    
    # Test boundary clamping at max limits (x > 38, y > 10)
    # click_x = 42.0 (off-grid right), click_y = 13.0 (off-grid bottom)
    # This gets clamped to max even coordinates: x = 38, y = 10
    screen_def.objects = [] # clear objects
    
    # We must mock position() to be within widget boundaries so mousePressEvent doesn't return early.
    # The canvas widget size is grid_width * tile_w_px * zoom = 40 * 4 * 4 = 640
    # and grid_height * tile_h_px * zoom = 12 * 8 * 4 = 384
    # A click at pixel (630, 375) translates to float tile coordinates:
    # click_x = 630 / 16 = 39.375
    # click_y = 375 / 32 = 11.71875
    # Standard tile coordinates would be (39, 11).
    # Snapping logic:
    # x = (39.375 + 1.0) // 2 * 2 = 40.0 -> clamped to 38
    # y = (11.71875 + 1.0) // 2 * 2 = 12.0 -> clamped to 10
    event.position.return_value = QPointF(630.0, 375.0)
    canvas.mousePressEvent(event)
    
    assert len(screen_def.objects) == 1
    placed_obj = screen_def.objects[0]
    assert placed_obj.x == 38
    assert placed_obj.y == 10
