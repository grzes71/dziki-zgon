import pytest
import sys
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPointF, QPoint
from world_studio.widgets.screen_canvas import ScreenCanvasWidget
from world_studio.models import ScreenDef, ObjectDefinition, ObjectSize, ObjectFlags, ObjectInstance, EnemyInstance
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

def test_enemy_context_menu_actions_and_deletion(qapp):
    canvas = ScreenCanvasWidget()
    pm = ProjectManager()
    
    enemy = EnemyInstance(enemy="strzyga", x=10, y=5, strategy="vertical", speed="medium", color="white")
    screen_def = ScreenDef(
        id="TEST_SCREEN",
        grid_x=0,
        grid_y=0,
        exits={"north": None, "south": None, "east": None, "west": None},
        objects=[],
        enemies=[enemy]
    )
    canvas.set_data(screen_def=screen_def, project=pm, charset=None, region_id="TEST_REGION")
    
    signal_emitted = False
    def on_screen_changed():
        nonlocal signal_emitted
        signal_emitted = True
    canvas.screen_changed.connect(on_screen_changed)
    
    event = MagicMock()
    event.position.return_value = QPointF(160.0, 160.0)
    event.globalPosition.return_value.toPoint.return_value = QPoint(0, 0)
    event.button.return_value = Qt.RightButton
    
    # 1. Test "usuń" action
    with patch("world_studio.widgets.screen_canvas.QMenu") as mock_menu_cls:
        current_menu = MockMenu()
        mock_menu_cls.return_value = current_menu
        
        # Configure menu to select delete
        def custom_exec(point):
            for a in current_menu.actions_list:
                if a.text() == "usuń":
                    return a
            return None
        current_menu.exec = custom_exec

        canvas.mousePressEvent(event)
        
        action_names = [a.text() for a in current_menu.actions()]
        assert action_names == ["usuń", "w prawo", "w lewo", "w górę", "w dół"]
        
        # All directions enabled in empty area
        for a in current_menu.actions():
            assert a.isEnabled()
            
        assert len(screen_def.enemies) == 0
        assert signal_emitted is True

def test_enemy_context_menu_movement_directions(qapp):
    canvas = ScreenCanvasWidget()
    pm = ProjectManager()
    
    directions = [
        ("w prawo", 11, 5),
        ("w lewo", 9, 5),
        ("w górę", 10, 4),
        ("w dół", 10, 6),
    ]
    
    for action_text, expected_x, expected_y in directions:
        enemy = EnemyInstance(enemy="strzyga", x=10, y=5, strategy="vertical", speed="medium", color="white")
        screen_def = ScreenDef(
            id="TEST_SCREEN",
            grid_x=0,
            grid_y=0,
            exits={"north": None, "south": None, "east": None, "west": None},
            objects=[],
            enemies=[enemy]
        )
        canvas.set_data(screen_def=screen_def, project=pm, charset=None, region_id="TEST_REGION")
        
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
            
            assert len(screen_def.enemies) == 1
            assert screen_def.enemies[0].x == expected_x
            assert screen_def.enemies[0].y == expected_y

def test_enemy_context_menu_boundary_restrictions(qapp):
    canvas = ScreenCanvasWidget()
    pm = ProjectManager()
    
    # 1. Top-Left corner (0, 0): cannot move left or up
    enemy_tl = EnemyInstance(enemy="strzyga", x=0, y=0, strategy="vertical", speed="medium", color="white")
    screen_def = ScreenDef(
        id="TEST_SCREEN",
        grid_x=0,
        grid_y=0,
        exits={"north": None, "south": None, "east": None, "west": None},
        objects=[],
        enemies=[enemy_tl]
    )
    canvas.set_data(screen_def=screen_def, project=pm, charset=None, region_id="TEST_REGION")
    
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
        assert action_map["w lewo"] is False # boundary x=0
        assert action_map["w górę"] is False # boundary y=0
        assert action_map["w dół"] is True

    # 2. Bottom-Right corner (39, 11): cannot move right or down
    enemy_br = EnemyInstance(enemy="strzyga", x=39, y=11, strategy="vertical", speed="medium", color="white")
    screen_def.enemies = [enemy_br]
    
    event.position.return_value = QPointF(39.0 * 16.0, 11.0 * 32.0)
    
    with patch("world_studio.widgets.screen_canvas.QMenu") as mock_menu_cls:
        current_menu = MockMenu()
        mock_menu_cls.return_value = current_menu
        canvas.mousePressEvent(event)
        
        action_map = {a.text(): a.isEnabled() for a in current_menu.actions()}
        assert action_map["usuń"] is True
        assert action_map["w prawo"] is False # boundary x=39
        assert action_map["w lewo"] is True
        assert action_map["w górę"] is True
        assert action_map["w dół"] is False # boundary y=11

def test_enemy_context_menu_obstacle_overlap_restrictions(qapp):
    canvas = ScreenCanvasWidget()
    pm = ProjectManager()
    
    # Setup 2x2 object at (11, 5) -> blocking movement to the right of enemy at (10, 5)
    obj_2x2 = ObjectDefinition(
        id="TREE_2X2",
        code=5,
        size=ObjectSize(width=2, height=2),
        flags=ObjectFlags(blocking=True, interactive=False, secret=False),
        tiles=[0] * 4,
        tags=[]
    )
    pm.objects = [obj_2x2]
    
    enemy1 = EnemyInstance(enemy="strzyga", x=10, y=5, strategy="vertical", speed="medium", color="white")
    enemy2 = EnemyInstance(enemy="strzyga", x=9, y=5, strategy="vertical", speed="medium", color="white")
    
    screen_def = ScreenDef(
        id="TEST_SCREEN",
        grid_x=0,
        grid_y=0,
        exits={"north": None, "south": None, "east": None, "west": None},
        objects=[ObjectInstance(object="TREE_2X2", x=11, y=5, **{"repeat-x": 1, "repeat-y": 1})],
        enemies=[enemy1, enemy2]
    )
    canvas.set_data(screen_def=screen_def, project=pm, charset=None, region_id="TEST_REGION")
    
    event = MagicMock()
    event.position.return_value = QPointF(160.0, 160.0) # (10, 5)
    event.globalPosition.return_value.toPoint.return_value = QPoint(0, 0)
    event.button.return_value = Qt.RightButton
    
    with patch("world_studio.widgets.screen_canvas.QMenu") as mock_menu_cls:
        current_menu = MockMenu()
        mock_menu_cls.return_value = current_menu
        canvas.mousePressEvent(event)
        
        action_map = {a.text(): a.isEnabled() for a in current_menu.actions()}
        assert action_map["usuń"] is True
        assert action_map["w prawo"] is False # blocked by TREE_2X2 at (11, 5)
        assert action_map["w lewo"] is False  # blocked by enemy2 at (9, 5)
        assert action_map["w górę"] is True
        assert action_map["w dół"] is True
