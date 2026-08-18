#!/usr/bin/env python3
"""
analyze_objects.py — Analizator wystąpień obiektów i znaków charsetu w świecie gry.

PRZYPADKI UŻYCIA (USE CASES):
1. Pełny raport wystąpień obiektów (gdzie i ile razy każdy obiekt jest postawiony):
   python scripts/analyze_objects.py

2. Ograniczenie analizy do konkretnego regionu:
   python scripts/analyze_objects.py -r WHITE_FIELD

3. Analiza nieużywanych znaków charsetu (0-127) oraz obiektów bezpiecznych do usunięcia:
   python scripts/analyze_objects.py -c
   (Wykrywa nieużywane znaki w charsecie oraz klasyfikuje nieużywane obiekty pod kątem
    możliwości bezpiecznego przeprojektowania ich znaków).

4. Raport nieużywanych obiektów i znaków do odzyskania / przeprojektowania:
   python scripts/analyze_objects.py -u
   (lub --unused-objects / --cleanup)

5. Zbiorcze statystyki świata gry (przeciwnicy, portale, kwatery, sekrety, tagi):
   python scripts/analyze_objects.py -s
   python scripts/analyze_objects.py -s -r LAS_PIJANEGO_ZAJACA

6. Kombinacja flag (np. pełne statystyki + analiza czyszczenia):
   python scripts/analyze_objects.py -c -u -s
"""
import sys
import argparse
from pathlib import Path
from collections import Counter
import yaml

def print_world_stats(base_dir, objects_data, target_region=None):
    enemies_meta = {}
    enemies_file = base_dir / "enemies.yaml"
    if enemies_file.exists():
        with open(enemies_file, 'r', encoding='utf-8') as ef:
            edata = yaml.safe_load(ef) or {}
            for e in edata.get("enemies", []):
                if isinstance(e, dict) and "id" in e:
                    enemies_meta[e["id"]] = e.get("name", e["id"])

    objects_dict = {}
    defined_tags = list(objects_data.get("tags", [])) if objects_data else []
    if objects_data and "objects" in objects_data:
        for obj in objects_data["objects"]:
            obj_id = obj.get("id") or obj.get("object")
            if obj_id:
                objects_dict[obj_id] = obj
                for t in obj.get("tags", []):
                    if t not in defined_tags:
                        defined_tags.append(t)

    region_stats = {}
    
    for item in sorted(base_dir.iterdir()):
        if item.is_dir() and (item / "region.yaml").exists():
            region_id = item.name
            if target_region and region_id.lower() != target_region.lower():
                continue
                
            with open(item / "region.yaml", 'r', encoding='utf-8') as rf:
                reg_data = yaml.safe_load(rf) or {}
                
            portal_entries = reg_data.get("portal_entries", {})
            portal_entries_count = len(portal_entries) if isinstance(portal_entries, dict) else 0
            
            enemies_counter = Counter()
            total_objects = 0
            interactive_count = 0
            kwatery_count = 0
            portals_count = 0
            secrets_count = 0
            tags_counter = Counter()
            
            screens_dir = item / "screens"
            if screens_dir.exists() and screens_dir.is_dir():
                for sf in sorted(screens_dir.glob("*.yaml")):
                    with open(sf, 'r', encoding='utf-8') as scf:
                        sd = yaml.safe_load(scf) or {}
                        
                    for enemy_inst in sd.get("enemies", []):
                        if isinstance(enemy_inst, dict):
                            eid = enemy_inst.get("enemy")
                            if eid:
                                enemies_counter[eid] += 1
                                
                    for inst in sd.get("objects", []):
                        if not isinstance(inst, dict):
                            continue
                        oid = inst.get("object")
                        if not oid:
                            continue
                        rx = int(inst.get("repeat-x", 1))
                        ry = int(inst.get("repeat-y", 1))
                        cnt = rx * ry
                        
                        total_objects += cnt
                        
                        odef = objects_dict.get(oid, {})
                        oflags = odef.get("flags", {})
                        otags = odef.get("tags", [])
                        itype = inst.get("type")
                        
                        is_interactive = (
                            bool(oflags.get("interactive"))
                            or (itype in ["interactive", "kwatera", "portal"])
                            or ("interakcja" in otags)
                            or (inst.get("target_region") is not None)
                        )
                        is_kwatera = (itype == "kwatera") or ("kwatera" in otags)
                        is_portal = (itype == "portal") or ("portal" in otags) or (inst.get("target_region") is not None)
                        is_secret = (
                            bool(oflags.get("secret"))
                            or ("sekret" in otags)
                            or (itype == "secret")
                            or (inst.get("secret") is True)
                        )
                        
                        if is_interactive:
                            interactive_count += cnt
                        if is_kwatera:
                            kwatery_count += cnt
                        if is_portal:
                            portals_count += cnt
                        if is_secret:
                            secrets_count += cnt
                            
                        for t in otags:
                            tags_counter[t] += cnt
                            
            region_stats[region_id] = {
                "portal_entries": portal_entries_count,
                "enemies": enemies_counter,
                "total_enemies": sum(enemies_counter.values()),
                "total_objects": total_objects,
                "interactive": interactive_count,
                "kwatery": kwatery_count,
                "portals": portals_count,
                "secrets": secrets_count,
                "tags": tags_counter
            }

    global_enemies = Counter()
    global_portal_entries = 0
    global_secrets = 0
    global_total_objects = 0
    global_interactive = 0
    global_kwatery = 0
    global_portals = 0
    global_tags = Counter()

    for rdata in region_stats.values():
        global_enemies.update(rdata["enemies"])
        global_portal_entries += rdata["portal_entries"]
        global_secrets += rdata["secrets"]
        global_total_objects += rdata["total_objects"]
        global_interactive += rdata["interactive"]
        global_kwatery += rdata["kwatery"]
        global_portals += rdata["portals"]
        global_tags.update(rdata["tags"])

    target_str = f" [region: {target_region}]" if target_region else ""
    print(f"\n=== STATYSTYKI ŚWIATA GRY (OGÓŁEM){target_str} ===")
    total_e_count = sum(global_enemies.values())
    print(f"Ilość przeciwników (ogółem: {total_e_count}):")
    if global_enemies:
        for eid, cnt in sorted(global_enemies.items(), key=lambda x: (-x[1], x[0])):
            name_str = f" ({enemies_meta[eid]})" if eid in enemies_meta and enemies_meta[eid] != eid else ""
            print(f"  - {eid}{name_str}: {cnt}")
    else:
        print("  - (brak)")
        
    print(f"Ilość portal entry: {global_portal_entries}")
    print(f"Ilość secret'ów: {global_secrets}")
    print(f"Ilość obiektów (ogółem: {global_total_objects}):")
    print(f"  - Interaktywne: {global_interactive}")
    print(f"  - Kwatery: {global_kwatery}")
    print(f"  - Portale: {global_portals}")
    
    print("Ilość obiektów dla każdego tagu:")
    if global_tags:
        for t in defined_tags:
            print(f"  - {t}: {global_tags.get(t, 0)}")
        extra_tags = [t for t in global_tags if t not in defined_tags]
        for t in sorted(extra_tags):
            print(f"  - {t}: {global_tags[t]}")
    else:
        print("  - (brak)")

    print(f"\n=== STATYSTYKI W ROZBICIU NA POSZCZEGÓLNE REGIONY{target_str} ===")
    for rid, rdata in region_stats.items():
        print(f"\n--- Region: {rid} ---")
        renemies = rdata["enemies"]
        print(f"Ilość przeciwników (ogółem: {rdata['total_enemies']}):")
        if renemies:
            for eid, cnt in sorted(renemies.items(), key=lambda x: (-x[1], x[0])):
                name_str = f" ({enemies_meta[eid]})" if eid in enemies_meta and enemies_meta[eid] != eid else ""
                print(f"  - {eid}{name_str}: {cnt}")
        else:
            print("  - (brak)")
            
        print(f"Ilość portal entry: {rdata['portal_entries']}")
        print(f"Ilość secret'ów: {rdata['secrets']}")
        print(f"Ilość obiektów (ogółem: {rdata['total_objects']}):")
        print(f"  - Interaktywne: {rdata['interactive']}")
        print(f"  - Kwatery: {rdata['kwatery']}")
        print(f"  - Portale: {rdata['portals']}")
        
        print("Ilość obiektów dla każdego tagu:")
        rtags = rdata["tags"]
        if rtags:
            for t in defined_tags:
                print(f"  - {t}: {rtags.get(t, 0)}")
            extra_tags = [t for t in rtags if t not in defined_tags]
            for t in sorted(extra_tags):
                print(f"  - {t}: {rtags[t]}")
        else:
            print("  - (brak)")


def print_unused_cleanup_report(object_tiles, object_counts, target_region=None):
    region_str = f" [region: {target_region}]" if target_region else ""
    print(f"\n=== ANALIZA NIEUŻYWANYCH OBIEKTÓW I MOŻLIWOŚCI PRZEPROJEKTOWANIA ZNAKÓW{region_str} ===")

    placed_tiles = set()
    for oid, count in object_counts.items():
        if count > 0 and oid in object_tiles:
            for t in object_tiles[oid]:
                if isinstance(t, int):
                    placed_tiles.add(t % 128)

    unused_objects = [oid for oid, count in object_counts.items() if count == 0]

    fully_unused_objs = []
    partially_unused_objs = []
    locked_unused_objs = []

    for oid in sorted(unused_objects):
        raw_tiles = object_tiles.get(oid, [])
        otiles = set(t % 128 for t in raw_tiles if isinstance(t, int))
        shared = otiles & placed_tiles
        exclusive = otiles - placed_tiles

        if not shared:
            fully_unused_objs.append((oid, sorted(otiles)))
        elif exclusive:
            partially_unused_objs.append((oid, sorted(exclusive), sorted(shared)))
        else:
            locked_unused_objs.append((oid, sorted(otiles)))

    freed_tiles_100 = set()
    for _, tiles in fully_unused_objs:
        freed_tiles_100.update(tiles)

    print(f"\n1. OBIEKTY W 100% BEZPIECZNE DO USUNIĘCIA (oraz ich znaki do przeprojektowania) [{len(fully_unused_objs)} obiektów]:")
    print("   (Żaden ze znaków tych obiektów nie jest używany przez żaden obiekt na planszach)")
    if fully_unused_objs:
        for oid, tiles in fully_unused_objs:
            print(f"   - {oid:<22} znaki charsetu: {tiles}")
        print(f"\n   -> ŁĄCZNIE WOLNE ZNAKI CHARSETU Z TEJ GRUPY ({len(freed_tiles_100)}):")
        print(f"      {sorted(freed_tiles_100)}")
    else:
        print("   (Brak takich obiektów)")

    print(f"\n2. NIEUŻYWANE OBIEKTY O CZĘŚCIOWO WOLNYCH ZNAKACH [{len(partially_unused_objs)} obiektów]:")
    print("   (Obiekt można usunąć z objects.yaml, ale przeprojektować wolno TYLKO znaki niewspółdzielone)")
    if partially_unused_objs:
        for oid, excl, shared in partially_unused_objs:
            print(f"   - {oid:<22} wolne znaki: {excl} | współdzielone z grą: {shared}")
    else:
        print("   (Brak)")

    print(f"\n3. NIEUŻYWANE OBIEKTY O CAŁKOWICIE ZABLOKOWANYCH ZNAKACH [{len(locked_unused_objs)} obiektów]:")
    print("   (Obiekt można usunąć z objects.yaml, ale ŻADNEGO jego znaku NIE WOLNO modyfikować)")
    if locked_unused_objs:
        for oid, tiles in locked_unused_objs:
            print(f"   - {oid:<22} używane w innych obiektach: {tiles}")
    else:
        print("   (Brak)")


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        
    # Find base directory (world/)
    base_dir = Path(__file__).resolve().parent.parent / "world"
    if not base_dir.exists():
        base_dir = Path("world")
    
    if not base_dir.exists():
        print("Error: Could not find 'world' directory. Run the script from the project root.", file=sys.stderr)
        sys.exit(1)
        
    parser = argparse.ArgumentParser(description="Analyze object occurrences in the game world.")
    parser.add_argument(
        "--region", "-r",
        type=str,
        help="Limit the analysis to a specific region (e.g., WHITE_FIELD)"
    )
    parser.add_argument(
        "--unused-charset", "--charset", "-c",
        action="store_true",
        help="Report unused charset codes (0-127) not present in objects"
    )
    parser.add_argument(
        "--unused-objects", "--cleanup", "-u",
        action="store_true",
        help="Report unused objects and whether their charset tiles can be safely redesigned/reused"
    )
    parser.add_argument(
        "--stats", "-s",
        action="store_true",
        help="Report game world statistics (enemies, portal entries, secrets, object categories, tags)"
    )
    args = parser.parse_args()

        
    objects_file = base_dir / "objects.yaml"
    if not objects_file.exists():
        print(f"Error: Could not find objects.yaml at {objects_file}", file=sys.stderr)
        sys.exit(1)
        
    # Find all available regions
    available_regions = []
    for item in base_dir.iterdir():
        if item.is_dir() and (item / "region.yaml").exists():
            available_regions.append(item.name)
            
    target_region = None
    if args.region:
        matched = [r for r in available_regions if r.lower() == args.region.lower()]
        if not matched:
            print(f"Error: Region '{args.region}' not found.", file=sys.stderr)
            print(f"Available regions: {', '.join(available_regions)}", file=sys.stderr)
            sys.exit(1)
        target_region = matched[0]
        
    # Load objects
    with open(objects_file, 'r', encoding='utf-8') as f:
        objects_data = yaml.safe_load(f)
        
    defined_objects = []
    object_tiles = {}
    if objects_data and "objects" in objects_data:
        for obj in objects_data["objects"]:
            obj_id = obj.get("id") or obj.get("object")
            if obj_id:
                defined_objects.append(obj_id)
                object_tiles[obj_id] = obj.get("tiles", [])
                
    # Initialize data structures
    object_counts = {obj_id: 0 for obj_id in defined_objects}
    object_locations = {obj_id: set() for obj_id in defined_objects}
    
    undefined_objects_counts = {}
    undefined_objects_locations = {}
    
    # Scan all regions (subdirectories of world/ containing region.yaml)
    for item in base_dir.iterdir():
        if item.is_dir() and (item / "region.yaml").exists():
            region_id = item.name
            if target_region and region_id != target_region:
                continue
                
            screens_dir = item / "screens"
            if screens_dir.exists() and screens_dir.is_dir():
                for screen_file in screens_dir.glob("*.yaml"):
                    screen_id = screen_file.stem
                    with open(screen_file, 'r', encoding='utf-8') as sf:
                        screen_data = yaml.safe_load(sf)
                    
                    if not screen_data or "objects" not in screen_data:
                        continue
                        
                    for obj_inst in screen_data["objects"]:
                        obj_id = obj_inst.get("object")
                        if not obj_id:
                            continue
                            
                        # Calculate total instances taking repeat-x and repeat-y into account
                        repeat_x = int(obj_inst.get("repeat-x", 1))
                        repeat_y = int(obj_inst.get("repeat-y", 1))
                        count = repeat_x * repeat_y
                        
                        location = f"{region_id}-{screen_id}"
                        
                        if obj_id in object_counts:
                            object_counts[obj_id] += count
                            object_locations[obj_id].add(location)
                        else:
                            # Track undefined objects if any are used
                            undefined_objects_counts[obj_id] = undefined_objects_counts.get(obj_id, 0) + count
                            if obj_id not in undefined_objects_locations:
                                undefined_objects_locations[obj_id] = set()
                            undefined_objects_locations[obj_id].add(location)

    # Sort defined objects by count descending, then alphabetically
    sorted_defined = sorted(
        defined_objects,
        key=lambda oid: (-object_counts[oid], oid)
    )
    
    # Generate and print the report
    for oid in sorted_defined:
        count = object_counts[oid]
        locs = sorted(list(object_locations[oid]))
        locs_str = ", ".join(locs)
        print(f"{oid}: [{locs_str}] {count}")
            
    if undefined_objects_counts:
        print("\n=== NIEZDEFINIOWANE OBIEKTY (UŻYTE W GRACH, ALE BRAK W objects.yaml) ===")
        sorted_undefined = sorted(
            undefined_objects_counts.keys(),
            key=lambda oid: (-undefined_objects_counts[oid], oid)
        )
        for oid in sorted_undefined:
            count = undefined_objects_counts[oid]
            locs = sorted(list(undefined_objects_locations[oid]))
            locs_str = ", ".join(locs)
            print(f"{oid}: [{locs_str}] {count}")

    if args.unused_charset:
        print("\n=== NIEUŻYWANE KODY CHARSETU (0-127) ===")
        
        all_defined_tiles = set()
        for tiles in object_tiles.values():
            for t in tiles:
                if isinstance(t, int):
                    all_defined_tiles.add(t % 128)
                    
        unused_defined = sorted(set(range(128)) - all_defined_tiles)
        print(f"Nieużywane w definicjach objects.yaml ({len(unused_defined)}/128):")
        if unused_defined:
            print("  " + ", ".join(map(str, unused_defined)))
        else:
            print("  (Brak - wszystkie kody 0-127 są użyte w definicjach obiektów)")
            
        placed_tiles = set()
        for oid, count in object_counts.items():
            if count > 0 and oid in object_tiles:
                for t in object_tiles[oid]:
                    if isinstance(t, int):
                        placed_tiles.add(t % 128)
                        
        unused_placed = sorted(set(range(128)) - placed_tiles)
        region_str = f" [region: {target_region}]" if target_region else ""
        print(f"\nNieużywane w obiektach umieszczonych na planszach{region_str} ({len(unused_placed)}/128):")
        if unused_placed:
            print("  Kody: " + ", ".join(map(str, unused_placed)))
            print("  Występowanie w definicjach obiektów (objects.yaml):")
            for t in unused_placed:
                using_objs = [
                    oid for oid, tiles in object_tiles.items()
                    if any(isinstance(x, int) and (x % 128) == t for x in tiles)
                ]
                if using_objs:
                    print(f"    - Znak {t:>3}: {', '.join(sorted(using_objs))}")
                else:
                    print(f"    - Znak {t:>3}: (brak - nieużyty w żadnym obiekcie)")
        else:
            print("  (Brak - wszystkie kody 0-127 są użyte na planszach)")

    if args.unused_objects:
        print_unused_cleanup_report(object_tiles, object_counts, target_region)

    if args.stats:
        print_world_stats(base_dir, objects_data, target_region)

if __name__ == '__main__':

    main()

