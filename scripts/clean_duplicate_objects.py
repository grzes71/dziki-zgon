import yaml
from pathlib import Path
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="Find and clean duplicate/invalid objects in Witcher Atari project.")
    parser.add_argument("--fix", action="store_true", help="Perform the actual removal and references replacement.")
    args = parser.parse_args()

    workspace_dir = Path(__file__).resolve().parent.parent
    world_dir = workspace_dir / "world"
    objects_yaml_path = world_dir / "objects.yaml"

    if not objects_yaml_path.exists():
        print(f"Error: {objects_yaml_path} does not exist.")
        sys.exit(1)

    with objects_yaml_path.open("r", encoding="utf-8") as f:
        objects_data = yaml.safe_load(f) or {}

    objects_list = objects_data.get("objects", [])
    print(f"Loaded {len(objects_list)} object definitions.")

    # Group objects by width, height, and tiles layout
    groups = {}  # key -> list of obj
    for obj in objects_list:
        width = obj.get("size", {}).get("width", 1)
        height = obj.get("size", {}).get("height", 1)
        tiles = tuple(obj.get("tiles", []))
        key = (width, height, tiles)
        groups.setdefault(key, []).append(obj)

    duplicate_to_proper = {}
    duplicates_set = set()

    print("\nChecking for duplicates...")
    duplicate_groups_found = 0
    for key, group in groups.items():
        if len(group) > 1:
            duplicate_groups_found += 1
            proper = group[0]
            proper_id = proper["id"]
            dups = group[1:]
            print(f"\nGroup {duplicate_groups_found}:")
            print(f"  Proper (first occurrence): {proper_id} (code: {proper.get('code')})")
            for dup in dups:
                dup_id = dup["id"]
                duplicate_to_proper[dup_id] = proper_id
                duplicates_set.add(dup_id)
                print(f"  Duplicate: {dup_id} (code: {dup.get('code')})")

    valid_object_ids = {obj["id"] for obj in objects_list if obj["id"] not in duplicates_set}

    screen_files = list(world_dir.glob("**/screens/*.yaml"))
    print(f"\nScanning {len(screen_files)} screen files for duplicate/invalid references...")

    screens_to_update = []  # list of (screen_file, screen_data, new_objects, num_replaced, num_removed)
    replaced_instances_total = 0
    removed_instances_total = 0

    for screen_file in screen_files:
        with screen_file.open("r", encoding="utf-8") as f:
            screen_data = yaml.safe_load(f) or {}

        objects = screen_data.get("objects", [])
        new_objects = []
        num_replaced = 0
        num_removed = 0
        screen_modified = False

        for inst in objects:
            obj_id = inst.get("object")
            # 1. Handle duplicate replacement
            if obj_id in duplicate_to_proper:
                proper_id = duplicate_to_proper[obj_id]
                inst["object"] = proper_id
                num_replaced += 1
                screen_modified = True
                obj_id = proper_id

            # 2. Check if the object is valid (exists in objects.yaml)
            if obj_id in valid_object_ids:
                new_objects.append(inst)
            else:
                num_removed += 1
                screen_modified = True

        if screen_modified:
            screens_to_update.append((screen_file, screen_data, new_objects, num_replaced, num_removed))
            replaced_instances_total += num_replaced
            removed_instances_total += num_removed

    if not duplicates_set and not screens_to_update:
        print("\nEverything is clean! No duplicates and no invalid objects found.")
        return

    # Print summary of changes
    if screens_to_update:
        print("\nReferences to update/remove in screens:")
        for sf, _, _, n_rep, n_rem in screens_to_update:
            parts = []
            if n_rep > 0:
                parts.append(f"replace {n_rep} duplicate reference(s)")
            if n_rem > 0:
                parts.append(f"remove {n_rem} invalid reference(s)")
            print(f"  {sf.relative_to(workspace_dir)}: {', '.join(parts)}")

    print(f"\nOverall Summary:")
    print(f"  Duplicate object definitions to remove from objects.yaml: {len(duplicates_set)}")
    print(f"  Duplicate instances to replace in screens: {replaced_instances_total}")
    print(f"  Invalid object instances to remove from screens: {removed_instances_total}")

    if not args.fix:
        print("\nDry-run completed. Run with '--fix' to perform the actual cleanup.")
        return

    # Fix mode: Rewrite objects.yaml
    if duplicates_set:
        cleaned_objects = [obj for obj in objects_list if obj["id"] not in duplicates_set]
        objects_data["objects"] = cleaned_objects
        with objects_yaml_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(objects_data, f, sort_keys=False, default_flow_style=False, allow_unicode=True)
        print(f"\nUpdated {objects_yaml_path} (removed {len(duplicates_set)} duplicate definitions).")

    # Fix mode: Write back screen files
    if screens_to_update:
        for sf, screen_data, new_objects, _, _ in screens_to_update:
            screen_data["objects"] = new_objects
            with sf.open("w", encoding="utf-8") as f:
                yaml.safe_dump(screen_data, f, sort_keys=False, default_flow_style=False, allow_unicode=True)
        print(f"Updated {len(screens_to_update)} screen files.")

    print(f"\nCleanup Finished.")

if __name__ == "__main__":
    main()
