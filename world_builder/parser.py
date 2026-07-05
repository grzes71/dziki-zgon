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
            
            screens = []
            screens_dir = item / "screens"
            if screens_dir.exists() and screens_dir.is_dir():
                for screen_file in screens_dir.glob("*.yaml"):
                    screen_data = load_yaml(screen_file)
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
