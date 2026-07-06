import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from world_studio.models import WorldConfig, ObjectDefinition, RegionDef, ScreenDef

class ProjectManager:
    def __init__(self):
        self.world_dir: Optional[Path] = None
        self.world_config: Optional[WorldConfig] = None
        self.colors: Dict[str, tuple] = {}
        self.objects: List[ObjectDefinition] = []
        self.regions: Dict[str, RegionDef] = {}
        self.screens: Dict[str, Dict[str, ScreenDef]] = {}
        
    def _load_yaml(self, path: Path) -> dict:
        if not path.exists():
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def _save_yaml(self, path: Path, data: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def load_project(self, world_dir: Path) -> bool:
        if not (world_dir / "world.yaml").exists():
            return False
            
        self.world_dir = world_dir
        
        # world.yaml
        w_data = self._load_yaml(world_dir / "world.yaml")
        if "world" in w_data:
            self.world_config = WorldConfig.model_validate(w_data["world"])
            
        # colors.yaml
        c_data = self._load_yaml(world_dir / "colors.yaml")
        self.colors.clear()
        for k, v in c_data.items():
            if isinstance(v, list) and len(v) == 3:
                self.colors[k] = tuple(v)
                
        # objects.yaml
        o_data = self._load_yaml(world_dir / "objects.yaml")
        self.objects = [ObjectDefinition.model_validate(obj) for obj in o_data.get("objects", [])]
        
        # regions
        self.regions.clear()
        self.screens.clear()
        
        for item in world_dir.iterdir():
            if item.is_dir() and (item / "region.yaml").exists():
                r_data = self._load_yaml(item / "region.yaml")
                try:
                    region_def = RegionDef.model_validate(r_data)
                    self.regions[item.name] = region_def
                    self.screens[item.name] = {}
                    
                    screens_dir = item / "screens"
                    if screens_dir.exists():
                        for screen_file in screens_dir.glob("*.yaml"):
                            s_data = self._load_yaml(screen_file)
                            screen_def = ScreenDef.model_validate(s_data)
                            self.screens[item.name][screen_def.id] = screen_def
                except Exception as e:
                    print(f"Error loading region {item.name}: {e}")
                    
        return True

    def save_project(self) -> bool:
        if not self.world_dir or not self.world_config:
            return False
            
        # save world.yaml
        self._save_yaml(self.world_dir / "world.yaml", {"world": self.world_config.model_dump()})
        
        # colors.yaml
        if self.colors:
            colors_list = {k: list(v) for k, v in self.colors.items()}
            self._save_yaml(self.world_dir / "colors.yaml", colors_list)
            
        # objects.yaml is loaded in read-only mode, so we don't save it.
        
        for region_id, region_def in self.regions.items():
            r_dir = self.world_dir / region_id
            self._save_yaml(r_dir / "region.yaml", region_def.model_dump())
            
            screens_dict = self.screens.get(region_id, {})
            for screen_id, screen_def in screens_dict.items():
                s_path = r_dir / "screens" / f"{screen_id}.yaml"
                s_data = screen_def.model_dump(by_alias=True)
                
                # Manual cleanup to match World Builder expectations
                for obj in s_data.get("objects", []):
                    if obj.get("repeat-x") == 1:
                        del obj["repeat-x"]
                    if obj.get("repeat-y") == 1:
                        del obj["repeat-y"]
                
                # Make flow style for lists
                # yaml.dump doesn't easily let us mix flow and block without custom representers
                # We will just write it.
                self._save_yaml(s_path, s_data)
                
        return True
