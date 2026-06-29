#!/usr/bin/env python3
"""Unit tests for the fnt2png converter tool."""

import subprocess
import sys
from pathlib import Path
import pytest
from PIL import Image

from scripts.fnt2png import (
    ANTICMode5Decoder,
    ConverterConfig,
    MissingInputFileError,
    UnsupportedFileSizeError,
    InvalidOutputPathError,
    InvalidRGBValueError,
    InvalidAtariColorNumberError,
)


def create_mock_fnt(path: Path, size: int = 1024, fill_byte: int = 0) -> None:
    """Helper to create a mock .fnt binary file."""
    data = bytes([fill_byte] * size)
    path.write_bytes(data)


def test_valid_conversion(tmp_path: Path) -> None:
    """Test that a valid 1024-byte .fnt converts successfully with expected dimensions."""
    input_fnt = tmp_path / "valid.fnt"
    output_png = tmp_path / "valid.png"

    # Fill with 27 (0b00011011) so each row contains pixel sequence: 0, 1, 2, 3
    create_mock_fnt(input_fnt, size=1024, fill_byte=27)

    config = ConverterConfig(
        input_path=input_fnt,
        output_path=output_png,
        palette_name="",
        custom_colors="",
        verbose=True,
    )
    decoder = ANTICMode5Decoder(config)
    img = decoder.decode_and_generate()

    # Verify geometry
    assert img.width == 128
    assert img.height == 32
    assert img.mode == "P"

    # Verify pixel decoding
    # First character, row 0 (x=0..3, y=0) should contain palette indexes 0, 1, 2, 3
    assert img.getpixel((0, 0)) == 0
    assert img.getpixel((1, 0)) == 1
    assert img.getpixel((2, 0)) == 2
    assert img.getpixel((3, 0)) == 3

    # Save and verify
    decoder.write_output(img)
    assert output_png.is_file()

    # Load saved file and verify properties
    with Image.open(output_png) as saved_img:
        assert saved_img.width == 128
        assert saved_img.height == 32
        assert saved_img.mode == "P"
        # Check palette exists and has expected default entries
        palette = saved_img.getpalette()
        assert palette is not None
        # Check first 4 colors: index 0 (0,0,0), index 1 (255,255,255), index 2 (0,170,0), index 3 (170,85,0)
        assert palette[0:3] == [0, 0, 0]
        assert palette[3:6] == [255, 255, 255]
        assert palette[6:9] == [0, 170, 0]
        assert palette[9:12] == [170, 85, 0]


def test_invalid_file_size(tmp_path: Path) -> None:
    """Test that file sizes other than 1024 bytes are rejected."""
    input_fnt = tmp_path / "invalid_size.fnt"
    output_png = tmp_path / "output.png"

    config = ConverterConfig(
        input_path=input_fnt,
        output_path=output_png,
        palette_name="",
        custom_colors="",
        verbose=False,
    )
    decoder = ANTICMode5Decoder(config)

    # 1023 bytes
    create_mock_fnt(input_fnt, size=1023)
    with pytest.raises(UnsupportedFileSizeError):
        decoder.decode_and_generate()

    # 1025 bytes
    create_mock_fnt(input_fnt, size=1025)
    with pytest.raises(UnsupportedFileSizeError):
        decoder.decode_and_generate()


def test_missing_input_file(tmp_path: Path) -> None:
    """Test that a missing input file is rejected."""
    non_existent = tmp_path / "missing.fnt"
    output_png = tmp_path / "output.png"

    config = ConverterConfig(
        input_path=non_existent,
        output_path=output_png,
        palette_name="",
        custom_colors="",
        verbose=False,
    )
    decoder = ANTICMode5Decoder(config)
    with pytest.raises(MissingInputFileError):
        decoder.decode_and_generate()


def test_invalid_rgb_palette(tmp_path: Path) -> None:
    """Test validation of custom RGB colors."""
    input_fnt = tmp_path / "valid.fnt"
    output_png = tmp_path / "output.png"
    create_mock_fnt(input_fnt)

    # Too few colors (3 instead of 4)
    decoder = ANTICMode5Decoder(
        ConverterConfig(
            input_path=input_fnt,
            output_path=output_png,
            palette_name="",
            custom_colors="#111111,#222222,#333333",
            verbose=False,
        )
    )
    with pytest.raises(InvalidRGBValueError):
        decoder.decode_and_generate()

    # Malformed hex string
    decoder = ANTICMode5Decoder(
        ConverterConfig(
            input_path=input_fnt,
            output_path=output_png,
            palette_name="",
            custom_colors="#111111,#222222,#333333,#444ZZZ",
            verbose=False,
        )
    )
    with pytest.raises(InvalidRGBValueError):
        decoder.decode_and_generate()


def test_invalid_atari_color_numbers(tmp_path: Path) -> None:
    """Test validation of Atari color index parameters."""
    input_fnt = tmp_path / "valid.fnt"
    output_png = tmp_path / "output.png"
    create_mock_fnt(input_fnt)

    # Index out of bounds (256)
    decoder = ANTICMode5Decoder(
        ConverterConfig(
            input_path=input_fnt,
            output_path=output_png,
            palette_name="",
            custom_colors="0,15,256,36",
            verbose=False,
        )
    )
    with pytest.raises(InvalidAtariColorNumberError):
        decoder.decode_and_generate()

    # Non-integer index
    decoder = ANTICMode5Decoder(
        ConverterConfig(
            input_path=input_fnt,
            output_path=output_png,
            palette_name="",
            custom_colors="0,abc,202,36",
            verbose=False,
        )
    )
    with pytest.raises(InvalidAtariColorNumberError):
        decoder.decode_and_generate()


def test_predefined_atari_palette(tmp_path: Path) -> None:
    """Test predefined 'atari' palette option (uses 0, 15, 202, 36)."""
    input_fnt = tmp_path / "valid.fnt"
    output_png = tmp_path / "output.png"
    create_mock_fnt(input_fnt)

    decoder = ANTICMode5Decoder(
        ConverterConfig(
            input_path=input_fnt,
            output_path=output_png,
            palette_name="atari",
            custom_colors="",
            verbose=False,
        )
    )
    img = decoder.decode_and_generate()
    palette = img.getpalette()
    assert palette is not None

    # Atari colors:
    # 0   -> 0x323132 -> [50, 49, 50]
    # 15  -> 0xFFFFFF -> [255, 255, 255]
    # 202 -> 0xA8DF4D -> [168, 223, 77]
    # 36  -> 0x9E5D22 -> [158, 93, 34]
    assert palette[0:3] == [50, 49, 50]
    assert palette[3:6] == [255, 255, 255]
    assert palette[6:9] == [168, 223, 77]
    assert palette[9:12] == [158, 93, 34]


def test_custom_rgb_palette(tmp_path: Path) -> None:
    """Test that a custom RGB palette is embedded correctly in the output PNG."""
    input_fnt = tmp_path / "valid.fnt"
    output_png = tmp_path / "output.png"
    create_mock_fnt(input_fnt)

    decoder = ANTICMode5Decoder(
        ConverterConfig(
            input_path=input_fnt,
            output_path=output_png,
            palette_name="",
            custom_colors="#111111,#222222,#333333,#444444",
            verbose=False,
        )
    )
    img = decoder.decode_and_generate()
    palette = img.getpalette()
    assert palette is not None
    assert palette[0:3] == [0x11, 0x11, 0x11]
    assert palette[3:6] == [0x22, 0x22, 0x22]
    assert palette[6:9] == [0x33, 0x33, 0x33]
    assert palette[9:12] == [0x44, 0x44, 0x44]


def test_custom_atari_palette(tmp_path: Path) -> None:
    """Test that custom Atari color codes map correctly to RGB palette."""
    input_fnt = tmp_path / "valid.fnt"
    output_png = tmp_path / "output.png"
    create_mock_fnt(input_fnt)

    decoder = ANTICMode5Decoder(
        ConverterConfig(
            input_path=input_fnt,
            output_path=output_png,
            palette_name="",
            custom_colors="0,15,202,36",
            verbose=False,
        )
    )
    img = decoder.decode_and_generate()
    palette = img.getpalette()
    assert palette is not None
    assert palette[0:3] == [50, 49, 50]
    assert palette[3:6] == [255, 255, 255]
    assert palette[6:9] == [168, 223, 77]
    assert palette[9:12] == [158, 93, 34]


def test_invalid_output_path(tmp_path: Path) -> None:
    """Test that write errors raise a descriptive exception."""
    input_fnt = tmp_path / "valid.fnt"
    blocked_dir = tmp_path / "blocked_dir"
    blocked_dir.write_text("Blocked file")
    invalid_output = blocked_dir / "output.png"

    create_mock_fnt(input_fnt)
    decoder = ANTICMode5Decoder(
        ConverterConfig(
            input_path=input_fnt,
            output_path=invalid_output,
            palette_name="",
            custom_colors="",
            verbose=False,
        )
    )
    img = decoder.decode_and_generate()
    with pytest.raises(InvalidOutputPathError):
        decoder.write_output(img)


def test_cli_execution(tmp_path: Path) -> None:
    """Test command-line execution by running the script in a subprocess."""
    input_fnt = tmp_path / "cli_input.fnt"
    output_png = tmp_path / "cli_output.png"

    create_mock_fnt(input_fnt)

    # Run scripts/fnt2png.py as a subprocess
    result = subprocess.run(
        [
            sys.executable,
            "scripts/fnt2png.py",
            "--input",
            str(input_fnt),
            "--output",
            str(output_png),
            "--palette",
            "atari",
            "--verbose",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert output_png.is_file()
    with Image.open(output_png) as img:
        assert img.width == 128
        assert img.height == 32
