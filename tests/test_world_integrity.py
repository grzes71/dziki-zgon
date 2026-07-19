import yaml
from pathlib import Path

def test_world_objects_integrity():
    # Find the world directory relative to this test file
    root_dir = Path(__file__).parent.parent
    world_dir = root_dir / "world"
    
    objects_file = world_dir / "objects.yaml"
    assert objects_file.exists(), f"objects.yaml not found at {objects_file}"
    
    # Load objects.yaml
    with open(objects_file, 'r', encoding='utf-8') as f:
        objects_data = yaml.safe_load(f) or {}
    
    # Extract defined object IDs from objects.yaml
    objects_list = objects_data.get("objects", [])
    defined_object_ids = {obj.get("id") for obj in objects_list if obj.get("id")}
    
    # Scan for screen YAML files: world/*/screens/*.yaml
    screen_files = list(world_dir.glob("*/screens/*.yaml"))
    assert len(screen_files) > 0, "No screen files found under world/*/screens/"
    
    errors = []
    for screen_file in screen_files:
        with open(screen_file, 'r', encoding='utf-8') as f:
            screen_data = yaml.safe_load(f) or {}
        
        screen_id = screen_data.get("id", screen_file.stem)
        screen_objects = screen_data.get("objects", [])
        if not isinstance(screen_objects, list):
            continue
            
        for obj_inst in screen_objects:
            if not isinstance(obj_inst, dict):
                continue
            obj_name = obj_inst.get("object")
            if not obj_name:
                continue
                
            if obj_name not in defined_object_ids:
                relative_path = screen_file.relative_to(root_dir)
                errors.append(
                    f"Screen '{screen_id}' in file '{relative_path}' uses undefined object: '{obj_name}'"
                )
                
    assert not errors, "World integrity check failed! Undefined objects used in screens:\n" + "\n".join(errors)
