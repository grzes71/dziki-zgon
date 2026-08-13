import yaml
from pathlib import Path

def main():
    workspace_dir = Path(__file__).resolve().parent.parent
    world_dir = workspace_dir / "world"
    objects_yaml_path = world_dir / "objects.yaml"
    
    if not objects_yaml_path.exists():
        print(f"Error: {objects_yaml_path} does not exist.")
        return
        
    with objects_yaml_path.open("r", encoding="utf-8") as f:
        objects_data = yaml.safe_load(f) or {}
        
    objects_dict = {}
    for obj in objects_data.get("objects", []):
        objects_dict[obj["id"]] = {
            "width": obj.get("size", {}).get("width", 1),
            "height": obj.get("size", {}).get("height", 1),
            "blocking": obj.get("flags", {}).get("blocking", False),
            "interactive": obj.get("flags", {}).get("interactive", False),
            "secret": obj.get("flags", {}).get("secret", False)
        }
        
    screen_files = list(world_dir.glob("**/screens/*.yaml"))
    print(f"Found {len(screen_files)} screen files to process.")
    
    total_original_objects = 0
    total_final_objects = 0
    total_deleted_objects = 0
    
    for screen_file in screen_files:
        with screen_file.open("r", encoding="utf-8") as f:
            screen_data = yaml.safe_load(f) or {}
            
        screen_id = screen_data.get("id", screen_file.stem)
        objects = screen_data.get("objects", [])
        total_original_objects += len(objects)
        
        final_objects = []
        for inst in objects:
            obj_id = inst.get("object")
            w = 1
            h = 1
            interactive = False
            secret = False
            if obj_id in objects_dict:
                w = objects_dict[obj_id]["width"]
                h = objects_dict[obj_id]["height"]
                interactive = objects_dict[obj_id]["interactive"]
                secret = objects_dict[obj_id]["secret"]
                
            is_critical = (
                inst.get("type") is not None or
                inst.get("target_region") is not None or
                inst.get("conditions_met") is not None or
                inst.get("conditions_unmet") is not None or
                inst.get("items_required") is not None or
                inst.get("items_provided") is not None or
                interactive or
                secret
            )
            
            if is_critical:
                # Critical objects are never deleted, even if they have odd coordinates
                final_objects.append(inst)
            else:
                # Non-critical decorations: expand if they repeat, and filter out odd coordinates
                rx = inst.get("repeat-x", 1)
                ry = inst.get("repeat-y", 1)
                bx = inst.get("x", 0)
                by = inst.get("y", 0)
                
                for y_idx in range(ry):
                    for x_idx in range(rx):
                        curr_x = bx + x_idx * w
                        curr_y = by + y_idx * h
                        
                        # Delete if x or y is odd
                        if curr_x % 2 != 0 or curr_y % 2 != 0:
                            total_deleted_objects += 1
                        else:
                            new_inst = dict(inst)
                            new_inst.pop("repeat-x", None)
                            new_inst.pop("repeat-y", None)
                            new_inst["x"] = curr_x
                            new_inst["y"] = curr_y
                            final_objects.append(new_inst)
                            
        screen_data["objects"] = final_objects
        total_final_objects += len(final_objects)
        
        with screen_file.open("w", encoding="utf-8") as f:
            yaml.safe_dump(screen_data, f, sort_keys=False, default_flow_style=False, allow_unicode=True)
            
    print("Cleanup Summary:")
    print(f"Total screens processed: {len(screen_files)}")
    print(f"Total original objects listed: {total_original_objects}")
    print(f"Total final objects saved: {total_final_objects}")
    print(f"Total objects deleted (odd coordinates): {total_deleted_objects}")

if __name__ == "__main__":
    main()
