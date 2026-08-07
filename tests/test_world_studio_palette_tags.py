import pytest
from pathlib import Path
from PySide6.QtWidgets import QApplication
import sys

from world_studio.project_manager import ProjectManager
from world_studio.models import ObjectDefinition, ObjectSize, ObjectFlags
from world_studio.widgets.object_palette import ObjectPaletteWidget, ALL_TAGS_OPTION

@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

def test_project_manager_loads_available_tags(tmp_path: Path):
    world_dir = tmp_path / "world"
    world_dir.mkdir()

    # world.yaml
    (world_dir / "world.yaml").write_text("world:\n  start_region: REG1\n  start_screen: SCR1\n  start_position:\n    x: 0\n    y: 0\n", encoding="utf-8")
    
    # objects.yaml
    objects_yaml_content = """tags:
  - woda
  - dom
objects:
  - id: WATER_TILE
    code: 1
    size:
      width: 1
      height: 1
    flags:
      blocking: true
    tiles: [10]
    tags: [woda]
  - id: TREE_SMALL
    code: 2
    size:
      width: 1
      height: 1
    flags:
      blocking: false
    tiles: [20]
    tags: [las]
"""
    (world_dir / "objects.yaml").write_text(objects_yaml_content, encoding="utf-8")

    pm = ProjectManager()
    loaded = pm.load_project(world_dir)
    assert loaded is True
    assert "woda" in pm.available_tags
    assert "dom" in pm.available_tags
    assert "las" in pm.available_tags

def test_object_palette_widget_tag_filtering(qapp, tmp_path: Path):
    pm = ProjectManager()
    pm.available_tags = ["woda", "dom", "drzewo"]
    
    obj1 = ObjectDefinition(
        id="WATER_1",
        code=1,
        size=ObjectSize(width=1, height=1),
        flags=ObjectFlags(),
        tiles=[1],
        tags=["woda"]
    )
    obj2 = ObjectDefinition(
        id="HOUSE_1",
        code=2,
        size=ObjectSize(width=1, height=1),
        flags=ObjectFlags(),
        tiles=[2],
        tags=["dom"]
    )
    obj3 = ObjectDefinition(
        id="TREE_1",
        code=3,
        size=ObjectSize(width=1, height=1),
        flags=ObjectFlags(),
        tiles=[3],
        tags=["drzewo"]
    )
    pm.objects = [obj1, obj2, obj3]

    palette = ObjectPaletteWidget()
    palette.action_combo.setCurrentText(ObjectPaletteWidget.ACTION_ADD_OBJECT)
    palette.populate(pm, None)

    # By default, ALL_TAGS_OPTION shows 3 items
    assert palette.list_widget.count() == 3

    # Filter by "woda"
    palette.tag_combo.setCurrentText("woda")
    assert palette.list_widget.count() == 1
    assert palette.list_widget.item(0).text() == "WATER_1"

    # Filter by "dom"
    palette.tag_combo.setCurrentText("dom")
    assert palette.list_widget.count() == 1
    assert palette.list_widget.item(0).text() == "HOUSE_1"

    # Back to "(Wszystkie tagi)"
    palette.tag_combo.setCurrentText(ALL_TAGS_OPTION)
    assert palette.list_widget.count() == 3
