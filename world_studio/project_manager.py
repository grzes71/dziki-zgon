import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from world_studio.models import WorldConfig, ObjectDefinition, RegionDef, ScreenDef, EnemyDef

class ProjectManager:
    def __init__(self):
        self.world_dir: Optional[Path] = None
        self.world_config: Optional[WorldConfig] = None
        self.colors: Dict[str, tuple] = {} # Deprecated global colors
        self.region_colors: Dict[str, Dict[str, tuple]] = {}
        self.region_atari_colors: Dict[str, Dict[str, int]] = {}
        self.objects: List[ObjectDefinition] = []
        self.enemy_defs: List[EnemyDef] = []
        self.enemy_colors: List[str] = []
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
            
        # colors.yaml (global fallback if it exists, though deprecated)
        c_data = self._load_yaml(world_dir / "colors.yaml")
        self.colors.clear()
        for k, v in c_data.items():
            if isinstance(v, dict) and "rgb" in v:
                self.colors[k] = tuple(v["rgb"])
            elif isinstance(v, list) and len(v) == 3:
                self.colors[k] = tuple(v)
                
        # objects.yaml
        o_data = self._load_yaml(world_dir / "objects.yaml")
        self.objects = [ObjectDefinition.model_validate(obj) for obj in o_data.get("objects", [])]
        
        # enemies.yaml
        e_data = self._load_yaml(world_dir / "enemies.yaml")
        self.enemy_defs = [EnemyDef.model_validate(e) for e in e_data.get("enemies", [])]
        self.enemy_colors = list(e_data.get("colors", {}).keys())
        
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
                    
                    # Load region colors from region.yaml
                    r_colors_data = r_data.get("colors", {})
                    r_colors = {}
                    r_atari = {}
                    for k, v in r_colors_data.items():
                        if isinstance(v, dict):
                            if "rgb" in v:
                                r_colors[k] = tuple(v["rgb"])
                            if "atari" in v:
                                r_atari[k] = v["atari"]
                        elif isinstance(v, list) and len(v) == 3:
                            r_colors[k] = tuple(v)
                    self.region_colors[item.name] = r_colors
                    self.region_atari_colors[item.name] = r_atari
                    
                    screens_dir = item / "screens"
                    if screens_dir.exists():
                        for screen_file in screens_dir.glob("*.yaml"):
                            s_data = self._load_yaml(screen_file)
                            screen_def = ScreenDef.model_validate(s_data)
                            self.screens[item.name][screen_def.id] = screen_def
                except Exception as e:
                    print(f"Error loading region {item.name}: {e}")
            
            # Zapewnienie, że wszystkie wczytane regiony mają grid_x i grid_y
            for rid in self.regions.keys():
                self._ensure_grid_coordinates(rid)
                    
        return True

    def save_project(self) -> bool:
        if not self.world_dir or not self.world_config:
            return False
            
        # save world.yaml
        self._save_yaml(self.world_dir / "world.yaml", {"world": self.world_config.model_dump()})
        # objects.yaml is loaded in read-only mode, so we don't save it.
        
        for region_id, region_def in self.regions.items():
            r_dir = self.world_dir / region_id
            
            r_dump = region_def.model_dump()
            
            # Save region colors into region.yaml
            if region_id in self.region_colors and self.region_colors[region_id]:
                import sys
                from pathlib import Path
                scripts_path = str(Path(__file__).parent.parent / "scripts")
                if scripts_path not in sys.path:
                    sys.path.append(scripts_path)
                try:
                    from img2asm import rgb_to_atari
                except ImportError:
                    rgb_to_atari = lambda r, g, b: 0
                
                c_data = {}
                for k, v in self.region_colors[region_id].items():
                    r, g, b = v
                    if region_id in self.region_atari_colors and k in self.region_atari_colors[region_id]:
                        atari_val = self.region_atari_colors[region_id][k]
                    else:
                        atari_val = rgb_to_atari(r, g, b)
                    c_data[k] = {"rgb": list(v), "atari": atari_val}
                r_dump["colors"] = c_data
                
            self._save_yaml(r_dir / "region.yaml", r_dump)
                
            screens_dict = self.screens.get(region_id, {})
            for screen_id, screen_def in screens_dict.items():
                s_path = r_dir / "screens" / f"{screen_id}.yaml"
                
                # Optimize objects list (merge adjacent tiles using repeat-x and repeat-y)
                screen_def.objects = self.optimize_screen_objects(screen_def.objects)
                
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

    def optimize_screen_objects(self, objects: List[Any]) -> List[Any]:
        from world_studio.models import ObjectInstance
        
        obj_dict = {o.id: o for o in self.objects}
        
        # Make a working copy of ObjectInstance objects
        current_list = [
            ObjectInstance(
                object=o.object,
                x=o.x,
                y=o.y,
                repeat_x=o.repeat_x if getattr(o, 'repeat_x', 1) is not None else 1,
                repeat_y=o.repeat_y if getattr(o, 'repeat_y', 1) is not None else 1
            )
            for o in objects
        ]
        
        changed = True
        while changed:
            changed = False
            
            # Try to find a horizontal merge
            for i in range(len(current_list)):
                inst1 = current_list[i]
                odef = obj_dict.get(inst1.object)
                if not odef:
                    continue
                w = odef.size.width
                
                for j in range(len(current_list)):
                    if i == j:
                        continue
                    inst2 = current_list[j]
                    if inst1.object != inst2.object:
                        continue
                    if inst1.y != inst2.y or inst1.repeat_y != inst2.repeat_y:
                        continue
                    
                    # Check if inst2 is immediately to the right of inst1
                    if inst1.x + w * inst1.repeat_x == inst2.x:
                        inst1.repeat_x += inst2.repeat_x
                        current_list.pop(j)
                        changed = True
                        break
                if changed:
                    break
                    
            if changed:
                continue
                
            # Try to find a vertical merge
            for i in range(len(current_list)):
                inst1 = current_list[i]
                odef = obj_dict.get(inst1.object)
                if not odef:
                    continue
                h = odef.size.height
                
                for j in range(len(current_list)):
                    if i == j:
                        continue
                    inst2 = current_list[j]
                    if inst1.object != inst2.object:
                        continue
                    if inst1.x != inst2.x or inst1.repeat_x != inst2.repeat_x:
                        continue
                    
                    # Check if inst2 is immediately below inst1
                    if inst1.y + h * inst1.repeat_y == inst2.y:
                        inst1.repeat_y += inst2.repeat_y
                        current_list.pop(j)
                        changed = True
                        break
                if changed:
                    break
                    
        return current_list

    def add_region(self, region_id: str, name: str, rows: int, columns: int, damage: int = 10) -> bool:
        if region_id in self.regions:
            return False
            
        region_def = RegionDef(
            id=region_id,
            name=name,
            damage=damage,
            layout={"rows": rows, "columns": columns},
            start_screen="START",
            music=region_id
        )
        self.regions[region_id] = region_def
        self.screens[region_id] = {}
        return True

    def _ensure_grid_coordinates(self, region_id: str):
        region = self.regions.get(region_id)
        screens = self.screens.get(region_id, {})
        if not region or not screens:
            return
            
        missing = [s for s in screens.values() if s.grid_x is None or s.grid_y is None]
        if not missing:
            return
            
        start_id = region.start_screen
        if start_id not in screens:
            start_id = list(screens.keys())[0]
            
        positions = {start_id: (0, 0)}
        queue = [start_id]
        
        while queue:
            curr_id = queue.pop(0)
            cx, cy = positions[curr_id]
            s_def = screens.get(curr_id)
            if not s_def:
                continue
                
            directions = [
                (s_def.exits.north, cx, cy - 1),
                (s_def.exits.south, cx, cy + 1),
                (s_def.exits.west, cx - 1, cy),
                (s_def.exits.east, cx + 1, cy)
            ]
            
            for next_id, nx, ny in directions:
                if next_id and next_id in screens and next_id not in positions:
                    positions[next_id] = (nx, ny)
                    queue.append(next_id)
                    
        if positions:
            min_x = min(x for x, y in positions.values())
            min_y = min(y for x, y in positions.values())
            for sid, (x, y) in positions.items():
                s = screens[sid]
                s.grid_x = x - min_x
                s.grid_y = y - min_y
                
        for s in missing:
            if s.grid_x is None:
                s.grid_x = 0
                s.grid_y = 0
                
    def update_all_exits(self, region_id: str, old_id: str = None, new_id: str = None):
        screens = self.screens.get(region_id, {})
        for sid, sdef in screens.items():
            if old_id:
                if sdef.exits.north == old_id: sdef.exits.north = new_id
                if sdef.exits.south == old_id: sdef.exits.south = new_id
                if sdef.exits.west == old_id: sdef.exits.west = new_id
                if sdef.exits.east == old_id: sdef.exits.east = new_id

    def add_screen(self, region_id: str, screen_id: str, grid_x: int, grid_y: int) -> bool:
        if region_id not in self.regions:
            return False
            
        if screen_id in self.screens[region_id]:
            return False
            
        screen_def = ScreenDef(
            id=screen_id,
            grid_x=grid_x,
            grid_y=grid_y,
            exits={},
            objects=[]
        )
        self.screens[region_id][screen_id] = screen_def
        self.update_all_exits(region_id)
        return True

    def remove_screen(self, region_id: str, screen_id: str) -> bool:
        if region_id not in self.regions or screen_id not in self.screens[region_id]:
            return False
        del self.screens[region_id][screen_id]
        self.update_all_exits(region_id, old_id=screen_id, new_id=None)
        return True
