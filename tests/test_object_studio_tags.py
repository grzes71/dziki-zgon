import pytest
from pathlib import Path
from object_studio.models import Project, ObjectDefinition, ObjectSize, ObjectFlags
from object_studio.yaml_io import load_project, save_project
from world_builder.model import ObjectDefinition as WBObjectDefinition

def test_object_studio_tags_serialization(tmp_path: Path):
    yaml_file = tmp_path / "test_objects.yaml"

    project = Project()
    project.available_tags = ["woda", "dom", "drzewo"]

    obj1 = ObjectDefinition(
        id="WATER_TILE",
        code=1,
        size=ObjectSize(1, 1),
        flags=ObjectFlags(blocking=True),
        tiles=[10],
        tags=["woda"]
    )
    obj2 = ObjectDefinition(
        id="HOUSE_SMALL",
        code=2,
        size=ObjectSize(2, 2),
        flags=ObjectFlags(blocking=True),
        tiles=[1, 2, 3, 4],
        tags=["dom", "budynek"]
    )
    project.objects = [obj1, obj2]

    # Save project
    saved = save_project(yaml_file, project)
    assert saved is True

    # Load project back
    loaded_project = load_project(yaml_file)
    assert "woda" in loaded_project.available_tags
    assert "dom" in loaded_project.available_tags
    assert "drzewo" in loaded_project.available_tags
    assert "budynek" in loaded_project.available_tags  # tags from object added to available_tags

    o1 = next(o for o in loaded_project.objects if o.id == "WATER_TILE")
    assert o1.tags == ["woda"]

    o2 = next(o for o in loaded_project.objects if o.id == "HOUSE_SMALL")
    assert o2.tags == ["dom", "budynek"]

def test_world_builder_parses_tagged_object():
    wb_obj = WBObjectDefinition(
        id="TEST_OBJ",
        code=100,
        size={"width": 1, "height": 1},
        flags={"blocking": True, "interactive": False, "secret": False},
        tiles=[1],
        tags=["woda", "las"]
    )
    assert wb_obj.tags == ["woda", "las"]
