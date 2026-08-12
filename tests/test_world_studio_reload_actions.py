import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication
from world_studio.main import WorldStudioMainWindow
from world_studio.charset import Charset
from world_studio.project_manager import ProjectManager

@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

def test_reload_actions_default_state(qapp):
    window = WorldStudioMainWindow()
    assert window.act_reload_objects.isEnabled() is False
    assert window.act_reload_charset.isEnabled() is False

def test_reload_objects_action(qapp, tmp_path):
    # Prepare dummy world directory
    world_dir = tmp_path / "world"
    world_dir.mkdir()
    
    world_yaml = world_dir / "world.yaml"
    world_yaml.write_text("world:\n  start_region: START\n  start_screen: S1\n  start_position: {x: 1, y: 1}\n", encoding="utf-8")
    
    objects_yaml = world_dir / "objects.yaml"
    objects_yaml.write_text("objects: []\ntags: []\n", encoding="utf-8")
    
    window = WorldStudioMainWindow()
    
    with patch("world_studio.main.QFileDialog.getExistingDirectory", return_value=str(world_dir)):
        window.action_open_world()
        
    assert window.act_reload_objects.isEnabled() is True
    
    # Modify objects.yaml
    objects_yaml.write_text("objects:\n  - id: TREE\n    code: 1\n    name: Tree\n    size: {width: 1, height: 1}\n    flags: {blocking: false}\n    tiles: [1]\ntags: [nature]\n", encoding="utf-8")
    
    # Trigger reload
    with patch.object(window, "_refresh_views") as mock_refresh, \
         patch.object(window.object_palette, "populate") as mock_populate:
        window.action_reload_objects()
        assert len(window.project.objects) == 1
        assert window.project.objects[0].id == "TREE"
        mock_populate.assert_called_once()
        mock_refresh.assert_called_once()

def test_reload_charset_action(qapp, tmp_path):
    fnt_file = tmp_path / "font.fnt"
    fnt_file.write_bytes(bytes([0] * 1024))
    
    window = WorldStudioMainWindow()
    
    with patch("world_studio.main.QFileDialog.getOpenFileName", return_value=(str(fnt_file), "")):
        window.action_load_charset()
        
    assert window.act_reload_charset.isEnabled() is True
    assert window.charset.file_path == fnt_file
    
    # Modify font file bytes
    new_data = bytes([255] * 1024)
    fnt_file.write_bytes(new_data)
    
    # Trigger reload
    with patch.object(window, "_refresh_views") as mock_refresh, \
         patch.object(window.object_palette, "populate") as mock_populate:
        window.action_reload_charset()
        assert window.charset.data == bytearray(new_data)
        mock_populate.assert_called_once()
        mock_refresh.assert_called_once()

