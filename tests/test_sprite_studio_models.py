#!/usr/bin/env python3
"""Unit tests for Sprite Studio data models and layer combining/splitting."""

import pytest
from sprite_studio.models import Sprite, Frame, Animation, Project
from sprite_studio.palette import mix_atari_colors, get_atari_rgb

def test_sprite_default_2color():
    sprite = Sprite(id="TEST_2C", height=4)
    assert not sprite.is_4color()
    assert sprite.color_mode == 2
    assert sprite.color2 == 0

def test_sprite_4color_properties():
    sprite = Sprite(
        id="TEST_4C",
        height=2,
        color=0x24,
        color_mode=4,
        color2=0x88,
        frames=[
            Frame(pixels=["01230123", "32103210"])
        ]
    )
    assert sprite.is_4color()
    assert sprite.color == 0x24
    assert sprite.color2 == 0x88
    # Hardware mix
    assert sprite.get_overlap_color() == (0x24 | 0x88)

def test_layer_pixel_extraction():
    # Frame has row "01230123"
    # P0 gets '1' where char is '1' or '3' -> "01010101"
    # P1 gets '1' where char is '2' or '3' -> "00110011"
    sprite = Sprite(
        id="HERO",
        height=1,
        color_mode=4,
        frames=[Frame(pixels=["01230123"])]
    )

    p0 = sprite.get_layer_pixels(0, layer=0)
    p1 = sprite.get_layer_pixels(0, layer=1)

    assert p0 == ["01010101"]
    assert p1 == ["00110011"]

def test_combine_layer_frames_roundtrip():
    p0_frames = [Frame(pixels=["01010101", "11001100"])]
    p1_frames = [Frame(pixels=["00110011", "10101010"])]

    combined = Sprite.combine_layer_frames(p0_frames, p1_frames)
    assert len(combined) == 1
    # row 0: P0="01010101", P1="00110011"
    # b0: 0, 1, 0, 1, 0, 1, 0, 1
    # b1: 0, 0, 1, 1, 0, 0, 1, 1
    # val: (b1<<1)|b0 -> 0, 1, 2, 3, 0, 1, 2, 3
    assert combined[0].pixels[0] == "01230123"

    # row 1: P0="11001100", P1="10101010"
    # x=0: P0=1, P1=1 -> 3
    # x=1: P0=1, P1=0 -> 1
    # x=2: P0=0, P1=1 -> 2
    # x=3: P0=0, P1=0 -> 0
    # x=4: P0=1, P1=1 -> 3
    # x=5: P0=1, P1=0 -> 1
    # x=6: P0=0, P1=1 -> 2
    # x=7: P0=0, P1=0 -> 0
    assert combined[0].pixels[1] == "31203120"

    # Now verify splitting combined frames matches original p0 and p1!
    spr = Sprite(id="COMB", color_mode=4, frames=combined)
    assert spr.get_layer_pixels(0, layer=0) == p0_frames[0].pixels
    assert spr.get_layer_pixels(0, layer=1) == p1_frames[0].pixels

def test_palette_hardware_mix():
    c1 = 0x24  # Hue 2, Lum 4
    c2 = 0x88  # Hue 8, Lum 8
    mix = mix_atari_colors(c1, c2)
    assert mix == (c1 | c2)

    # Valid RGB lookup
    rgb = get_atari_rgb(mix)
    assert rgb.isValid()

