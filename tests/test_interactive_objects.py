import pytest
from pathlib import Path
from world_studio.project_manager import ProjectManager
from world_studio.models import ObjectDefinition, ObjectSize, ObjectFlags, ScreenDef, ObjectInstance, WorldConfig, StartPosition, RegionDef, RegionLayout
from world_builder.validator import WorldValidator, ValidationError
from world_builder.parser import parse_world_dir

def test_project_manager_interactive_object_validation(tmp_path):
    pm = ProjectManager()
    
    # Define objects: BOX (not interactive), KEY (interactive)
    obj_box = ObjectDefinition(
        id="BOX", code=1, size=ObjectSize(width=2, height=2),
        flags=ObjectFlags(blocking=True, interactive=False), tiles=[1, 2, 3, 4]
    )
    obj_key = ObjectDefinition(
        id="KEY", code=2, size=ObjectSize(width=1, height=1),
        flags=ObjectFlags(blocking=False, interactive=True), tiles=[5]
    )
    pm.objects = [obj_box, obj_key]
    
    # Create screen with 1 KEY and 2 BOXes
    screen1 = ScreenDef(
        id="SCR1",
        objects=[
            ObjectInstance(object="BOX", x=0, y=0),
            ObjectInstance(object="BOX", x=5, y=5),
            ObjectInstance(object="KEY", x=10, y=2)
        ]
    )
    pm.screens = {"REG1": {"SCR1": screen1}}
    
    # 1 instance of KEY -> should pass validation
    errors = pm.validate_interactive_objects()
    assert len(errors) == 0
    
    # Add second KEY instance to screen2 (different screen -> should pass validation)
    screen2 = ScreenDef(
        id="SCR2",
        objects=[
            ObjectInstance(object="KEY", x=2, y=2)
        ]
    )
    pm.screens["REG1"]["SCR2"] = screen2
    
    # 2 instances of KEY on different screens -> should pass validation
    errors = pm.validate_interactive_objects()
    assert len(errors) == 0

def test_world_builder_interactive_object_validation(tmp_path):
    world_dir = tmp_path / "world"
    
    import yaml
    def create_yaml(path: Path, data: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', encoding='utf-8') as f:
            yaml.dump(data, f)
            
    create_yaml(world_dir / "world.yaml", {
        "world": {
            "start_region": "REG1",
            "start_screen": "SCR1",
            "start_position": {"x": 5, "y": 5}
        }
    })
    
    create_yaml(world_dir / "objects.yaml", {
        "objects": [
            {
                "id": "KEY", "code": 1,
                "size": {"width": 1, "height": 1},
                "flags": {"blocking": False, "interactive": True},
                "tiles": [1]
            }
        ]
    })
    
    create_yaml(world_dir / "REG1" / "region.yaml", {
        "id": "REG1",
        "name": "Region 1",
        "layout": {"rows": 1, "columns": 2},
        "start_screen": "SCR1",
        "music": "NONE"
    })
    
    create_yaml(world_dir / "REG1" / "screens" / "000.yaml", {
        "id": "SCR1",
        "exits": {"north": None, "south": None, "east": "SCR2", "west": None},
        "objects": [{"object": "KEY", "x": 1, "y": 1}]
    })
    
    create_yaml(world_dir / "REG1" / "screens" / "001.yaml", {
        "id": "SCR2",
        "exits": {"north": None, "south": None, "east": None, "west": "SCR1"},
        "objects": [{"object": "KEY", "x": 2, "y": 2}]
    })
    
    game_world = parse_world_dir(world_dir)
    validator = WorldValidator(game_world)
    
    # Placed on separate screens -> validator should pass without error
    validator.validate()

def test_screen_multiple_interactive_objects_validation():
    pm = ProjectManager()
    
    obj_box = ObjectDefinition(
        id="BOX", code=1, size=ObjectSize(width=2, height=2),
        flags=ObjectFlags(blocking=True, interactive=False), tiles=[1, 2, 3, 4]
    )
    obj_key = ObjectDefinition(
        id="KEY", code=2, size=ObjectSize(width=1, height=1),
        flags=ObjectFlags(blocking=False, interactive=True), tiles=[5]
    )
    obj_chest = ObjectDefinition(
        id="CHEST", code=3, size=ObjectSize(width=2, height=2),
        flags=ObjectFlags(blocking=True, interactive=True), tiles=[6, 7, 8, 9]
    )
    pm.objects = [obj_box, obj_key, obj_chest]
    
    # Screen with 2 interactive objects (KEY and CHEST)
    screen1 = ScreenDef(
        id="SCR1",
        objects=[
            ObjectInstance(object="BOX", x=0, y=0),
            ObjectInstance(object="KEY", x=5, y=5),
            ObjectInstance(object="CHEST", x=10, y=2)
        ]
    )
    pm.screens = {"REG1": {"SCR1": screen1}}
    
    errors = pm.validate_interactive_objects()
    assert len(errors) == 1
    assert "SCR1" in errors[0]
    assert "2 interactive objects" in errors[0]

def test_load_project_screen_interactive_object_limit(tmp_path):
    world_dir = tmp_path / "world"
    import yaml
    def create_yaml(path: Path, data: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', encoding='utf-8') as f:
            yaml.dump(data, f)
            
    create_yaml(world_dir / "world.yaml", {
        "world": {
            "start_region": "REG1",
            "start_screen": "SCR1",
            "start_position": {"x": 5, "y": 5}
        }
    })
    create_yaml(world_dir / "objects.yaml", {
        "objects": [
            {
                "id": "KEY", "code": 1,
                "size": {"width": 1, "height": 1},
                "flags": {"blocking": False, "interactive": True},
                "tiles": [1]
            },
            {
                "id": "CHEST", "code": 2,
                "size": {"width": 1, "height": 1},
                "flags": {"blocking": False, "interactive": True},
                "tiles": [2]
            }
        ]
    })
    create_yaml(world_dir / "enemies.yaml", {"enemies": []})
    create_yaml(world_dir / "items.yaml", {"items": []})
    create_yaml(world_dir / "REG1" / "region.yaml", {
        "id": "REG1",
        "name": "Region 1",
        "layout": {"rows": 1, "columns": 1},
        "start_screen": "SCR1",
        "music": "NONE"
    })
    create_yaml(world_dir / "REG1" / "screens" / "SCR1.yaml", {
        "id": "SCR1",
        "exits": {"north": None, "south": None, "east": None, "west": None},
        "objects": [
            {"object": "KEY", "x": 1, "y": 1},
            {"object": "CHEST", "x": 5, "y": 5}
        ]
    })
    
    pm = ProjectManager()
    loaded = pm.load_project(world_dir)
    assert loaded is False
    assert pm.load_error is not None
    assert "SCR1" in pm.load_error
    assert "2 interactive objects" in pm.load_error

def test_world_builder_screen_interactive_object_limit(tmp_path):
    world_dir = tmp_path / "world"
    import yaml
    def create_yaml(path: Path, data: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', encoding='utf-8') as f:
            yaml.dump(data, f)
            
    create_yaml(world_dir / "world.yaml", {
        "world": {
            "start_region": "REG1",
            "start_screen": "SCR1",
            "start_position": {"x": 5, "y": 5}
        }
    })
    create_yaml(world_dir / "objects.yaml", {
        "objects": [
            {
                "id": "KEY", "code": 1,
                "size": {"width": 1, "height": 1},
                "flags": {"blocking": False, "interactive": True},
                "tiles": [1]
            },
            {
                "id": "CHEST", "code": 2,
                "size": {"width": 1, "height": 1},
                "flags": {"blocking": False, "interactive": True},
                "tiles": [2]
            }
        ]
    })
    create_yaml(world_dir / "REG1" / "region.yaml", {
        "id": "REG1",
        "name": "Region 1",
        "layout": {"rows": 1, "columns": 1},
        "start_screen": "SCR1",
        "music": "NONE"
    })
    create_yaml(world_dir / "REG1" / "screens" / "SCR1.yaml", {
        "id": "SCR1",
        "exits": {"north": None, "south": None, "east": None, "west": None},
        "objects": [
            {"object": "KEY", "x": 1, "y": 1},
            {"object": "CHEST", "x": 5, "y": 5}
        ]
    })
    
    game_world = parse_world_dir(world_dir)
    validator = WorldValidator(game_world)
    with pytest.raises(ValidationError) as exc_info:
        validator.validate()
        
    assert "Screen 'SCR1' in region 'REG1' has 2 interactive objects" in str(exc_info.value)

def test_interactive_object_kwatera_properties():
    inst = ObjectInstance(
        object="INN",
        x=5, y=5,
        type="kwatera",
        conditions_met="Masz klucz",
        conditions_unmet="Brak klucza",
        items_required=[1, 2],
        items_provided=[3],
        game_over=True
    )
    data = inst.model_dump(by_alias=True, exclude_none=True)
    assert data["type"] == "kwatera"
    assert data["conditions_met"] == "Masz klucz"
    assert data["conditions_unmet"] == "Brak klucza"
    assert data["items_required"] == [1, 2]
    assert data["items_provided"] == [3]
    assert data["game_over"] is True
    assert "cost_of_travel" not in data

def test_interactive_object_portal_properties():
    inst = ObjectInstance(
        object="TELEPORT",
        x=10, y=8,
        type="portal",
        message_travel="Podróżujesz do sąsiedniego krainy",
        cost_of_travel=50
    )
    data = inst.model_dump(by_alias=True, exclude_none=True)
    assert data["type"] == "portal"
    assert data["message_travel"] == "Podróżujesz do sąsiedniego krainy"
    assert data["cost_of_travel"] == 50
    assert "conditions_met" not in data
    assert "conditions_unmet" not in data
    assert "items_provided" not in data
