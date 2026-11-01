#!/usr/bin/env python3
"""Unit tests for Sprite Studio validation, JSON I/O and backward compatibility."""

from pathlib import Path
import pytest

from sprite_studio.models import Project, Sprite, Frame, Animation
from sprite_studio.validation import validate_project
from sprite_studio.io import load_project, save_project

def test_validation_valid_4color():
    project = Project(
        version=1,
        sprites=[
            Sprite(
                id="VALID_4C",
                height=2,
                color=0x12,
                color_mode=4,
                color2=0x94,
                frames=[Frame(pixels=["01230123", "00112233"])]
            )
        ]
    )
    errors = validate_project(project)
    assert errors == []

def test_validation_rejects_invalid_chars_in_2color():
    project = Project(
        version=1,
        sprites=[
            Sprite(
                id="TEST_2C",
                height=1,
                color_mode=2,
                frames=[Frame(pixels=["01010123"])]  # '2' and '3' not allowed in 2-color
            )
        ]
    )
    errors = validate_project(project)
    assert any("invalid chars" in e for e in errors)

def test_validation_rejects_invalid_chars_in_4color():
    project = Project(
        version=1,
        sprites=[
            Sprite(
                id="TEST_4C",
                height=1,
                color_mode=4,
                color2=10,
                frames=[Frame(pixels=["01234567"])]  # '4', '5', '6', '7' not allowed
            )
        ]
    )
    errors = validate_project(project)
    assert any("invalid chars" in e for e in errors)

def test_validation_rejects_invalid_color2():
    project = Project(
        version=1,
        sprites=[
            Sprite(
                id="TEST_4C",
                height=1,
                color_mode=4,
                color2=300,  # Invalid color > 255
                frames=[Frame(pixels=["01230123"])]
            )
        ]
    )
    errors = validate_project(project)
    assert any("invalid_color2" in e for e in errors)

def test_io_save_and_load_roundtrip(tmp_path: Path):
    file_path = tmp_path / "test_4c.sprite.json"
    orig_proj = Project(
        version=1,
        sprites=[
            Sprite(
                id="SPR_2C",
                height=2,
                color=10,
                color_mode=2,
                frames=[Frame(pixels=["00110011", "11001100"])]
            ),
            Sprite(
                id="SPR_4C",
                height=2,
                color=20,
                color_mode=4,
                color2=40,
                frames=[Frame(pixels=["01230123", "32103210"])]
            )
        ]
    )

    assert save_project(file_path, orig_proj) is True

    loaded_proj = load_project(file_path)
    assert len(loaded_proj.sprites) == 2

    s0 = loaded_proj.sprites[0]
    assert s0.id == "SPR_2C"
    assert s0.color_mode == 2
    assert s0.frames[0].pixels == ["00110011", "11001100"]

    s1 = loaded_proj.sprites[1]
    assert s1.id == "SPR_4C"
    assert s1.color_mode == 4
    assert s1.color == 20
    assert s1.color2 == 40
    assert s1.frames[0].pixels == ["01230123", "32103210"]

def test_backward_compatibility_with_existing_sprites():
    sprites_dir = Path("sprites")
    if not sprites_dir.exists():
        pytest.skip("sprites directory not found")

    sprite_files = list(sprites_dir.glob("*.sprite.json"))
    assert len(sprite_files) > 0, "No sprite files found in sprites/"

    for sf in sprite_files:
        proj = load_project(sf)
        assert proj.version == 1
        errors = validate_project(proj)
        assert errors == [], f"Validation failed for existing file {sf}: {errors}"

