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

def test_screen_canvas_dynamic_bounds_clamping_for_larger_objects(qapp):
    canvas = ScreenCanvasWidget()
    pm = ProjectManager()
    
    obj_4x4 = ObjectDefinition(
        id="HOUSE_4X4",
        code=3,
        size=ObjectSize(width=4, height=4),
        flags=ObjectFlags(blocking=True, interactive=False, secret=False),
        tiles=[0] * 16,
        tags=["wieś"]
    )
    obj_6x4 = ObjectDefinition(
        id="HOUSE_6X4",
        code=4,
        size=ObjectSize(width=6, height=4),
        flags=ObjectFlags(blocking=True, interactive=False, secret=False),
        tiles=[0] * 24,
        tags=["wieś"]
    )
    pm.objects = [obj_4x4, obj_6x4]
    
    screen_def = ScreenDef(
        id="TEST_SCREEN_BOUNDS",
        grid_x=0,
        grid_y=0,
        exits={"north": None, "south": None, "east": None, "west": None},
        objects=[],
        enemies=[]
    )
    
    canvas.set_data(screen_def=screen_def, project=pm, charset=None, region_id="TEST_REGION")
    
    # 1. Test 4x4 object near bottom-right corner (click at pixel 630, 375 -> tile 39, 11)
    canvas.active_tool = "HOUSE_4X4"
    event = MagicMock()
    event.position.return_value = QPointF(630.0, 375.0)
    event.button.return_value = Qt.LeftButton
    
    canvas.mousePressEvent(event)
    assert len(screen_def.objects) == 1
    placed_4x4 = screen_def.objects[0]
    # For a 4x4 object, max valid x is 36 (36 + 4 = 40) and max valid y is 8 (8 + 4 = 12)
    assert placed_4x4.x == 36
    assert placed_4x4.y == 8
    assert placed_4x4.x + 4 <= 40
    assert placed_4x4.y + 4 <= 12

    # 2. Test 6x4 object near bottom-right corner
    screen_def.objects = []
    canvas.active_tool = "HOUSE_6X4"
    canvas.mousePressEvent(event)
    assert len(screen_def.objects) == 1
    placed_6x4 = screen_def.objects[0]
    # For a 6x4 object, max valid x is 34 (34 + 6 = 40) and max valid y is 8 (8 + 4 = 12)
    assert placed_6x4.x == 34
    assert placed_6x4.y == 8
    assert placed_6x4.x + 6 <= 40
    assert placed_6x4.y + 4 <= 12

def test_screen_canvas_entity_object_overlap_prevention(qapp):
    from world_studio.models import WorldConfig, StartPosition, RegionDef, PortalEntry, EnemyInstance, RegionLayout
    from unittest.mock import patch
    from PySide6.QtWidgets import QDialog

    canvas = ScreenCanvasWidget()
    pm = ProjectManager()
    
    obj_2x2 = ObjectDefinition(
        id="TREE_2X2",
        code=5,
        size=ObjectSize(width=2, height=2),
        flags=ObjectFlags(blocking=True, interactive=False, secret=False),
        tiles=[0] * 4,
        tags=["las"]
    )
    pm.objects = [obj_2x2]
    pm.world_config = WorldConfig(start_region="TEST_REGION", start_screen="TEST_SCREEN_ENTITIES", start_position=StartPosition(x=4, y=4))
    
    region = RegionDef(id="TEST_REGION", name="Test Region", damage=0, layout=RegionLayout(columns=1, rows=1), start_screen="TEST_SCREEN_ENTITIES", music="music.rmt", portal_entries={
        "OTHER_REGION": PortalEntry(screen="TEST_SCREEN_ENTITIES", x=10, y=6)
    })
    pm.regions = {"TEST_REGION": region}
    
    screen_def = ScreenDef(
        id="TEST_SCREEN_ENTITIES",
        grid_x=0,
        grid_y=0,
        exits={"north": None, "south": None, "east": None, "west": None},
        objects=[],
        enemies=[EnemyInstance(enemy="strzyga", x=16, y=8, strategy="vertical", speed="medium", color="white")]
    )
    
    canvas.set_data(screen_def=screen_def, project=pm, charset=None, region_id="TEST_REGION")
    canvas.active_tool = "TREE_2X2"
    
    event = MagicMock()
    event.button.return_value = Qt.LeftButton
    
    with patch.object(QDialog, 'exec', return_value=QDialog.Accepted), patch("world_studio.widgets.screen_canvas.QMessageBox.information"):
        # 1. Try placing 2x2 object overlapping Player Start at (4, 4) -> click at (4, 4) -> (4*16, 4*32) = (64, 128)
        event.position.return_value = QPointF(64.0, 128.0)
        canvas.mousePressEvent(event)
        assert len(screen_def.objects) == 0 # Placement blocked due to Player Start overlap
        
        # 2. Try placing 2x2 object overlapping Portal Entry at (10, 6) -> click at (10, 6) -> (160, 192)
        event.position.return_value = QPointF(160.0, 192.0)
        canvas.mousePressEvent(event)
        assert len(screen_def.objects) == 0 # Placement blocked due to Portal Entry overlap
        
        # 3. Try placing 2x2 object overlapping Enemy at (16, 8) -> click at (16, 8) -> (256, 256)
        event.position.return_value = QPointF(256.0, 256.0)
        canvas.mousePressEvent(event)
        assert len(screen_def.objects) == 0 # Placement blocked due to Enemy overlap

        # 4. Place 2x2 object at clear location (20, 2) -> (320, 64)
        event.position.return_value = QPointF(320.0, 64.0)
        canvas.mousePressEvent(event)
        assert len(screen_def.objects) == 1
        assert screen_def.objects[0].x == 20
        assert screen_def.objects[0].y == 2

        # 5. Try placing Enemy on top of the placed object at (20, 2)
        canvas.active_tool = "ENEMY"
        canvas.mousePressEvent(event)
        assert len(screen_def.enemies) == 1 # Second enemy blocked because of object overlap



