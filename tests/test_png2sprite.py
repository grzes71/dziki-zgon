#!/usr/bin/env python3
"""Unit tests for the png2sprite converter tool."""

import json
from pathlib import Path
import pytest
from PIL import Image

from scripts.png2sprite import convert_png_to_sprite

def create_mock_png(
    path: Path,
    width: int = 8,
    height: int = 16,
    mode: str = "P",
    pixels: list = None
) -> None:
    """Helper function to create a mock PNG with specified properties."""
    img = Image.new(mode, (width, height), 0)

    if mode == "P":
        # Palette entries are RGB triples: 0 is Black, 1 is White
        palette = [
            0, 0, 0,        # 0
            255, 255, 255,  # 1
        ]
        palette += [0] * (768 - len(palette))
        img.putpalette(palette)

    if pixels:
        img.putdata(pixels)
    else:
        # Default pattern: alternate lines of 0s and 1s
        default_pixels = []
        for y in range(height):
            val = y % 2
            default_pixels.extend([val] * width)
        img.putdata(default_pixels)

    img.save(path, format="PNG")

def test_valid_conversion(tmp_path: Path) -> None:
    """Test that a valid 1-bit indexed PNG converts successfully."""
    input_png = tmp_path / "valid.png"
    
    # 8x16 image, let's use 2 frames -> height 8 per frame
    # Frame 0: rows 0-7, Frame 1: rows 8-15
    # Let's specify exact pixels to test
    # Frame 0 row 0: 01010000
    # Frame 1 row 0: 10100000
    pixels = []
    # Frame 0 (first 8 rows)
    for y in range(8):
        if y == 0:
            pixels.extend([0, 1, 0, 1, 0, 0, 0, 0])
        else:
            pixels.extend([0] * 8)
    # Frame 1 (second 8 rows)
    for y in range(8):
        if y == 0:
            pixels.extend([1, 0, 1, 0, 0, 0, 0, 0])
        else:
            pixels.extend([0] * 8)

    create_mock_png(input_png, width=8, height=16, pixels=pixels)

    result = convert_png_to_sprite(image_path=input_png, num_frames=2, sprite_id="TEST_SPRITE")

    assert result["version"] == 1
    assert len(result["sprites"]) == 1
    sprite = result["sprites"][0]
    
    assert sprite["id"] == "TEST_SPRITE"
    assert sprite["width"] == 8
    assert sprite["height"] == 8
    assert sprite["color"] == 0
    assert len(sprite["frames"]) == 2
    
    # Check Frame 0 pixels
    assert sprite["frames"][0]["pixels"][0] == "01010000"
    # Check Frame 1 pixels
    assert sprite["frames"][1]["pixels"][0] == "10100000"

def test_invalid_dimensions(tmp_path: Path) -> None:
    """Test that height not divisible by num_frames raises ValueError."""
    input_png = tmp_path / "invalid_dim.png"
    create_mock_png(input_png, width=8, height=15) # 15 height

    with pytest.raises(ValueError) as excinfo:
        convert_png_to_sprite(image_path=input_png, num_frames=2)
    assert "must be divisible by the number of frames" in str(excinfo.value)

def test_mirroring(tmp_path: Path) -> None:
    """Test horizontal mirroring option."""
    input_png = tmp_path / "mirror.png"
    pixels = []
    # Frame 0 row 0: 01010000 -> mirrored should be 00001010
    pixels.extend([0, 1, 0, 1, 0, 0, 0, 0])
    for _ in range(7):
        pixels.extend([0] * 8)

    create_mock_png(input_png, width=8, height=8, pixels=pixels)

    # Convert with mirror=True
    result = convert_png_to_sprite(image_path=input_png, num_frames=1, mirror=True)
    sprite = result["sprites"][0]
    assert sprite["frames"][0]["pixels"][0] == "00001010"

def test_add_mirrored(tmp_path: Path) -> None:
    """Test generating both original and mirrored sprites."""
    input_png = tmp_path / "both.png"
    pixels = []
    # Frame 0 row 0: 01010000 -> mirrored should be 00001010
    pixels.extend([0, 1, 0, 1, 0, 0, 0, 0])
    for _ in range(7):
        pixels.extend([0] * 8)

    create_mock_png(input_png, width=8, height=8, pixels=pixels)

    result = convert_png_to_sprite(image_path=input_png, num_frames=1, sprite_id="HERO", add_mirrored=True)
    
    assert len(result["sprites"]) == 2
    
    # First sprite: original
    sprite_orig = result["sprites"][0]
    assert sprite_orig["id"] == "HERO"
    assert sprite_orig["frames"][0]["pixels"][0] == "01010000"

    # Second sprite: mirrored
    sprite_mirrored = result["sprites"][1]
    assert sprite_mirrored["id"] == "HERO_MIRRORED"
    assert sprite_mirrored["frames"][0]["pixels"][0] == "00001010"

def test_inversion(tmp_path: Path) -> None:
    """Test pixel color inversion."""
    input_png = tmp_path / "invert.png"
    pixels = []
    # Row 0: 01010000 -> inverted should be 10101111
    pixels.extend([0, 1, 0, 1, 0, 0, 0, 0])
    for _ in range(7):
        pixels.extend([0] * 8)

    create_mock_png(input_png, width=8, height=8, pixels=pixels)

    result = convert_png_to_sprite(image_path=input_png, num_frames=1, invert=True)
    sprite = result["sprites"][0]
    assert sprite["frames"][0]["pixels"][0] == "10101111"

def test_non_indexed_conversion(tmp_path: Path) -> None:
    """Test that RGB/Grayscale images are auto-converted gracefully."""
    input_png = tmp_path / "rgb.png"
    # Create an RGB image
    img = Image.new("RGB", (8, 8), (0, 0, 0))
    # Put some white pixels
    img.putpixel((1, 0), (255, 255, 255))
    img.putpixel((3, 0), (255, 255, 255))
    img.save(input_png, format="PNG")

    result = convert_png_to_sprite(image_path=input_png, num_frames=1)
    sprite = result["sprites"][0]
    # Check that it converted correctly and pixel values got mapped to 1
    assert sprite["frames"][0]["pixels"][0] == "01010000"
