#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path
import yaml

def main():
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
    if objects_data and "objects" in objects_data:
        for obj in objects_data["objects"]:
            obj_id = obj.get("id") or obj.get("object")
            if obj_id:
                defined_objects.append(obj_id)
                
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

if __name__ == '__main__':
    main()

