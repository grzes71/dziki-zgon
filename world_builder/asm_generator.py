from pathlib import Path
from .model import GameWorld

POLISH_CHARS = {
    'ą': 0x7B, 'Ą': 0x7B,
    'ć': 0x7C, 'Ć': 0x7C,
    'ę': 0x7D, 'Ę': 0x7D,
    'ł': 0x7E, 'Ł': 0x7E,
    'ń': 0x7F, 'Ń': 0x7F,
    'ó': 0x5F, 'Ó': 0x5F,
    'ś': 0x5E, 'Ś': 0x5E,
    'ź': 0x5D, 'Ź': 0x5D,
    'ż': 0x5C, 'Ż': 0x5C
}

def to_screencodes(s: str) -> list:
    codes = []
    for c in s:
        if c in POLISH_CHARS:
            codes.append(POLISH_CHARS[c])
        else:
            val = ord(c)
            if 32 <= val <= 95:
                codes.append(val - 32)
            elif 96 <= val <= 127:
                codes.append(val)
            elif 0 <= val <= 31:
                codes.append(val + 64)
            else:
                codes.append(val)
    return codes

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
            
        out.append("\n; Region Palette Offsets (Indexed by RegionId)")
        out.append("REGION_PALETTE_OFFSETS")
        for i, r in enumerate(self.regions_sorted):
            out.append(f"    dta {i * 9} ; Region {r.id}")
            
        out.append("\n; Region Palettes (9 bytes per region: PCOLR0-3, COLPF0-3, COLBK)")
        out.append("REGION_PALETTES")
        for r in self.regions_sorted:
            p = r.palette
            # order: PCOLR0, PCOLR1, PCOLR2, PCOLR3, COLPF0, COLPF1, COLPF2, COLPF3_INV, COLBK
            p_bytes = [
                p.get("PCOLR0", 0x0E), p.get("PCOLR1", 0x0E), p.get("PCOLR2", 0x0E), p.get("PCOLR3", 0x0E),
                p.get("PF0", 0), p.get("PF1", 0), p.get("PF2", 0), p.get("PF3_INV", 0), p.get("BACKGROUND", 0)
            ]
            hex_bytes = ", ".join(f"${b:02X}" for b in p_bytes)
            out.append(f"    dta {hex_bytes} ; Region {r.id}")
            
        # Mapping of ScreenId to RegionId
        screen_regions = []
        for s in self.screens_sorted:
            # Find region containing s
            region_found = None
            for r in self.regions_sorted:
                if any(x.id == s.id for x in r.screens):
                    region_found = r
                    break
            if region_found:
                screen_regions.append(self.region_idx[region_found.id])
            else:
                screen_regions.append(0)
                
        out.append("\n; Mapping of ScreenId to RegionId")
        out.append("SCREEN_REGION")
        out.append(f"    dta {', '.join(str(idx) for idx in screen_regions)}")
        
        # Region Names Pointers Table
        out.append("\n; Region Names Pointers Table")
        out.append("REGION_NAMES_LO")
        for i, r in enumerate(self.regions_sorted):
            out.append(f"    dta <REGION_NAME_{i}")
        out.append("REGION_NAMES_HI")
        for i, r in enumerate(self.regions_sorted):
            out.append(f"    dta >REGION_NAME_{i}")
            
        # Padded Region Names (31 bytes each)
        out.append("\n; Padded Region Names (31 bytes each)")
        for i, r in enumerate(self.regions_sorted):
            codes = to_screencodes(r.name)
            # Pad to 31 bytes
            codes = codes[:31] + [0] * (31 - len(codes))
            hex_bytes = ", ".join(f"${b:02X}" for b in codes)
            out.append(f"REGION_NAME_{i}")
            out.append(f"    dta {hex_bytes} ; \"{r.name}\"")
            
        # Enemy Damage Table (Indexed by Enemy Type ID)
        out.append("\n; Enemy Damage Table (Indexed by Enemy Type ID)")
        out.append("ENEMY_DAMAGE")
        for e in self.world.enemies:
            out.append(f"    dta {e.damage} ; {e.id}")

        # Region Damage Table (Indexed by RegionId)
        out.append("\n; Region Damage Table (Indexed by RegionId)")
        out.append("REGION_DAMAGE")
        for r in self.regions_sorted:
            out.append(f"    dta {r.damage} ; Region {r.id}")

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
        
        enemy_types = {e.id: idx for idx, e in enumerate(self.world.enemies)}
        strategies = {"horizontal": 0, "vertical": 1, "random": 2, "chaotic": 3, "patrol": 4, "pacing": 5, "snake": 6, "homing": 7}
        speeds = {"slow": 0, "medium": 1, "fast": 2}
        
        for s in self.screens_sorted:
            out.append(f"SCREEN_{s.id}")
            out.append(f"    dta {len(s.objects)} ; Object count")
            for inst in s.objects:
                obj_def = objects_by_id[inst.object]
                out.append(f"    dta {obj_def.code}, {inst.x}, {inst.y} ; {inst.object}")
            
            # Append compiled enemy data
            out.append(f"    dta {len(s.enemies)} ; Enemy count")
            for inst in s.enemies:
                e_type = enemy_types.get(inst.enemy, 0)
                pixel_x = inst.x * 4 + 48
                pixel_y = inst.y * 16 + 32
                e_strat = strategies.get(inst.strategy, 1)
                e_speed = speeds.get(inst.speed, 1)
                e_color = self.world.enemy_colors.get(inst.color, 15)
                
                out.append(f"    dta {e_type}, {pixel_x}, {pixel_y}, {e_strat}, {e_speed}, {e_color} ; enemy {inst.enemy} (x={inst.x}, y={inst.y}, strategy={inst.strategy}, speed={inst.speed}, color={inst.color})")
                
        with open(self.out_dir / "screens.asm", "w", encoding="utf-8") as f:
            f.write("\n".join(out) + "\n")
            
    def _generate_world_inc(self):
        out = ["; World Builder Master Include File"]
        out.append(f"SCREEN_COUNT = {len(self.screens_sorted)}")
        
        out.append("\n; Global Screen Translation Constants")
        for s in self.screens_sorted:
            out.append(f"SCREEN_ID_{s.id} = {self.screen_idx[s.id]}")
            
        out.append("\n; Player Spawn Configuration")
        out.append(f"START_REGION_ID = {self.region_idx[self.world.world.start_region]}")
        out.append(f"START_SCREEN_ID = {self.screen_idx[self.world.world.start_screen]}")
        out.append(f"START_POS_X = {self.world.world.start_position.x}")
        out.append(f"START_POS_Y = {self.world.world.start_position.y}")
        
        with open(self.out_dir / "world.inc", "w", encoding="utf-8") as f:
            f.write("\n".join(out) + "\n")
