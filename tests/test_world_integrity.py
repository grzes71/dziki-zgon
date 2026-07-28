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


def test_world_sprites_integrity():
    # Find root directory relative to this test file
    root_dir = Path(__file__).parent.parent
    world_dir = root_dir / "world"
    sprites_dir = root_dir / "sprites"
    
    enemies_file = world_dir / "enemies.yaml"
    assert enemies_file.exists(), f"enemies.yaml not found at {enemies_file}"
    assert sprites_dir.exists(), f"sprites directory not found at {sprites_dir}"
    
    # Load enemies.yaml
    with open(enemies_file, 'r', encoding='utf-8') as f:
        enemies_data = yaml.safe_load(f) or {}
    
    enemies_list = enemies_data.get("enemies", [])
    defined_enemy_ids = {e.get("id") for e in enemies_list if isinstance(e, dict) and e.get("id")}
    
    # Scan for screen YAML files: world/*/screens/*.yaml
    screen_files = list(world_dir.glob("*/screens/*.yaml"))
    assert len(screen_files) > 0, "No screen files found under world/*/screens/"
    
    errors = []
    for screen_file in screen_files:
        with open(screen_file, 'r', encoding='utf-8') as f:
            screen_data = yaml.safe_load(f) or {}
        
        screen_id = screen_data.get("id", screen_file.stem)
        screen_enemies = screen_data.get("enemies", [])
        if not isinstance(screen_enemies, list):
            continue
            
        for enemy_inst in screen_enemies:
            if not isinstance(enemy_inst, dict):
                continue
            enemy_name = enemy_inst.get("enemy")
            if not enemy_name:
                continue
                
            relative_path = screen_file.relative_to(root_dir)
            if enemy_name not in defined_enemy_ids:
                errors.append(
                    f"Screen '{screen_id}' in file '{relative_path}' uses undefined enemy: '{enemy_name}' (not in enemies.yaml)"
                )
                
            sprite_file = sprites_dir / f"{enemy_name}.sprite.json"
            alt_sprite_file = sprites_dir / f"{enemy_name}.json"
            if not (sprite_file.exists() or alt_sprite_file.exists()):
                errors.append(
                    f"Screen '{screen_id}' in file '{relative_path}' uses enemy '{enemy_name}', but sprite definition was not found in 'sprites/' ({sprite_file.name})"
                )
                
    assert not errors, "World sprite integrity check failed! Issues with enemies in screens:\n" + "\n".join(errors)


def test_world_portal_entries_integrity():
    root_dir = Path(__file__).parent.parent
    world_dir = root_dir / "world"
    
    # Load all regions and their portal_entries
    region_files = list(world_dir.glob("*/region.yaml"))
    assert len(region_files) > 0, "No region files found under world/*/region.yaml"
    
    regions_portal_entries = {}
    for r_file in region_files:
        with open(r_file, 'r', encoding='utf-8') as f:
            r_data = yaml.safe_load(f) or {}
        r_id = r_data.get("id")
        if r_id:
            p_entries = r_data.get("portal_entries", {}) or {}
            regions_portal_entries[r_id] = p_entries

    screen_files = list(world_dir.glob("*/screens/*.yaml"))
    errors = []
    for screen_file in screen_files:
        with open(screen_file, 'r', encoding='utf-8') as f:
            screen_data = yaml.safe_load(f) or {}
        
        screen_id = screen_data.get("id", screen_file.stem)
        source_region = screen_file.parent.parent.name
        screen_objects = screen_data.get("objects", [])
        if not isinstance(screen_objects, list):
            continue
            
        for obj_inst in screen_objects:
            if not isinstance(obj_inst, dict):
                continue
            if obj_inst.get("type") == "portal":
                target_region = obj_inst.get("target_region")
                relative_path = screen_file.relative_to(root_dir)
                if not target_region:
                    errors.append(f"Screen '{screen_id}' in '{relative_path}' has a portal object without 'target_region'")
                    continue
                if target_region not in regions_portal_entries:
                    errors.append(f"Screen '{screen_id}' in '{relative_path}' has portal object targeting unknown region '{target_region}'")
                    continue
                
                target_entries = regions_portal_entries[target_region]
                if source_region not in target_entries:
                    errors.append(
                        f"Screen '{screen_id}' in '{relative_path}' has portal targeting region '{target_region}', but '{target_region}' has no PORTAL ENTRY defined for '{source_region}'"
                    )

    assert not errors, "World portal integrity check failed! Issues with portals in screens:\n" + "\n".join(errors)


