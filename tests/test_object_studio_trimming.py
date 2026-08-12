import pytest
import sys
from PySide6.QtWidgets import QApplication
from object_studio.main import MainWindow
from object_studio.models import ObjectDefinition, ObjectSize, ObjectFlags
from object_studio.settings import CANVAS_WIDTH_TILES, CANVAS_HEIGHT_TILES

@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

def test_object_studio_left_trimming_disabled(qapp):
    window = MainWindow()
    
    # Setup a mock current object
    obj = ObjectDefinition(
        id="TEST_TRIM",
        code=99,
        size=ObjectSize(1, 1),
        flags=ObjectFlags(blocking=False),
        tiles=[0]
    )
    window.current_object = obj
    
    # We create a 16x16 grid with tiles
    # Place a non-zero tile at x=3, y=2 (meaning empty space on the left at x=0, 1, 2)
    grid = [[0 for _ in range(CANVAS_WIDTH_TILES)] for _ in range(CANVAS_HEIGHT_TILES)]
    grid[2][3] = 42
    
    # Set the grid to the canvas widget
    window.canvas_widget.grid = grid
    
    # Trigger change callback
    window._on_canvas_changed()
    
    # Expected behavior:
    # min_x is forced to 0 (no trimming on the left)
    # max_x is 3 (trimmed on the right)
    # So width = max_x + 1 = 4
    # min_y is forced to 0 (no trimming on the top)
    # max_y is 2 (trimmed on the bottom)
    # So height = max_y + 1 = 3
    assert obj.size.width == 4
    assert obj.size.height == 3
    
    # Expected tiles list: extracted from y in [0, 1, 2], x in [0, 1, 2, 3]
    expected_tiles = [
        0, 0, 0, 0,  # y=0
        0, 0, 0, 0,  # y=1
        0, 0, 0, 42  # y=2
    ]
    assert obj.tiles == expected_tiles
