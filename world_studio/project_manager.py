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

    def add_region(self, region_id: str, name: str, rows: int, columns: int) -> bool:
        if region_id in self.regions:
            return False
            
        region_def = RegionDef(
            id=region_id,
            name=name,
            layout={"rows": rows, "columns": columns},
            start_screen="START",
            music=region_id
        )
        self.regions[region_id] = region_def
        self.screens[region_id] = {}
        return True

    def add_screen(self, region_id: str, screen_id: str, exits: dict = None) -> bool:
        if region_id not in self.regions:
            return False
            
        if screen_id in self.screens[region_id]:
            return False
            
        if exits is None:
            exits = {}
            
        screen_def = ScreenDef(
            id=screen_id,
            exits={},
            objects=[]
        )
        self.screens[region_id][screen_id] = screen_def
        
        self.update_screen_exits(region_id, screen_id, exits)
        return True

    def validate_screen_exits(self, region_id: str, screen_id: str, exits: dict) -> tuple[bool, str]:
        if region_id not in self.regions:
            return False, "Region not found."
            
        opposites = {
            "north": "south",
            "south": "north",
            "east": "west",
            "west": "east"
        }
        
        for d, target_screen_id in exits.items():
            if not target_screen_id or target_screen_id == "None":
                continue
            if target_screen_id == screen_id:
                return False, f"Screen cannot link to itself ({d})."
            
            target_screen = self.screens[region_id].get(target_screen_id)
            if target_screen:
                opp = opposites[d]
                existing_link = getattr(target_screen.exits, opp)
                if existing_link and existing_link != screen_id:
                    return False, f"Cannot set {d} exit to {target_screen_id}. It already has a {opp} exit pointing to {existing_link}."
                    
        # Check layout constraints
        region_def = self.regions.get(region_id)
        if region_def:
            graph = {}
            for sid, sdef in self.screens[region_id].items():
                if sid != screen_id:
                    graph[sid] = {
                        "north": sdef.exits.north,
                        "south": sdef.exits.south,
                        "east": sdef.exits.east,
                        "west": sdef.exits.west
                    }
            
            graph[screen_id] = {
                "north": exits.get("north"),
                "south": exits.get("south"),
                "east": exits.get("east"),
                "west": exits.get("west")
            }
            
            for d, target in exits.items():
                if target and target != "None" and target in graph:
                    opp = opposites[d]
                    graph[target][opp] = screen_id
                    
            positions = {screen_id: (0, 0)}
            queue = [screen_id]
            
            while queue:
                curr = queue.pop(0)
                cx, cy = positions[curr]
                
                curr_exits = graph.get(curr, {})
                directions = [
                    (curr_exits.get("north"), cx, cy - 1),
                    (curr_exits.get("south"), cx, cy + 1),
                    (curr_exits.get("west"), cx - 1, cy),
                    (curr_exits.get("east"), cx + 1, cy)
                ]
                
                for nxt, nx, ny in directions:
                    if nxt and nxt != "None" and nxt in graph:
                        if nxt not in positions:
                            positions[nxt] = (nx, ny)
                            queue.append(nxt)
                            
            if positions:
                min_x = min(x for x, y in positions.values())
                max_x = max(x for x, y in positions.values())
                min_y = min(y for x, y in positions.values())
                max_y = max(y for x, y in positions.values())
                
                width = max_x - min_x + 1
                height = max_y - min_y + 1
                
                if width > region_def.layout.columns:
                    return False, f"Layout width exceeded. Connected width is {width}, max is {region_def.layout.columns}."
                if height > region_def.layout.rows:
                    return False, f"Layout height exceeded. Connected height is {height}, max is {region_def.layout.rows}."
                    
        return True, ""

    def update_screen_exits(self, region_id: str, screen_id: str, exits: dict) -> bool:
        if region_id not in self.regions or screen_id not in self.screens[region_id]:
            return False
            
        screen_def = self.screens[region_id][screen_id]
        screen_def.exits.north = exits.get("north")
        screen_def.exits.south = exits.get("south")
        screen_def.exits.east = exits.get("east")
        screen_def.exits.west = exits.get("west")
        
        # Automatyczne ustawienie obustronnych przejść
        opposites = {
            "north": "south",
            "south": "north",
            "east": "west",
            "west": "east"
        }
        
        for d, opp in opposites.items():
            linked_screen = exits.get(d)
            if linked_screen and linked_screen in self.screens[region_id]:
                setattr(self.screens[region_id][linked_screen].exits, opp, screen_id)
                
        return True
