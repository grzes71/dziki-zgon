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
        self._generate_interactive_objects()
        self._generate_secret_objects()
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
                
        out.append("\n; PackedFlags (Bit 7: blocking, Bit 6: interactive, Bit 5: secret)")
        out.append("OBJ_FLAGS")
        for code in range(max_code + 1):
            if code in objects_by_code:
                obj = objects_by_code[code]
                flags = 0
                if obj.flags.blocking: flags |= 0x80
                if obj.flags.interactive: flags |= 0x40
                if getattr(obj.flags, 'secret', False): flags |= 0x20
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
            
        # Padded Region Names (20 bytes each)
        out.append("\n; Padded Region Names (20 bytes each)")
        for i, r in enumerate(self.regions_sorted):
            codes = to_screencodes(r.name)
            # Pad to 20 bytes
            codes = codes[:20] + [0] * (20 - len(codes))
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
                # Coordinates packed into a single byte: 5 lower bits = x // 2, 3 upper bits = y // 2
                x_half = inst.x // 2
                y_half = inst.y // 2
                packed_xy = (y_half << 5) | x_half
                out.append(f"    dta {obj_def.code}, {packed_xy} ; {inst.object} (x={inst.x}, y={inst.y})")
            
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
        out.append(f"START_POS_X = {(self.world.world.start_position.x // 2) * 2}")
        out.append(f"START_POS_Y = {(self.world.world.start_position.y // 2) * 2}")
        
        with open(self.out_dir / "world.inc", "w", encoding="utf-8") as f:
            f.write("\n".join(out) + "\n")

    def _generate_interactive_objects(self):
        out = ["; Interactive Objects Data & Item Charset Table"]
        
        # Item Charset Position Table
        max_item_id = max((item.id for item in self.world.inventory_items), default=0)
        item_pos_map = {item.id: item.charset_position for item in self.world.inventory_items}
        item_flag_map = {item.id: (1 if item.consumable else 0) for item in self.world.inventory_items}
        
        out.append("ITEM_CHARSET_POS")
        out.append("    dta 14 ; ID 0 (Empty slot)")
        for item_id in range(1, max_item_id + 1):
            pos = item_pos_map.get(item_id, 14)
            out.append(f"    dta {pos} ; Item ID {item_id}")
            
        out.append("\nITEM_FLAGS")
        out.append("    dta 0 ; ID 0 (Empty slot)")
        for item_id in range(1, max_item_id + 1):
            flag = item_flag_map.get(item_id, 1)
            out.append(f"    dta {flag} ; Item ID {item_id}")
            
        out.append("\n; Interactive Objects Table (Indexed by ScreenId)")
        objects_by_id = {obj.id: obj for obj in self.world.objects}
        
        interactive_data = []
        for s in self.screens_sorted:
            inter_inst = None
            for inst in s.objects:
                obj_def = objects_by_id.get(inst.object)
                if obj_def and obj_def.flags.interactive:
                    inter_inst = (inst, obj_def)
                    break
            interactive_data.append(inter_inst)

        # INTERACTIVE_OBJ_PRESENT
        out.append("INTERACTIVE_OBJ_PRESENT")
        out.append("    dta " + ", ".join("1" if d else "0" for d in interactive_data))

        # INTERACTIVE_OBJ_X
        out.append("INTERACTIVE_OBJ_X")
        out.append("    dta " + ", ".join(str((d[0].x // 2) * 2) if d else "0" for d in interactive_data))

        # INTERACTIVE_OBJ_Y
        out.append("INTERACTIVE_OBJ_Y")
        out.append("    dta " + ", ".join(str((d[0].y // 2) * 2) if d else "0" for d in interactive_data))

        # INTERACTIVE_OBJ_W
        out.append("INTERACTIVE_OBJ_W")
        out.append("    dta " + ", ".join(str(d[1].size.width) if d else "0" for d in interactive_data))

        # INTERACTIVE_OBJ_H
        out.append("INTERACTIVE_OBJ_H")
        out.append("    dta " + ", ".join(str(d[1].size.height) if d else "0" for d in interactive_data))

        # INTERACTIVE_OBJ_COMPLETE_INIT
        out.append("INTERACTIVE_OBJ_COMPLETE_INIT")
        out.append("    dta " + ", ".join("1" if (d and d[0].items_required and len(d[0].items_required) > 0) else "0" for d in interactive_data))

        # INTERACTIVE_OBJ_TYPE (0=kwatera, 1=portal)
        out.append("INTERACTIVE_OBJ_TYPE")
        out.append("    dta " + ", ".join("1" if (d and d[0].type == "portal") else "0" for d in interactive_data))

        # Reqs and Provs and Msgs
        out.append("INTERACTIVE_OBJ_REQ_COUNT")
        out.append("    dta " + ", ".join(str(len(d[0].items_required or [])) if d else "0" for d in interactive_data))

        out.append("INTERACTIVE_OBJ_REQ_PTR_LO")
        out.append("    dta " + ", ".join(f"<(REQ_ITEMS_SCR_{i})" if (d and d[0].items_required) else "<(EMPTY_ITEM_LIST)" for i, d in enumerate(interactive_data)))

        out.append("INTERACTIVE_OBJ_REQ_PTR_HI")
        out.append("    dta " + ", ".join(f">(REQ_ITEMS_SCR_{i})" if (d and d[0].items_required) else ">(EMPTY_ITEM_LIST)" for i, d in enumerate(interactive_data)))

        out.append("INTERACTIVE_OBJ_PROV_COUNT")
        out.append("    dta " + ", ".join(str(len(d[0].items_provided or [])) if d else "0" for d in interactive_data))

        out.append("INTERACTIVE_OBJ_PROV_PTR_LO")
        out.append("    dta " + ", ".join(f"<(PROV_ITEMS_SCR_{i})" if (d and d[0].items_provided) else "<(EMPTY_ITEM_LIST)" for i, d in enumerate(interactive_data)))

        out.append("INTERACTIVE_OBJ_PROV_PTR_HI")
        out.append("    dta " + ", ".join(f">(PROV_ITEMS_SCR_{i})" if (d and d[0].items_provided) else ">(EMPTY_ITEM_LIST)" for i, d in enumerate(interactive_data)))

        out.append("INTERACTIVE_OBJ_MSG_MET_LO")
        out.append("    dta " + ", ".join(f"<(MSG_MET_SCR_{i})" if (d and d[0].conditions_met) else "<(EMPTY_MSG_STRING)" for i, d in enumerate(interactive_data)))

        out.append("INTERACTIVE_OBJ_MSG_MET_HI")
        out.append("    dta " + ", ".join(f">(MSG_MET_SCR_{i})" if (d and d[0].conditions_met) else ">(EMPTY_MSG_STRING)" for i, d in enumerate(interactive_data)))

        out.append("INTERACTIVE_OBJ_MSG_UNMET_LO")
        out.append("    dta " + ", ".join(f"<(MSG_UNMET_SCR_{i})" if (d and d[0].conditions_unmet) else "<(EMPTY_MSG_STRING)" for i, d in enumerate(interactive_data)))

        out.append("INTERACTIVE_OBJ_MSG_UNMET_HI")
        out.append("    dta " + ", ".join(f">(MSG_UNMET_SCR_{i})" if (d and d[0].conditions_unmet) else ">(EMPTY_MSG_STRING)" for i, d in enumerate(interactive_data)))

        out.append("INTERACTIVE_OBJ_MSG_TRAVEL_LO")
        out.append("    dta " + ", ".join(f"<(MSG_TRAVEL_SCR_{i})" if (d and d[0].message_travel) else "<(EMPTY_MSG_STRING)" for i, d in enumerate(interactive_data)))

        out.append("INTERACTIVE_OBJ_MSG_TRAVEL_HI")
        out.append("    dta " + ", ".join(f">(MSG_TRAVEL_SCR_{i})" if (d and d[0].message_travel) else ">(EMPTY_MSG_STRING)" for i, d in enumerate(interactive_data)))

        # Portal Target resolution: ScreenId, Target Pixel X, Target Pixel Y
        regions_by_id = {r.id: r for r in self.world.regions}
        screen_region_map = {}
        for r in self.world.regions:
            for sc in r.screens:
                screen_region_map[sc.id] = r

        portal_screen_list = []
        portal_x_list = []
        portal_y_list = []

        for s, d in zip(self.screens_sorted, interactive_data):
            if d and d[0].type == "portal" and d[0].target_region:
                source_region = screen_region_map.get(s.id)
                target_region_obj = regions_by_id.get(d[0].target_region)
                p_entry = target_region_obj.portal_entries.get(source_region.id) if (target_region_obj and source_region) else None
                if p_entry and p_entry.screen in self.screen_idx:
                    portal_screen_list.append(f"${self.screen_idx[p_entry.screen]:02X}")
                    p_entry_x_even = (p_entry.x // 2) * 2
                    p_entry_y_even = (p_entry.y // 2) * 2
                    portal_x_list.append(str(p_entry_x_even * 4 + 48))
                    portal_y_list.append(str(p_entry_y_even * 16 + 32))
                else:
                    portal_screen_list.append("$FF")
                    portal_x_list.append("0")
                    portal_y_list.append("0")
            else:
                portal_screen_list.append("$FF")
                portal_x_list.append("0")
                portal_y_list.append("0")

        out.append("INTERACTIVE_OBJ_PORTAL_SCREEN")
        out.append("    dta " + ", ".join(portal_screen_list))

        out.append("INTERACTIVE_OBJ_PORTAL_X")
        out.append("    dta " + ", ".join(portal_x_list))

        out.append("INTERACTIVE_OBJ_PORTAL_Y")
        out.append("    dta " + ", ".join(portal_y_list))

        out.append("\n; Dummy Data Labels")
        out.append("EMPTY_ITEM_LIST")
        out.append("    dta 0")
        out.append("EMPTY_MSG_STRING")
        out.append("    dta 0")

        out.append("\n; Screen Specific Interactive Object Data")
        for i, d in enumerate(interactive_data):
            if not d:
                continue
            inst, _ = d
            if inst.items_required:
                items_str = ", ".join(str(item_id) for item_id in inst.items_required)
                out.append(f"REQ_ITEMS_SCR_{i}")
                out.append(f"    dta {items_str}")
            if inst.items_provided:
                items_str = ", ".join(str(item_id) for item_id in inst.items_provided)
                out.append(f"PROV_ITEMS_SCR_{i}")
                out.append(f"    dta {items_str}")
            if inst.conditions_met:
                bytes_str = ", ".join(str(b) for b in inst.conditions_met.encode("utf-8") + b"\x00")
                out.append(f"MSG_MET_SCR_{i}")
                out.append(f"    dta {bytes_str}")
            if inst.conditions_unmet:
                bytes_str = ", ".join(str(b) for b in inst.conditions_unmet.encode("utf-8") + b"\x00")
                out.append(f"MSG_UNMET_SCR_{i}")
                out.append(f"    dta {bytes_str}")
            if inst.message_travel:
                bytes_str = ", ".join(str(b) for b in inst.message_travel.encode("utf-8") + b"\x00")
                out.append(f"MSG_TRAVEL_SCR_{i}")
                out.append(f"    dta {bytes_str}")

        with open(self.out_dir / "interactive_objects.asm", "w", encoding="utf-8") as f:
            f.write("\n".join(out) + "\n")

    def _generate_secret_objects(self):
        out = ["; Secret Objects Table (Indexed by ScreenId)"]
        objects_by_id = {obj.id: obj for obj in self.world.objects}
        
        secret_data = []
        for s in self.screens_sorted:
            sec_inst = None
            for inst in s.objects:
                obj_def = objects_by_id.get(inst.object)
                if obj_def and obj_def.flags and getattr(obj_def.flags, 'secret', False):
                    sec_inst = (inst, obj_def)
                    break
            secret_data.append(sec_inst)

        # SECRET_OBJ_PRESENT
        out.append("SECRET_OBJ_PRESENT")
        out.append("    dta " + ", ".join("1" if d else "0" for d in secret_data))

        # SECRET_OBJ_X
        out.append("SECRET_OBJ_X")
        out.append("    dta " + ", ".join(str((d[0].x // 2) * 2) if d else "0" for d in secret_data))

        # SECRET_OBJ_Y
        out.append("SECRET_OBJ_Y")
        out.append("    dta " + ", ".join(str((d[0].y // 2) * 2) if d else "0" for d in secret_data))

        # SECRET_OBJ_W
        out.append("SECRET_OBJ_W")
        out.append("    dta " + ", ".join(str(d[1].size.width) if d else "0" for d in secret_data))

        # SECRET_OBJ_H
        out.append("SECRET_OBJ_H")
        out.append("    dta " + ", ".join(str(d[1].size.height) if d else "0" for d in secret_data))

        # SECRET_OBJ_CODE
        out.append("SECRET_OBJ_CODE")
        out.append("    dta " + ", ".join(str(d[1].code) if d else "0" for d in secret_data))

        # SECRET_OBJ_ITEM (Item ID to provide)
        out.append("SECRET_OBJ_ITEM")
        item_ids = []
        for d in secret_data:
            if d and d[0].items_provided and len(d[0].items_provided) > 0:
                item_ids.append(str(d[0].items_provided[0]))
            else:
                item_ids.append("0")
        out.append("    dta " + ", ".join(item_ids))

        # ITEM_NAME_LO/HI — Item name pointers (indexed by Item ID)
        # Only item names are stored; the "znalazłeś " prefix is in 6502 code
        item_desc_map = {item.id: item.description for item in self.world.inventory_items}
        max_item_id = max((item.id for item in self.world.inventory_items), default=0)

        out.append("ITEM_NAME_LO")
        parts_lo = ["<(ITEM_NAME_EMPTY)"]  # ID 0 = no item
        for item_id in range(1, max_item_id + 1):
            if item_id in item_desc_map:
                parts_lo.append(f"<(ITEM_NAME_{item_id})")
            else:
                parts_lo.append("<(ITEM_NAME_EMPTY)")
        out.append("    dta " + ", ".join(parts_lo))

        out.append("ITEM_NAME_HI")
        parts_hi = [">(ITEM_NAME_EMPTY)"]  # ID 0 = no item
        for item_id in range(1, max_item_id + 1):
            if item_id in item_desc_map:
                parts_hi.append(f">(ITEM_NAME_{item_id})")
            else:
                parts_hi.append(">(ITEM_NAME_EMPTY)")
        out.append("    dta " + ", ".join(parts_hi))

        out.append("ITEM_NAME_EMPTY")
        out.append("    dta 0")

        for item_id in range(1, max_item_id + 1):
            if item_id in item_desc_map:
                name = item_desc_map[item_id]
                bytes_str = ", ".join(str(b) for b in name.encode("utf-8") + b"\x00")
                out.append(f"ITEM_NAME_{item_id}")
                out.append(f"    dta {bytes_str} ; \"{name}\"")

        with open(self.out_dir / "secret_objects.asm", "w", encoding="utf-8") as f:
            f.write("\n".join(out) + "\n")

    def get_stats(self) -> dict:
        max_code = max((obj.code for obj in self.world.objects), default=0)
        objects_bytes = 4 * (max_code + 1) + sum(len(obj.tiles) for obj in self.world.objects)

        num_regions = len(self.regions_sorted)
        num_screens = len(self.screens_sorted)
        num_enemies = len(self.world.enemies)

        regions_bytes = 38 * num_regions + num_screens + num_enemies
        exits_bytes = 4 * num_screens

        screens_bytes = 2 * num_screens
        placed_objects_count = 0
        placed_enemies_count = 0
        for s in self.screens_sorted:
            placed_objects_count += len(s.objects)
            placed_enemies_count += len(s.enemies)
            screens_bytes += 2 + 2 * len(s.objects) + 6 * len(s.enemies)

        max_item_id = max((item.id for item in self.world.inventory_items), default=0)

        # Interactive objects
        objects_by_id = {obj.id: obj for obj in self.world.objects}
        interactive_data = []
        for s in self.screens_sorted:
            inter_inst = None
            for inst in s.objects:
                obj_def = objects_by_id.get(inst.object)
                if obj_def and obj_def.flags.interactive:
                    inter_inst = (inst, obj_def)
                    break
            interactive_data.append(inter_inst)

        interactive_bytes = (max_item_id + 1) + 22 * num_screens + 2
        for d in interactive_data:
            if not d:
                continue
            inst, _ = d
            if inst.items_required:
                interactive_bytes += len(inst.items_required)
            if inst.items_provided:
                interactive_bytes += len(inst.items_provided)
            if inst.conditions_met:
                interactive_bytes += len(inst.conditions_met.encode("utf-8")) + 1
            if inst.conditions_unmet:
                interactive_bytes += len(inst.conditions_unmet.encode("utf-8")) + 1
            if inst.message_travel:
                interactive_bytes += len(inst.message_travel.encode("utf-8")) + 1

        # Secret objects
        secret_bytes = 7 * num_screens + 2 * (max_item_id + 1) + 1
        item_desc_map = {item.id: item.description for item in self.world.inventory_items}
        for item_id in range(1, max_item_id + 1):
            if item_id in item_desc_map:
                secret_bytes += len(item_desc_map[item_id].encode("utf-8")) + 1

        main_world_bytes = objects_bytes + regions_bytes + screens_bytes + exits_bytes
        total_world_bytes = main_world_bytes + interactive_bytes + secret_bytes

        # Memory Budget for Main World Data ($6800 - $9D1F = 13,600 bytes)
        main_budget = 13600
        free_main = main_budget - main_world_bytes
        free_main_pct = (free_main / main_budget) * 100.0 if main_budget > 0 else 0

        return {
            "num_regions": num_regions,
            "num_screens": num_screens,
            "num_object_defs": len(self.world.objects),
            "placed_objects_count": placed_objects_count,
            "placed_enemies_count": placed_enemies_count,
            "objects_bytes": objects_bytes,
            "regions_bytes": regions_bytes,
            "screens_bytes": screens_bytes,
            "exits_bytes": exits_bytes,
            "interactive_bytes": interactive_bytes,
            "secret_bytes": secret_bytes,
            "main_world_bytes": main_world_bytes,
            "total_world_bytes": total_world_bytes,
            "main_budget": main_budget,
            "free_main": free_main,
            "free_main_pct": free_main_pct,
        }

