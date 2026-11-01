#!/usr/bin/env python3
"""Unit tests for sprite2asm.py with 4-color and 2-color sprites."""

from scripts.sprite2asm import generate_asm

def test_generate_asm_2color():
    json_data = {
        "version": 1,
        "sprites": [
            {
                "id": "HERO_2C",
                "height": 2,
                "color": 0x14,
                "color_mode": 2,
                "frames": [
                    {"pixels": ["11001100", "00110011"]}
                ]
            }
        ]
    }
    asm = generate_asm(json_data, "test.sprite.json")

    assert ".def SPRITE_HERO_2C_HEIGHT = 2" in asm
    assert ".def SPRITE_HERO_2C_COLOR = 20" in asm
    assert ".def SPRITE_HERO_2C_IS_4COLOR = 0" in asm
    assert "HERO_2C_FRAME_0" in asm
    assert "dta %11001100" in asm
    assert "HERO_2C_PTRS" in asm
    assert "dta a(HERO_2C_FRAME_0)" in asm

def test_generate_asm_4color():
    json_data = {
        "version": 1,
        "sprites": [
            {
                "id": "BOSS_4C",
                "height": 2,
                "color": 0x24,
                "color2": 0x88,
                "color_mode": 4,
                "frames": [
                    {"pixels": ["01230123", "32103210"]}
                ]
            }
        ]
    }
    asm = generate_asm(json_data, "boss.sprite.json")

    assert ".def SPRITE_BOSS_4C_HEIGHT = 2" in asm
    assert ".def SPRITE_BOSS_4C_COLOR0 = 36" in asm
    assert ".def SPRITE_BOSS_4C_COLOR1 = 136" in asm
    assert f".def SPRITE_BOSS_4C_COLOR_MIX = {0x24 | 0x88}" in asm
    assert ".def SPRITE_BOSS_4C_IS_4COLOR = 1" in asm

    # Layer P0 Frame 0: pixels with '1' or '3' -> "01010101"
    assert "BOSS_4C_P0_FRAME_0" in asm
    assert "dta %01010101" in asm

    # Layer P1 Frame 0: pixels with '2' or '3' -> "00110011"
    assert "BOSS_4C_P1_FRAME_0" in asm
    assert "dta %00110011" in asm

    # Pointer tables for both layers
    assert "BOSS_4C_P0_PTRS" in asm
    assert "dta a(BOSS_4C_P0_FRAME_0)" in asm
    assert "BOSS_4C_P1_PTRS" in asm
    assert "dta a(BOSS_4C_P1_FRAME_0)" in asm
    assert "BOSS_4C_PTRS = BOSS_4C_P0_PTRS" in asm

