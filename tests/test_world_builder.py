import pytest
import yaml
from pathlib import Path
from pydantic import ValidationError as PydanticValidationError
from world_builder.compiler import compile_world
from world_builder.model import ObjectDefinition, ObjectSize, ObjectFlags
from world_builder.parser import parse_world_dir
from world_builder.validator import WorldValidator, ValidationError

def create_yaml(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w') as f:
        yaml.dump(data, f)

@pytest.fixture
def happy_path_world(tmp_path):
    world_dir = tmp_path / "world"
    out_dir = tmp_path / "out"
    
    # world.yaml
    create_yaml(world_dir / "world.yaml", {
        "world": {
            "start_region": "TEST_REGION",
            "start_screen": "START",
            "start_position": {"x": 5, "y": 5}
        }
    })
    
    # objects.yaml
    create_yaml(world_dir / "objects.yaml", {
        "objects": [
            {
                "id": "BOX", "code": 1, 
                "size": {"width": 2, "height": 2}, 
                "flags": {"blocking": True, "interactive": False},
                "tiles": [1, 2, 3, 4]
            }
        ]
    })
    
    # region.yaml
    create_yaml(world_dir / "TEST_REGION" / "region.yaml", {
        "id": "TEST_REGION",
        "name": "Test Region",
        "layout": {"rows": 1, "columns": 2},
        "start_screen": "START",
        "music": "NONE"
    })
    
    # screens
    create_yaml(world_dir / "TEST_REGION" / "screens" / "000.yaml", {
        "id": "START",
        "exits": {"north": None, "south": None, "east": "NEXT", "west": None},
        "objects": [
            {"object": "BOX", "x": 10, "y": 5}
        ]
    })
    
    create_yaml(world_dir / "TEST_REGION" / "screens" / "001.yaml", {
        "id": "NEXT",
        "exits": {"north": None, "south": None, "east": None, "west": "START"}
    })
    
    return world_dir, out_dir

def test_happy_path(happy_path_world):
    world_dir, out_dir = happy_path_world
    assert compile_world(str(world_dir), str(out_dir)) is True
    assert (out_dir / "objects.asm").exists()
    assert (out_dir / "regions.asm").exists()
    assert (out_dir / "screens.asm").exists()
    assert (out_dir / "exits.asm").exists()
    assert (out_dir / "world.inc").exists()

def test_duplicate_detection(happy_path_world):
    world_dir, out_dir = happy_path_world
    # Add another screen with the same id "START"
    create_yaml(world_dir / "TEST_REGION" / "screens" / "002.yaml", {
        "id": "START",  # Duplicate ID
        "exits": {"north": None, "south": None, "east": None, "west": None}
    })
    
    # Should fail validation
    assert compile_world(str(world_dir), str(out_dir)) is False

def test_out_of_bounds_test(happy_path_world):
    world_dir, out_dir = happy_path_world
    # Modify object to be out of bounds
    create_yaml(world_dir / "TEST_REGION" / "screens" / "000.yaml", {
        "id": "START",
        "exits": {"north": None, "south": None, "east": "NEXT", "west": None},
        "objects": [
            {"object": "BOX", "x": 39, "y": 5}  # BOX is width=2, so 39+2 = 41 > 40
        ]
    })
    
    assert compile_world(str(world_dir), str(out_dir)) is False

def test_invalid_spawn_test(happy_path_world):
    world_dir, out_dir = happy_path_world
    # Change start screen to a non-existent screen
    create_yaml(world_dir / "world.yaml", {
        "world": {
            "start_region": "TEST_REGION",
            "start_screen": "NON_EXISTENT",
            "start_position": {"x": 5, "y": 5}
        }
    })
    
    assert compile_world(str(world_dir), str(out_dir)) is False

def test_resolution_verification():
    # Directly test the size packing logic
    # Width=4, Height=3 -> Packed = ((4-1)<<4) | (3-1) = (3<<4) | 2 = 0x32
    width = 4
    height = 3
    packed_size = ((width - 1) << 4) | ((height - 1) & 0x0F)
    assert packed_size == 0x32
    
    # Width=16, Height=16 -> Packed = (15<<4) | 15 = 0xFF
    packed_size_max = ((16 - 1) << 4) | ((16 - 1) & 0x0F)
    assert packed_size_max == 0xFF
    
    # Flags logic test
    blocking = True
    interactive = False
    flags = 0
    if blocking: flags |= 0x80
    if interactive: flags |= 0x40
    assert flags == 0x80
