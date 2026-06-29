#!/usr/bin/env python3
"""Unit tests for the png2fnt converter tool."""

import subprocess
import sys
from pathlib import Path
import pytest
from PIL import Image

from scripts.png2fnt import (
    ANTICMode5Converter,
    ConverterConfig,
    MissingInputFileError,
    InvalidPNGError,
    UnsupportedDimensionsError,
    UnsupportedColorCountError,
    AlphaChannelDetectedError,
    OutputWriteFailureError,
)


def create_mock_png(
    path: Path,
    width: int = 128,
    height: int = 32,
    mode: str = "P",
    colors: int = 4,
    has_transparency: bool = False,
    extra_pixel_val: int = 0,
) -> None:
    """Helper function to create a mock PNG with specified properties."""
    img = Image.new(mode, (width, height), 0)

    # Generate a palette for indexed images
    if mode == "P":
        # Palette entries are RGB triples
        palette = [
            0, 0, 0,        # Color 0 (Black)
            255, 0, 0,      # Color 1 (Red)
            0, 255, 0,      # Color 2 (Green)
            0, 0, 255,      # Color 3 (Blue)
        ]
        # Fill rest of palette to 256 colors
        palette += [0] * (768 - len(palette))
        img.putpalette(palette)

    # Fill pixels with pattern to verify packing
    # We want to use exactly the requested number of colors
    pixels = []
    for y in range(height):
        for x in range(width):
            if extra_pixel_val and x == 0 and y == 0:
                pixels.append(extra_pixel_val)
            else:
                # Cycle through available colors
                pixels.append((x + y) % colors)
    img.putdata(pixels)

    # Setup transparency info if requested
    if has_transparency:
        img.info["transparency"] = 0

    img.save(path, format="PNG")


def test_valid_conversion(tmp_path: Path) -> None:
    """Test that a valid 128x32 indexed PNG converts successfully."""
    input_png = tmp_path / "valid.png"
    output_fnt = tmp_path / "valid.fnt"

    # Create valid mock image
    create_mock_png(input_png, colors=4)

    config = ConverterConfig(
        input_path=input_png,
        output_path=output_fnt,
        verbose=True,
        strict=True,
    )
    converter = ANTICMode5Converter(config)
    fnt_data = converter.convert()

    # Output size must be exactly 1024 bytes
    assert len(fnt_data) == 1024

    # Write and verify output
    converter.write_output(fnt_data)
    assert output_fnt.is_file()
    assert output_fnt.stat().st_size == 1024

    # Verify bit-packing of first row (x=0..3, y=0)
    # Pattern is (x + y) % 4 -> Row 0, cols 0..3: 0, 1, 2, 3
    # Binary: 0b00 01 10 11 = 27 (decimal)
    assert fnt_data[0] == 27


def test_invalid_dimensions(tmp_path: Path) -> None:
    """Test that images with wrong dimensions are rejected."""
    input_png = tmp_path / "invalid_size.png"
    output_fnt = tmp_path / "output.fnt"

    config = ConverterConfig(
        input_path=input_png,
        output_path=output_fnt,
        verbose=False,
        strict=False,
    )
    converter = ANTICMode5Converter(config)

    # Height 31 instead of 32
    create_mock_png(input_png, width=128, height=31)
    with pytest.raises(UnsupportedDimensionsError):
        converter.convert()

    # Width 127 instead of 128
    create_mock_png(input_png, width=127, height=32)
    with pytest.raises(UnsupportedDimensionsError):
        converter.convert()


def test_invalid_color_count(tmp_path: Path) -> None:
    """Test validation of strict and non-strict color counts."""
    input_png = tmp_path / "colors.png"
    output_fnt = tmp_path / "output.fnt"

    # Strict mode: 3 colors is an error
    create_mock_png(input_png, colors=3)
    converter_strict = ANTICMode5Converter(
        ConverterConfig(
            input_path=input_png,
            output_path=output_fnt,
            verbose=False,
            strict=True,
        )
    )
    with pytest.raises(UnsupportedColorCountError):
        converter_strict.convert()

    # Non-strict mode: 3 colors is allowed
    converter_non_strict = ANTICMode5Converter(
        ConverterConfig(
            input_path=input_png,
            output_path=output_fnt,
            verbose=False,
            strict=False,
        )
    )
    data = converter_non_strict.convert()
    assert len(data) == 1024

    # 5 colors (pixel val 4 is used) is always an error
    create_mock_png(input_png, colors=4, extra_pixel_val=4)
    with pytest.raises(UnsupportedColorCountError):
        converter_non_strict.convert()


def test_missing_input_file(tmp_path: Path) -> None:
    """Test that a missing input file raises an exception."""
    non_existent = tmp_path / "does_not_exist.png"
    output_fnt = tmp_path / "output.fnt"

    converter = ANTICMode5Converter(
        ConverterConfig(
            input_path=non_existent,
            output_path=output_fnt,
            verbose=False,
            strict=False,
        )
    )
    with pytest.raises(MissingInputFileError):
        converter.convert()


def test_invalid_png_format(tmp_path: Path) -> None:
    """Test that non-PNG files are rejected."""
    dummy_file = tmp_path / "dummy.txt"
    dummy_file.write_text("Hello World")
    output_fnt = tmp_path / "output.fnt"

    converter = ANTICMode5Converter(
        ConverterConfig(
            input_path=dummy_file,
            output_path=output_fnt,
            verbose=False,
            strict=False,
        )
    )
    with pytest.raises(InvalidPNGError):
        converter.convert()


def test_alpha_channel_detected(tmp_path: Path) -> None:
    """Test that images with transparency are rejected."""
    input_png = tmp_path / "transparent.png"
    output_fnt = tmp_path / "output.fnt"

    converter = ANTICMode5Converter(
        ConverterConfig(
            input_path=input_png,
            output_path=output_fnt,
            verbose=False,
            strict=False,
        )
    )

    # Mode P with transparency info
    create_mock_png(input_png, has_transparency=True)
    with pytest.raises(AlphaChannelDetectedError):
        converter.convert()

    # Non-indexed mode (RGBA)
    create_mock_png(input_png, mode="RGBA")
    with pytest.raises(InvalidPNGError):
        converter.convert()


def test_output_write_failure(tmp_path: Path) -> None:
    """Test that write failures raise a descriptive exception."""
    input_png = tmp_path / "valid.png"
    
    # Create a regular file where the output directory should be
    blocked_dir = tmp_path / "blocked_dir"
    blocked_dir.write_text("This is a file, not a directory")
    
    # Try to write to a path where 'blocked_dir' is expected to be a directory
    invalid_output = blocked_dir / "output.fnt"

    create_mock_png(input_png)
    converter = ANTICMode5Converter(
        ConverterConfig(
            input_path=input_png,
            output_path=invalid_output,
            verbose=False,
            strict=False,
        )
    )
    data = converter.convert()
    with pytest.raises(OutputWriteFailureError):
        converter.write_output(data)


def test_cli_execution(tmp_path: Path) -> None:
    """Test command-line execution by running the script in a subprocess."""
    input_png = tmp_path / "cli_input.png"
    output_fnt = tmp_path / "cli_output.fnt"

    create_mock_png(input_png, colors=4)

    # Run scripts/png2fnt.py as a subprocess
    result = subprocess.run(
        [
            sys.executable,
            "scripts/png2fnt.py",
            "--input",
            str(input_png),
            "--output",
            str(output_fnt),
            "--strict",
            "--verbose",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert output_fnt.is_file()
    assert output_fnt.stat().st_size == 1024
