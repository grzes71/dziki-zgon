import yaml
from pathlib import Path
from typing import Dict, Any
from .model import GameWorld

def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}

def parse_world_dir(base_dir: Path) -> GameWorld:
    base_dir = Path(base_dir)
    world_path = base_dir / "world.yaml"
    objects_path = base_dir / "objects.yaml"
    
    if not world_path.exists():
        raise FileNotFoundError(f"Missing {world_path}")
    if not objects_path.exists():
        raise FileNotFoundError(f"Missing {objects_path}")
        
    world_data = load_yaml(world_path)
    objects_data = load_yaml(objects_path)
    
    regions = []
    
    for item in base_dir.iterdir():
        if item.is_dir():
            region_yaml = item / "region.yaml"
            if not region_yaml.exists():
                continue
                
            region_data = load_yaml(region_yaml)
            
            # Load region colors
            c_data = region_data.get("colors", {})
            region_palette = {
                "PCOLR0": 0x0E, "PCOLR1": 0x0E, "PCOLR2": 0x0E, "PCOLR3": 0x0E,
                "PF0": 0x00, "PF1": 0x00, "PF2": 0x00, "PF3_INV": 0x00, "BACKGROUND": 0x00
            }
            if c_data:
                for k, v in c_data.items():
                    if k in region_palette and isinstance(v, dict) and "atari" in v:
                        region_palette[k] = v["atari"]
            region_data["palette"] = region_palette
            
            objects_dict = {obj.get("id"): obj for obj in objects_data.get("objects", [])}
            
            screens = []
            screens_dir = item / "screens"
            if screens_dir.exists() and screens_dir.is_dir():
                for screen_file in screens_dir.glob("*.yaml"):
                    screen_data = load_yaml(screen_file)
                    
                    expanded_objects = []
                    for obj_inst in screen_data.get("objects", []):
                        obj_id = obj_inst.get("object")
                        repeat_x = obj_inst.get("repeat-x", 1)
                        repeat_y = obj_inst.get("repeat-y", 1)
                        
                        if repeat_x > 1 or repeat_y > 1:
                            w = 1
                            h = 1
                            if obj_id in objects_dict:
                                size = objects_dict[obj_id].get("size", {})
                                w = size.get("width", 1)
                                h = size.get("height", 1)
                                
                            base_x = obj_inst.get("x", 0)
                            base_y = obj_inst.get("y", 0)
                            
                            for ry in range(repeat_y):
                                for rx in range(repeat_x):
                                    new_inst = dict(obj_inst)
                                    new_inst.pop("repeat-x", None)
                                    new_inst.pop("repeat-y", None)
                                    new_x = base_x + rx * w
                                    new_y = base_y + ry * h
                                    if new_x <= 39 and new_y <= 11:
                                        new_inst["x"] = new_x
                                        new_inst["y"] = new_y
                                        expanded_objects.append(new_inst)
                        else:
                            # Also remove repeat flags if they are 1
                            new_inst = dict(obj_inst)
                            new_inst.pop("repeat-x", None)
                            new_inst.pop("repeat-y", None)
                            expanded_objects.append(new_inst)
                            
                    screen_data["objects"] = expanded_objects
                    screens.append(screen_data)
                    
            region_data['screens'] = screens
            
            # Keep directory name for validation
            region_data['_dir_name'] = item.name
            
            regions.append(region_data)
            
    raw_data = {
        "world": world_data.get("world", {}),
        "objects": objects_data.get("objects", []),
        "regions": regions
    }
    
    # Pydantic handles the deep validation of schema
    return GameWorld.model_validate(raw_data)
