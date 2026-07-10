import sys
from pathlib import Path
from world_studio.project_manager import ProjectManager

pm = ProjectManager()
pm.load_project(Path("world"))

def render_ascii(screen_def):
    grid = [["." for _ in range(40)] for _ in range(12)]
    for obj_inst in screen_def.objects:
        obj_def = next((o for o in pm.objects if o.id == obj_inst.object), None)
        if obj_def:
            for dy in range(obj_def.size.height):
                for dx in range(obj_def.size.width):
                    y = obj_inst.y + dy
                    x = obj_inst.x + dx
                    if 0 <= x < 40 and 0 <= y < 12:
                        grid[y][x] = obj_def.id[0] # First letter of object
    return "\n".join("".join(row) for row in grid)

with open("screens_ascii.txt", "w") as f:
    f.write("CROSSROADS:\n")
    f.write(render_ascii(pm.screens["WHITE_FIELD"]["CROSSROADS"]))
    f.write("\n\nCHURCH:\n")
    f.write(render_ascii(pm.screens["WHITE_FIELD"]["CHURCH"]))
    f.write("\n\nTAVERN:\n")
    f.write(render_ascii(pm.screens["WHITE_FIELD"]["TAVERN"]))

print("Done")
