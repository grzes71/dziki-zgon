import re
from typing import List
from sprite_studio.models import Project

def validate_project(project: Project) -> List[str]:
    errors = []
    
    if project.version != 1:
        errors.append(f"Root: version must be 1, got {project.version}")
        
    seen_ids = set()
    id_regex = re.compile(r"^[A-Z0-9_]{1,64}$")
    
    for s_idx, sprite in enumerate(project.sprites):
        path = f"sprites[{s_idx}]"
        
        if not id_regex.match(sprite.id):
            errors.append(f"{path}: invalid_sprite_id '{sprite.id}'")
            
        if sprite.id in seen_ids:
            errors.append(f"{path}: duplicate_sprite_id '{sprite.id}'")
        seen_ids.add(sprite.id)
        
        if sprite.width != 8:
            errors.append(f"{path}: invalid_width (must be 8, got {sprite.width})")
            
        if not (1 <= sprite.height <= 256):
            errors.append(f"{path}: invalid_height (must be 1..256, got {sprite.height})")
            
        if not (0 <= sprite.color <= 255):
            errors.append(f"{path}: invalid_color (must be 0..255, got {sprite.color})")
            
        if not (1 <= sprite.animation.frame_duration <= 255):
            errors.append(f"{path}.animation: invalid_animation frame_duration (must be 1..255)")
            
        if len(sprite.frames) < 1:
            errors.append(f"{path}.frames: invalid_frame_count (must be >= 1)")
            
        for f_idx, frame in enumerate(sprite.frames):
            f_path = f"{path}.frames[{f_idx}]"
            
            if len(frame.pixels) != sprite.height:
                errors.append(f"{f_path}: invalid_frame_data row count (expected {sprite.height}, got {len(frame.pixels)})")
                
            for r_idx, row in enumerate(frame.pixels):
                if len(row) != 8:
                    errors.append(f"{f_path}.pixels[{r_idx}]: invalid_frame_data row length (expected 8, got {len(row)})")
                if not all(c in ('0', '1') for c in row):
                    errors.append(f"{f_path}.pixels[{r_idx}]: invalid_frame_data invalid chars (allowed '0', '1')")
                    
    return errors
