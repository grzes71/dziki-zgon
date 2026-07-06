from pathlib import Path
from .model import GameWorld

class AsmGenerator:
    def __init__(self, world: GameWorld, out_dir: Path):
        self.world = world
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        
        # Sort indices
        self.regions_sorted = sorted(self.world.regions, key=lambda r: r.id)
        self.region_idx = {r.id: i for i, r in enumerate(self.regions_sorted)}
        
        # Extract and sort screens
        self.screens_sorted = []
        for r in self.regions_sorted:
            for s in r.screens:
                self.screens_sorted.append(s)
        self.screens_sorted.sort(key=lambda s: s.id)
        self.screen_idx = {s.id: i for i, s in enumerate(self.screens_sorted)}
        
    def generate(self):
        self._generate_objects()
        self._generate_regions()
        self._generate_exits()
        self._generate_screens()
        self._generate_world_inc()
        
    def _generate_objects(self):
        if not self.world.objects:
            max_code = 0
        else:
            max_code = max(obj.code for obj in self.world.objects)
            
        objects_by_code = {obj.code: obj for obj in self.world.objects}
        
        out = ["; Global Object Arrays (Index = Object Code)"]
        out.append(f"MAX_OBJECT_CODE = {max_code}")
        
        out.append("\n; PackedSize (W/H)")
        out.append("OBJ_SIZE")
        for code in range(max_code + 1):
            if code in objects_by_code:
                obj = objects_by_code[code]
                packed_size = ((obj.size.width - 1) << 4) | ((obj.size.height - 1) & 0x0F)
                out.append(f"    dta ${packed_size:02X} ; Code {code} ({obj.id})")
            else:
                out.append(f"    dta $00 ; Code {code} (Empty/Reserved)")
                
        out.append("\n; PackedFlags (Bit 7: blocking, Bit 6: interactive)")
        out.append("OBJ_FLAGS")
        for code in range(max_code + 1):
            if code in objects_by_code:
                obj = objects_by_code[code]
                flags = 0
                if obj.flags.blocking: flags |= 0x80
                if obj.flags.interactive: flags |= 0x40
                out.append(f"    dta ${flags:02X} ; Code {code} ({obj.id})")
            else:
                out.append(f"    dta $00 ; Code {code} (Empty/Reserved)")
                
        out.append("\n; Pointers to Object Tiles (Indexed by Object Code)")
        out.append("OBJ_TILES_LO")
        for code in range(max_code + 1):
            if code in objects_by_code:
                out.append(f"    dta <OBJ_TILES_{code}")
            else:
                out.append(f"    dta $00")
                
        out.append("OBJ_TILES_HI")
        for code in range(max_code + 1):
            if code in objects_by_code:
                out.append(f"    dta >OBJ_TILES_{code}")
            else:
                out.append(f"    dta $00")
                
        out.append("\n; Object Tile Data")
        for code in range(max_code + 1):
            if code in objects_by_code:
                obj = objects_by_code[code]
                tiles_hex = ", ".join(f"${t:02X}" for t in obj.tiles)
                out.append(f"OBJ_TILES_{code}")
                out.append(f"    dta {tiles_hex} ; {obj.id}")
                
        with open(self.out_dir / "objects.asm", "w", encoding="utf-8") as f:
            f.write("\n".join(out) + "\n")
            
    def _generate_regions(self):
        out = ["; Global Regions Table"]
        out.append(f"REGION_COUNT = {len(self.regions_sorted)}")
        
        out.append("\n; Pointers Table (Indexed by RegionId)")
        out.append("REGION_POINTERS_LO")
        for r in self.regions_sorted:
            out.append(f"    dta <REGION_{r.id}")
        out.append("REGION_POINTERS_HI")
        for r in self.regions_sorted:
            out.append(f"    dta >REGION_{r.id}")
            
        out.append("\n; Region Data Structures")
        for r in self.regions_sorted:
            out.append(f"REGION_{r.id}")
            out.append(f"    dta {r.layout.rows}, {r.layout.columns} ; Rows, Columns")
            start_idx = self.screen_idx[r.start_screen]
            out.append(f"    dta {start_idx} ; Start ScreenId ({r.start_screen})")
            
        with open(self.out_dir / "regions.asm", "w", encoding="utf-8") as f:
            f.write("\n".join(out) + "\n")

    def _generate_exits(self):
        out = ["; Global Exits Table (4 bytes per ScreenId: N, S, W, E)"]
        out.append("EXITS_TABLE")
        
        for s in self.screens_sorted:
            exits = []
            for dir_key in ['north', 'south', 'west', 'east']:
                target = getattr(s.exits, dir_key)
                if target is None:
                    exits.append("$FF")
                else:
                    target_idx = self.screen_idx[target]
                    exits.append(f"${target_idx:02X}")
            out.append(f"    dta {', '.join(exits)} ; ScreenId {self.screen_idx[s.id]} ({s.id})")
            
        with open(self.out_dir / "exits.asm", "w", encoding="utf-8") as f:
            f.write("\n".join(out) + "\n")
            
    def _generate_screens(self):
        out = ["; Screen Pointers Table (Indexed by ScreenId)"]
        out.append("SCREEN_POINTERS_LO")
        for s in self.screens_sorted:
            out.append(f"    dta <SCREEN_{s.id}")
        out.append("SCREEN_POINTERS_HI")
        for s in self.screens_sorted:
            out.append(f"    dta >SCREEN_{s.id}")
            
        out.append("\n; Screen Layout Configurations")
        objects_by_id = {obj.id: obj for obj in self.world.objects}
        
        for s in self.screens_sorted:
            out.append(f"SCREEN_{s.id}")
            out.append(f"    dta {len(s.objects)} ; Object count")
            for inst in s.objects:
                obj_def = objects_by_id[inst.object]
                out.append(f"    dta {obj_def.code}, {inst.x}, {inst.y} ; {inst.object}")
                
        with open(self.out_dir / "screens.asm", "w", encoding="utf-8") as f:
            f.write("\n".join(out) + "\n")
            
    def _generate_world_inc(self):
        out = ["; World Builder Master Include File"]
        out.append(f"SCREEN_COUNT = {len(self.screens_sorted)}")
        
        out.append("\n; Global Screen Translation Constants")
        for s in self.screens_sorted:
            out.append(f"SCREEN_ID_{s.id} = {self.screen_idx[s.id]}")
        
        with open(self.out_dir / "world.inc", "w", encoding="utf-8") as f:
            f.write("\n".join(out) + "\n")
