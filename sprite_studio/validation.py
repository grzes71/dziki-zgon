from __future__ import annotations

import re
from typing import List
from sprite_studio.models import Project

ID_STR_REGEX = re.compile(r"^[A-Za-z0-9_]{1,64}$")

def validate_project(project: Project) -> List[str]:
    errors: List[str] = []
    
    if project.version != 1:
        errors.append(f"Root: version must be 1, got {project.version}")
        
    seen_ids = set()
    for s_idx, sprite in enumerate(project.sprites):
        path = f"sprites[{s_idx}]"
        
        # ID validation (support int 1..255 or string matching regex)
        if isinstance(sprite.id, bool):
            errors.append(f"{path}: invalid_sprite_id (cannot be boolean)")
        elif isinstance(sprite.id, int):
            if not (1 <= sprite.id <= 255):
                errors.append(f"{path}: invalid_sprite_id (integer must be 1..255, got {sprite.id})")
            elif sprite.id in seen_ids:
                errors.append(f"{path}: duplicate_sprite_id '{sprite.id}'")
            else:
                seen_ids.add(sprite.id)
        elif isinstance(sprite.id, str):
            if not ID_STR_REGEX.match(sprite.id):
                errors.append(f"{path}: invalid_sprite_id (string must match ^[A-Za-z0-9_]{{1,64}}$, got '{sprite.id}')")
            elif sprite.id in seen_ids:
                errors.append(f"{path}: duplicate_sprite_id '{sprite.id}'")
            else:
                seen_ids.add(sprite.id)
        else:
            errors.append(f"{path}: invalid_sprite_id (must be integer 1..255 or string, got {type(sprite.id).__name__})")

        if not isinstance(sprite.description, str):
            errors.append(f"{path}: invalid_description (must be string, got {type(sprite.description).__name__})")
        elif len(sprite.description) > 40:
            errors.append(f"{path}: invalid_description (max 40 characters, got {len(sprite.description)})")
        
        if sprite.width != 8:
            errors.append(f"{path}: invalid_width (must be 8, got {sprite.width})")
            
        if not (1 <= sprite.height <= 256):
            errors.append(f"{path}: invalid_height (must be 1..256, got {sprite.height})")

        if sprite.color_mode not in (2, 4):
            errors.append(f"{path}: invalid_color_mode (must be 2 or 4, got {sprite.color_mode})")
            
        if not (0 <= sprite.color <= 255):
            errors.append(f"{path}: invalid_color (must be 0..255, got {sprite.color})")

        if sprite.color_mode == 4 and not (0 <= sprite.color2 <= 255):
            errors.append(f"{path}: invalid_color2 (must be 0..255, got {sprite.color2})")
            
        if not (1 <= sprite.animation.frame_duration <= 255):
            errors.append(f"{path}.animation: invalid_animation frame_duration (must be 1..255)")
            
        if len(sprite.frames) < 1:
            errors.append(f"{path}.frames: invalid_frame_count (must be >= 1)")

        allowed_chars = ('0', '1', '2', '3') if sprite.color_mode == 4 else ('0', '1')
            
        for f_idx, frame in enumerate(sprite.frames):
            f_path = f"{path}.frames[{f_idx}]"
            
            if len(frame.pixels) != sprite.height:
                errors.append(f"{f_path}: invalid_frame_data row count (expected {sprite.height}, got {len(frame.pixels)})")
                
            for r_idx, row in enumerate(frame.pixels):
                if len(row) != 8:
                    errors.append(f"{f_path}.pixels[{r_idx}]: invalid_frame_data row length (expected 8, got {len(row)})")
                if not all(c in allowed_chars for c in row):
                    chars_str = ", ".join(f"'{c}'" for c in allowed_chars)
                    errors.append(f"{f_path}.pixels[{r_idx}]: invalid_frame_data invalid chars (allowed {chars_str})")
                    
    return errors
