import pytest
import sys
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPointF, QPoint
from world_studio.widgets.screen_canvas import ScreenCanvasWidget
from world_studio.models import ScreenDef, ObjectDefinition, ObjectSize, ObjectFlags, ObjectInstance, RegionDef, PortalEntry
from world_studio.project_manager import ProjectManager

@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

class MockAction:
    def __init__(self, text):
        self.text_val = text
        self.enabled = True
    def text(self):
        return self.text_val
    def isEnabled(self):
        return self.enabled
    def setEnabled(self, val):
        self.enabled = val

class MockMenu:
    def __init__(self, parent=None):
        self.actions_list = []
        self.selected_action = None

    def addAction(self, text):
        act = MockAction(text)
        self.actions_list.append(act)
        return act

    def actions(self):
        return self.actions_list

    def exec(self, point):
        return self.selected_action

def test_portal_entry_left_click_shows_info_dialog(qapp):
    canvas = ScreenCanvasWidget()
    pm = ProjectManager()
    
    region = RegionDef(
        id="TARGET_REGION",
        name="docelowy region",
        layout={"rows": 2, "columns": 2},
        start_screen="TEST_SCREEN",
        music="TEST_MUSIC",
        portal_entries={
            "SRC_REGION": PortalEntry(screen="TEST_SCREEN", x=10, y=5)
        }
    )
    src_region = RegionDef(
        id="SRC_REGION",
        name="źródłowy las",
        layout={"rows": 2, "columns": 2},
        start_screen="START",
        music="TEST_MUSIC",
    )
    pm.regions = {"TARGET_REGION": region, "SRC_REGION": src_region}
    
    screen_def = ScreenDef(
        id="TEST_SCREEN",
        grid_x=0,
        grid_y=0,
        exits={"north": None, "south": None, "east": None, "west": None},
        objects=[]
    )
    canvas.set_data(screen_def=screen_def, project=pm, charset=None, region_id="TARGET_REGION")
    
    event = MagicMock()
    event.position.return_value = QPointF(160.0, 160.0)  # x=10, y=5 at zoom=4 (tile_w=4*4=16, tile_h=8*4=32)
    event.button.return_value = Qt.LeftButton
    
    with patch("world_studio.widgets.screen_canvas.QMessageBox.information") as mock_info:
        canvas.mousePressEvent(event)
        
        assert mock_info.called
        args, kwargs = mock_info.call_args
        title = args[1]
        msg = args[2]
        assert "Portal Entry" in title
        assert "SRC_REGION" in msg
        assert "źródłowy las" in msg
        assert "(10, 5)" in msg

def test_portal_entry_context_menu_actions_and_deletion(qapp):
    canvas = ScreenCanvasWidget()
    pm = ProjectManager()
    
    region = RegionDef(
        id="TARGET_REGION",
        name="docelowy region",
        layout={"rows": 2, "columns": 2},
        start_screen="TEST_SCREEN",
        music="TEST_MUSIC",
        portal_entries={
            "SRC_REGION": PortalEntry(screen="TEST_SCREEN", x=10, y=5)
        }
    )
    pm.regions = {"TARGET_REGION": region}
    
    screen_def = ScreenDef(
        id="TEST_SCREEN",
        grid_x=0,
        grid_y=0,
        exits={"north": None, "south": None, "east": None, "west": None},
        objects=[]
    )
    canvas.set_data(screen_def=screen_def, project=pm, charset=None, region_id="TARGET_REGION")
    
    signal_emitted = False
    def on_screen_changed():
        nonlocal signal_emitted
        signal_emitted = True
    canvas.screen_changed.connect(on_screen_changed)
    
    event = MagicMock()
    event.position.return_value = QPointF(160.0, 160.0)  # x=10, y=5
    event.globalPosition.return_value.toPoint.return_value = QPoint(0, 0)
    event.button.return_value = Qt.RightButton
    
    # Test "usuń" action
    with patch("world_studio.widgets.screen_canvas.QMenu") as mock_menu_cls:
        current_menu = MockMenu()
        mock_menu_cls.return_value = current_menu
        
        def custom_exec(point):
            for a in current_menu.actions_list:
                if a.text() == "usuń":
                    return a
            return None
        current_menu.exec = custom_exec

        canvas.mousePressEvent(event)
        
        action_names = [a.text() for a in current_menu.actions()]
        assert action_names == ["usuń", "w prawo", "w lewo", "w górę", "w dół"]
        
        for a in current_menu.actions():
            assert a.isEnabled()
            
        assert "SRC_REGION" not in region.portal_entries
        assert signal_emitted is True

def test_portal_entry_context_menu_movement_directions(qapp):
    canvas = ScreenCanvasWidget()
    pm = ProjectManager()
    
    directions = [
        ("w prawo", 11, 5),
        ("w lewo", 9, 5),
        ("w górę", 10, 4),
        ("w dół", 10, 6),
    ]
    
    for action_text, expected_x, expected_y in directions:
        region = RegionDef(
            id="TARGET_REGION",
            name="docelowy region",
            layout={"rows": 2, "columns": 2},
            start_screen="TEST_SCREEN",
        music="TEST_MUSIC",
            portal_entries={
                "SRC_REGION": PortalEntry(screen="TEST_SCREEN", x=10, y=5)
            }
        )
        pm.regions = {"TARGET_REGION": region}
        
        screen_def = ScreenDef(
            id="TEST_SCREEN",
            grid_x=0,
            grid_y=0,
            exits={"north": None, "south": None, "east": None, "west": None},
            objects=[]
        )
        canvas.set_data(screen_def=screen_def, project=pm, charset=None, region_id="TARGET_REGION")
        
        event = MagicMock()
        event.position.return_value = QPointF(160.0, 160.0)
        event.globalPosition.return_value.toPoint.return_value = QPoint(0, 0)
        event.button.return_value = Qt.RightButton
        
        with patch("world_studio.widgets.screen_canvas.QMenu") as mock_menu_cls:
            current_menu = MockMenu()
            mock_menu_cls.return_value = current_menu
            
            def custom_exec(point, sel=action_text):
                for a in current_menu.actions_list:
                    if a.text() == sel:
                        return a
                return None
            current_menu.exec = custom_exec

            canvas.mousePressEvent(event)
            
            entry = region.portal_entries["SRC_REGION"]
            assert entry.x == expected_x
            assert entry.y == expected_y

def test_portal_entry_context_menu_boundary_and_obstacle_restrictions(qapp):
    canvas = ScreenCanvasWidget()
    pm = ProjectManager()
    
    # 1. Top-Left corner (0, 0): cannot move left or up
    region_tl = RegionDef(
        id="TARGET_REGION",
        name="docelowy region",
        layout={"rows": 2, "columns": 2},
        start_screen="TEST_SCREEN",
        music="TEST_MUSIC",
        portal_entries={
            "SRC_REGION": PortalEntry(screen="TEST_SCREEN", x=0, y=0)
        }
    )
    pm.regions = {"TARGET_REGION": region_tl}
    
    screen_def = ScreenDef(
        id="TEST_SCREEN",
        grid_x=0,
        grid_y=0,
        exits={"north": None, "south": None, "east": None, "west": None},
        objects=[]
    )
    canvas.set_data(screen_def=screen_def, project=pm, charset=None, region_id="TARGET_REGION")
    
    event = MagicMock()
    event.position.return_value = QPointF(0.0, 0.0)
    event.globalPosition.return_value.toPoint.return_value = QPoint(0, 0)
    event.button.return_value = Qt.RightButton
    
    with patch("world_studio.widgets.screen_canvas.QMenu") as mock_menu_cls:
        current_menu = MockMenu()
        mock_menu_cls.return_value = current_menu
        canvas.mousePressEvent(event)
        
        action_map = {a.text(): a.isEnabled() for a in current_menu.actions()}
        assert action_map["usuń"] is True
        assert action_map["w prawo"] is True
        assert action_map["w lewo"] is False  # boundary x=0
        assert action_map["w górę"] is False  # boundary y=0
        assert action_map["w dół"] is True

    # 2. Obstacle blocking right movement
    obj_2x2 = ObjectDefinition(
        id="ROCK_2X2",
        code=12,
        size=ObjectSize(width=2, height=2),
        flags=ObjectFlags(blocking=True, interactive=False, secret=False),
        tiles=[0] * 4,
        tags=[]
    )
    pm.objects = [obj_2x2]
    
    region_obs = RegionDef(
        id="TARGET_REGION",
        name="docelowy region",
        layout={"rows": 2, "columns": 2},
        start_screen="TEST_SCREEN",
        music="TEST_MUSIC",
        portal_entries={
            "SRC_REGION": PortalEntry(screen="TEST_SCREEN", x=10, y=5)
        }
    )
    pm.regions = {"TARGET_REGION": region_obs}
    screen_def.objects = [ObjectInstance(object="ROCK_2X2", x=11, y=5, **{"repeat-x": 1, "repeat-y": 1})]
    
    event.position.return_value = QPointF(160.0, 160.0)
    
    with patch("world_studio.widgets.screen_canvas.QMenu") as mock_menu_cls:
        current_menu = MockMenu()
        mock_menu_cls.return_value = current_menu
        canvas.mousePressEvent(event)
        
        action_map = {a.text(): a.isEnabled() for a in current_menu.actions()}
        assert action_map["usuń"] is True
        assert action_map["w prawo"] is False  # blocked by ROCK_2X2 at (11, 5)
        assert action_map["w lewo"] is True
        assert action_map["w górę"] is True
        assert action_map["w dół"] is True
