from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict
from sprite_studio.models import Project, Sprite, Animation, Frame

def load_project(path: Path) -> Project:
    if not path.exists():
        raise FileNotFoundError(f"Project not found at {path}")
        
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    project = Project(version=data.get("version", 1))
    
    for s_data in data.get("sprites", []):
        anim_data = s_data.get("animation", {})
        animation = Animation(
            frame_duration=anim_data.get("frame_duration", 4),
            loop=anim_data.get("loop", True)
        )
        
        frames = []
        has_multi_color_pixels = False
        for f_data in s_data.get("frames", []):
            pixels = f_data.get("pixels", [])
            for row in pixels:
                if any(c in ('2', '3') for c in row):
                    has_multi_color_pixels = True
            frames.append(Frame(pixels=pixels))
            
        raw_id = s_data.get("id", 1)
        # Preserve int if numeric, otherwise preserve string
        if isinstance(raw_id, int) and not isinstance(raw_id, bool):
            sprite_id = raw_id
        elif isinstance(raw_id, str) and raw_id.isdigit():
            sprite_id = int(raw_id)
        else:
            sprite_id = str(raw_id)

        description = str(s_data.get("description", ""))
        
        # Color mode: explicit or auto-detected if frame contains 2 or 3
        raw_mode = s_data.get("color_mode")
        if raw_mode is not None:
            color_mode = int(raw_mode)
        elif has_multi_color_pixels:
            color_mode = 4
        else:
            color_mode = 2

        color2 = int(s_data.get("color2", 0))

        sprite = Sprite(
            id=sprite_id,
            description=description,
            width=s_data.get("width", 8),
            height=s_data.get("height", 24),
            color=s_data.get("color", 0),
            color_mode=color_mode,
            color2=color2,
            animation=animation,
            frames=frames
        )
        project.sprites.append(sprite)
        
    return project

def save_project(path: Path, project: Project) -> bool:
    data: Dict[str, Any] = {
        "version": project.version,
        "sprites": []
    }
    
    for sprite in project.sprites:
        s_dict: Dict[str, Any] = {
            "id": sprite.id,
            "description": str(sprite.description),
            "width": sprite.width,
            "height": sprite.height,
            "color": sprite.color,
        }
        if sprite.color_mode == 4:
            s_dict["color_mode"] = 4
            s_dict["color2"] = sprite.color2

        s_dict["animation"] = {
            "frame_duration": sprite.animation.frame_duration,
            "loop": sprite.animation.loop
        }
        s_dict["frames"] = [
            {"pixels": frame.pixels} for frame in sprite.frames
        ]
        data["sprites"].append(s_dict)
        
    try:
        # Atomic save
        fd, temp_path = tempfile.mkstemp(dir=path.parent, prefix=".", suffix=".tmp")
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            
        os.replace(temp_path, path)
        return True
    except Exception as e:
        print(f"Error saving project: {e}")
        return False
