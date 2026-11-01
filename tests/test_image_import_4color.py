#!/usr/bin/env python3
"""Unit tests for 2-color and 4-color image import and thresholding."""

from pathlib import Path
from PIL import Image
import pytest

from sprite_studio.image_import import (
    detect_image_color_mode,
    convert_frame_to_pixels,
    import_raster_frames,
)

def test_detect_image_color_mode_2color_indexed(tmp_path: Path):
    path = tmp_path / "img_2c.png"
    img = Image.new("P", (8, 16), 0)
    palette = [0, 0, 0,  255, 255, 255] + [0] * (768 - 6)
    img.putpalette(palette)
    img.putdata([0, 1] * 64)
    img.save(path)

    mode, desc = detect_image_color_mode(img)
    assert mode == 2
    assert "2 colors" in desc

def test_detect_image_color_mode_4color_indexed(tmp_path: Path):
    path = tmp_path / "img_4c.png"
    img = Image.new("P", (8, 16), 0)
    palette = [
        0, 0, 0,
        255, 0, 0,
        0, 255, 0,
        0, 0, 255
    ] + [0] * (768 - 12)
    img.putpalette(palette)
    img.putdata([0, 1, 2, 3] * 32)
    img.save(path)

    mode, desc = detect_image_color_mode(img)
    assert mode == 4
    assert "4 colors" in desc

def test_convert_frame_to_pixels_exact_indexed_4color():
    img = Image.new("P", (8, 2), 0)
    palette = [
        0, 0, 0,
        255, 0, 0,
        0, 255, 0,
        0, 0, 255
    ] + [0] * (768 - 12)
    img.putpalette(palette)
    # Row 0: 0, 1, 2, 3, 0, 1, 2, 3
    # Row 1: 3, 2, 1, 0, 3, 2, 1, 0
    img.putdata([0, 1, 2, 3, 0, 1, 2, 3, 3, 2, 1, 0, 3, 2, 1, 0])

    pixels = convert_frame_to_pixels(
        frame_image=img,
        target_width=8,
        target_height=2,
        color_mode=4,
    )
    assert pixels == ["01230123", "32103210"]

def test_convert_frame_to_pixels_exact_indexed_2color():
    img = Image.new("P", (8, 2), 0)
    palette = [0, 0, 0,  255, 255, 255] + [0] * (768 - 6)
    img.putpalette(palette)
    img.putdata([0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0])

    pixels = convert_frame_to_pixels(
        frame_image=img,
        target_width=8,
        target_height=2,
        color_mode=2,
    )
    assert pixels == ["01010101", "10101010"]

def test_convert_frame_to_pixels_continuous_4color():
    # 8x4 image with 4 horizontal bands of brightness (0, 80, 160, 240)
    img = Image.new("L", (8, 4), 0)
    data = []
    data.extend([0] * 8)    # Level 0 (< t1)
    data.extend([80] * 8)   # Level 1 (>= t1, < t2)
    data.extend([160] * 8)  # Level 2 (>= t2, < t3)
    data.extend([240] * 8)  # Level 3 (>= t3)
    img.putdata(data)

    pixels = convert_frame_to_pixels(
        frame_image=img,
        target_width=8,
        target_height=4,
        color_mode=4,
        threshold=50.0,
    )
    assert pixels[0] == "00000000"
    assert pixels[1] == "11111111"
    assert pixels[2] == "22222222"
    assert pixels[3] == "33333333"

def test_import_raster_frames_auto_detects_4color(tmp_path: Path):
    path = tmp_path / "sheet_4c.png"
    # 8x16 image with 2 frames of 8x8
    img = Image.new("P", (8, 16), 0)
    palette = [0, 0, 0,  255, 0, 0,  0, 255, 0,  255, 255, 0] + [0] * (768 - 12)
    img.putpalette(palette)
    img.putdata([0, 1, 2, 3] * 32)
    img.save(path)

    frames = import_raster_frames(
        path=path,
        frame_count=2,
        direction="vertical",
        target_height=8,
        color_mode=None, # auto-detect
    )
    assert len(frames) == 2
    # Verify pixels contain values 0..3
    assert any('2' in row or '3' in row for row in frames[0].pixels)

