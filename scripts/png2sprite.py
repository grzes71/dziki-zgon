#!/usr/bin/env python3
"""
PNG to Sprite Studio JSON converter for witcher-atari-game.
Converts a 1-bit indexed PNG sheet into a JSON format compatible with Sprite Studio.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from PIL import Image

def convert_png_to_sprite(
    image_path: Path,
    num_frames: int,
    sprite_id: str = None,
    mirror: bool = False,
    add_mirrored: bool = False,
    invert: bool = False,
    color: int = 0,
    duration: int = 4,
    loop: bool = True
) -> dict:
    """
    Converts a 1-bit indexed PNG image into Sprite Studio project JSON.
    """
    if not image_path.is_file():
        raise FileNotFoundError(f"Input file not found: {image_path}")

    # Load image
    img = Image.open(image_path)
    
    # Ensure indexed mode or 1-bit mode
    if img.mode not in ("P", "1"):
        img = img.convert("1")

    width, height = img.size

    if height % num_frames != 0:
        raise ValueError(
            f"Image height ({height}) must be divisible by the number of frames ({num_frames})."
        )

    frame_height = height // num_frames

    # Determine sprite ID if not provided
    if not sprite_id:
        sprite_id = image_path.stem.upper().replace(".", "_").replace("-", "_")

    def extract_frames(do_mirror: bool) -> list:
        frames_list = []
        for f_idx in range(num_frames):
            frame_pixels = []
            y_start = f_idx * frame_height
            for y in range(y_start, y_start + frame_height):
                row_chars = []
                for x in range(width):
                    pixel_val = img.getpixel((x, y))
                    # Check if pixel value represents foreground or background
                    # Non-zero means foreground by default (1)
                    is_fg = bool(pixel_val)
                    if invert:
                        is_fg = not is_fg
                    row_chars.append("1" if is_fg else "0")
                
                row_str = "".join(row_chars)
                if do_mirror:
                    row_str = row_str[::-1]
                frame_pixels.append(row_str)
            frames_list.append({"pixels": frame_pixels})
        return frames_list

    sprites = []

    # If add_mirrored is True, we generate two sprites: original and mirrored
    # If add_mirrored is False and mirror is True, we generate just the mirrored sprite
    if add_mirrored:
        # Original sprite
        sprites.append({
            "id": sprite_id,
            "width": width,
            "height": frame_height,
            "color": color,
            "animation": {
                "frame_duration": duration,
                "loop": loop
            },
            "frames": extract_frames(do_mirror=False)
        })
        # Mirrored sprite
        sprites.append({
            "id": f"{sprite_id}_MIRRORED",
            "width": width,
            "height": frame_height,
            "color": color,
            "animation": {
                "frame_duration": duration,
                "loop": loop
            },
            "frames": extract_frames(do_mirror=True)
        })
    else:
        # Single sprite (either mirrored or not)
        sprites.append({
            "id": sprite_id,
            "width": width,
            "height": frame_height,
            "color": color,
            "animation": {
                "frame_duration": duration,
                "loop": loop
            },
            "frames": extract_frames(do_mirror=mirror)
        })

    return {
        "version": 1,
        "sprites": sprites
    }

def main():
    parser = argparse.ArgumentParser(
        description="Convert a 1-bit indexed PNG image to Sprite Studio JSON format."
    )
    parser.add_argument("-i", "--input", required=True, type=Path, help="Path to input PNG image")
    parser.add_argument("-n", "--frames", required=True, type=int, help="Number of frames in the sheet")
    parser.add_argument("-o", "--output", type=Path, help="Path to output JSON file (defaults to <input>.sprite.json)")
    parser.add_argument("--id", type=str, help="Sprite ID (defaults to uppercase input filename)")
    parser.add_argument("--mirror", action="store_true", help="Mirror the sprite frames horizontally")
    parser.add_argument("--add-mirrored", action="store_true", help="Include both original and horizontally mirrored sprites in the JSON")
    parser.add_argument("--invert", action="store_true", help="Invert binary pixel colors (0 -> 1, 1 -> 0)")
    parser.add_argument("--color", type=int, default=0, help="Color attribute in JSON (default: 0)")
    parser.add_argument("--duration", type=int, default=4, help="Frame duration (default: 4)")
    parser.add_argument("--no-loop", action="store_false", dest="loop", help="Disable animation loop")

    args = parser.parse_args()

    try:
        sprite_data = convert_png_to_sprite(
            image_path=args.input,
            num_frames=args.frames,
            sprite_id=args.id,
            mirror=args.mirror,
            add_mirrored=args.add_mirrored,
            invert=args.invert,
            color=args.color,
            duration=args.duration,
            loop=args.loop
        )
    except Exception as e:
        print(f"Error during conversion: {e}", file=sys.stderr)
        sys.exit(1)

    output_path = args.output
    if not output_path:
        output_path = args.input.with_name(f"{args.input.stem}.sprite.json")

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(sprite_data, f, indent=2)
        print(f"Successfully wrote sprite JSON to {output_path}")
    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
