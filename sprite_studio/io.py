import json
import os
import tempfile
from pathlib import Path
from dataclasses import asdict
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
        for f_data in s_data.get("frames", []):
            frames.append(Frame(pixels=f_data.get("pixels", [])))
            
        sprite = Sprite(
            id=s_data.get("id", "UNKNOWN"),
            width=s_data.get("width", 8),
            height=s_data.get("height", 24),
            color=s_data.get("color", 0),
            animation=animation,
            frames=frames
        )
        project.sprites.append(sprite)
        
    return project

def save_project(path: Path, project: Project) -> bool:
    data = {
        "version": project.version,
        "sprites": []
    }
    
    for sprite in project.sprites:
        s_dict = {
            "id": sprite.id,
            "width": sprite.width,
            "height": sprite.height,
            "color": sprite.color,
            "animation": {
                "frame_duration": sprite.animation.frame_duration,
                "loop": sprite.animation.loop
            },
            "frames": [
                {"pixels": frame.pixels} for frame in sprite.frames
            ]
        }
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
