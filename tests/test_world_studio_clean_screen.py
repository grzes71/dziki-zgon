import pytest
import sys
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication, QMessageBox, QTreeWidgetItem
from PySide6.QtCore import Qt, QPoint
from world_studio.widgets.region_tree import RegionTreeWidget
from world_studio.widgets.live_region_view import LiveRegionViewWidget
from world_studio.main import WorldStudioMainWindow
from world_studio.models import ScreenDef, ObjectInstance

@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

def test_region_tree_context_menu_clean(qapp):
    tree = RegionTreeWidget()
    
    signal_received = None
    def handle_signal(r_id, s_id):
        nonlocal signal_received
        signal_received = (r_id, s_id)
        
    tree.request_clean_screen.connect(handle_signal)
    
    # Create a mock SCREEN tree item
    item = QTreeWidgetItem(tree, ["SCREEN1"])
    item.setData(0, 32, "SCREEN")
    item.setData(0, 33, "REGION1")
    item.setData(0, 34, "SCREEN1")
    
    # Mock itemAt to return our screen item
    tree.itemAt = MagicMock(return_value=item)
    
    with patch("world_studio.widgets.region_tree.QMenu") as mock_qmenu_class:
        mock_menu = MagicMock()
        mock_qmenu_class.return_value = mock_menu
        
        mock_clean_action = MagicMock()
        mock_menu.addAction.return_value = mock_clean_action
        
        # Trigger context menu
        tree._on_context_menu(QPoint(5, 5))
        
        # Retrieve QAction passed to menu.addAction
        assert mock_menu.addAction.call_count == 1
        qaction = mock_menu.addAction.call_args[0][0]
        
        # Trigger the action to emit signal
        qaction.trigger()
        assert signal_received == ("REGION1", "SCREEN1")

def test_live_region_view_context_menu_clean(qapp):
    view = LiveRegionViewWidget()
    
    signal_received = None
    def handle_signal(r_id, s_id):
        nonlocal signal_received
        signal_received = (r_id, s_id)
        
    view.screen_clean_requested.connect(handle_signal)
    
    # Setup mock project and data
    view.region_id = "REGION1"
    view.project = MagicMock()
    
    # Setup hovered cell and a screen at that position
    view.hovered_cell = (0, 0)
    screen_def = MagicMock()
    screen_def.grid_x = 0
    screen_def.grid_y = 0
    view.project.screens = {"REGION1": {"SCREEN1": screen_def}}
    
    with patch("world_studio.widgets.live_region_view.QMenu") as mock_qmenu_class:
        mock_menu = MagicMock()
        mock_qmenu_class.return_value = mock_menu
        
        mock_clean_action = MagicMock()
        mock_menu.addAction.side_effect = lambda text: mock_clean_action if text == "Clean" else MagicMock()
        mock_menu.exec.return_value = mock_clean_action
        
        # Trigger contextMenuEvent
        event = MagicMock()
        event.globalPos.return_value = QPoint(100, 100)
        view.contextMenuEvent(event)
        
        # Verify signal was emitted
        assert signal_received == ("REGION1", "SCREEN1")

def test_main_window_clean_screen(qapp):
    window = WorldStudioMainWindow()
    window.current_region_id = "REGION1"
    window.current_screen_id = "SCREEN1"
    
    screen_def = ScreenDef(
        id="SCREEN1",
        objects=[
            ObjectInstance(object="WALL", x=0, y=0),
            ObjectInstance(object="WALL", x=2, y=2)
        ]
    )
    window.project = MagicMock()
    window.project.screens = {"REGION1": {"SCREEN1": screen_def}}
    
    window.canvas_view = MagicMock()
    window.live_view = MagicMock()
    
    # Case 1: QMessageBox returns Yes (confirm clean)
    with patch("PySide6.QtWidgets.QMessageBox.question", return_value=QMessageBox.Yes) as mock_question:
        window._on_clean_screen("REGION1", "SCREEN1")
        mock_question.assert_called_once()
        assert len(screen_def.objects) == 0
        window.canvas_view.update.assert_called_once()
        
    # Reset objects
    screen_def.objects = [
        ObjectInstance(object="WALL", x=0, y=0)
    ]
    
    # Case 2: QMessageBox returns No (cancel clean)
    window.canvas_view.reset_mock()
    with patch("PySide6.QtWidgets.QMessageBox.question", return_value=QMessageBox.No) as mock_question:
        window._on_clean_screen("REGION1", "SCREEN1")
        mock_question.assert_called_once()
        assert len(screen_def.objects) == 1
        window.canvas_view.update.assert_not_called()
