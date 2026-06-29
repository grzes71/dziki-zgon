#!/usr/bin/env python3
"""Atari ANTIC Mode 5 Font to PNG converter.

Converts a 1024-byte binary .FNT file into a 128x32 indexed PNG image.
"""

import argparse
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple
from PIL import Image

# Setup logging
logging.basicConfig(format="%(levelname)s: %(message)s")
logger = logging.getLogger("fnt2png")

# Reference Atari PAL palette (256 colors) extracted from rgb2a8
ATARI_PALETTE: Tuple[int, ...] = (
    0x323132, 0x3F3E3F, 0x4D4C4D, 0x5B5B5B, 0x6A696A, 0x797879, 0x888788, 0x979797,
    0xA1A0A1, 0xAFAFAF, 0xBEBEBE, 0xCECDCE, 0xDBDBDB, 0xEBEAEB, 0xFAFAFA, 0xFFFFFF,
    0x612E00, 0x6C3B00, 0x7A4A00, 0x885800, 0x94670C, 0xA5761B, 0xB2842A, 0xC1943A,
    0xCA9D43, 0xDAAD53, 0xE8BB62, 0xF8CB72, 0xFFD87F, 0xFFE88F, 0xFFF79F, 0xFFFFAE,
    0x6C2400, 0x773000, 0x844003, 0x924E11, 0x9E5D22, 0xAF6C31, 0xBC7B41, 0xCC8A50,
    0xD5935B, 0xE4A369, 0xF2B179, 0xFFC289, 0xFFCF97, 0xFFDFA6, 0xFFEDB5, 0xFFFDC4,
    0x751618, 0x812324, 0x8F3134, 0x9D4043, 0xAA4E50, 0xB85E60, 0xC66D6F, 0xD57D7F,
    0xDE8787, 0xED9596, 0xFCA4A5, 0xFFB4B5, 0xFFC2C4, 0xFFD1D3, 0xFFE0E1, 0xFFEFF0,
    0x620E71, 0x6E1B7C, 0x7B2A8A, 0x8A3998, 0x9647A5, 0xA557B5, 0xB365C3, 0xC375D1,
    0xCD7EDA, 0xDC8DE9, 0xEA97F7, 0xF9ACFF, 0xFFBAFF, 0xFFC9FF, 0xFFD9FF, 0xFFE8FF,
    0x560F87, 0x611D90, 0x712C9E, 0x7F3AAC, 0x8D48BA, 0x9B58C7, 0xA967D5, 0xB877E5,
    0xC280ED, 0xD090FC, 0xDF9FFF, 0xEEAFFF, 0xFCBDFF, 0xFFCCFF, 0xFFDBFF, 0xFFEAFF,
    0x461695, 0x5122A0, 0x6032AC, 0x6E41BB, 0x7C4FC8, 0x8A5ED6, 0x996DE3, 0xA87CF2,
    0xB185FB, 0xC095FF, 0xCFA3FF, 0xDFB3FF, 0xEEC1FF, 0xFCD0FF, 0xFFDFFF, 0xFFEFFF,
    0x212994, 0x2D359F, 0x3D44AD, 0x4B53BA, 0x5961C7, 0x686FD5, 0x777EE2, 0x878EF2,
    0x9097FA, 0x96A6FF, 0xAEB5FF, 0xBFC4FF, 0xCDD2FF, 0xDAE3FF, 0xEAF1FF, 0xFAFEFF,
    0x0F3584, 0x1C418D, 0x2C509B, 0x3A5EAA, 0x486CB7, 0x587BC5, 0x678AD2, 0x7699E2,
    0x80A2EB, 0x8FB2F9, 0x9EC0FF, 0xADD0FF, 0xBDDDFF, 0xCBECFF, 0xDBFCFF, 0xEAFFFF,
    0x043F70, 0x114B79, 0x215988, 0x2F6896, 0x3E75A4, 0x4D83B2, 0x5C92C1, 0x6CA1D2,
    0x74ABD9, 0x83BAE7, 0x93C9F6, 0xA2D8FF, 0xB1E6FF, 0xC0F5FF, 0xD0FFFF, 0xDEFFFF,
    0x005918, 0x006526, 0x0F7235, 0x1D8144, 0x2C8E50, 0x3B9D60, 0x4AAC6F, 0x59BB7E,
    0x63C487, 0x72D396, 0x82E2A5, 0x92F1B5, 0x9FFEC3, 0xAEFFD2, 0xBEFFE2, 0xCEFFF1,
    0x075C00, 0x146800, 0x227500, 0x328300, 0x3F910B, 0x4FA01B, 0x5EAE2A, 0x6EBD3B,
    0x77C644, 0x87D553, 0x96E363, 0xA7F373, 0xB3FE80, 0xC3FF8F, 0xD3FFA0, 0xE3FFB0,
    0x1A5600, 0x286200, 0x367000, 0x457E00, 0x538C00, 0x629B07, 0x70A916, 0x80B926,
    0x89C22F, 0x99D13E, 0xA8DF4D, 0xB7EF5C, 0xC5FC6B, 0xD5FF7B, 0xE3FF8B, 0xF3FF99,
    0x334B00, 0x405700, 0x4D6500, 0x5D7300, 0x6A8200, 0x7A9100, 0x889E0F, 0x98AE1F,
    0xA1B728, 0xBAC638, 0xBFD548, 0xCEE458, 0xDCF266, 0xEBFF75, 0xFAFF85, 0xFFFF95,
    0x4B3C00, 0x584900, 0x655700, 0x746500, 0x817400, 0x908307, 0x9F9116, 0xAEA126,
    0xB7AA2E, 0xC7BA3E, 0xD5C74D, 0xE5D75D, 0xF2E56B, 0xFEF47A, 0xFFFF8B, 0xFFFF9A,
    0x602E00, 0x6D3A00, 0x7A4900, 0x895800, 0x95670A, 0xA4761B, 0xB2832A, 0xC2943A,
    0xCB9D44, 0xDAAC53, 0xE8BA62, 0xF8CB73, 0xFFD77F, 0xFFE791, 0xFFF69F, 0xFFFFAF,
)


class ConversionError(Exception):
    """Base exception class for fnt2png conversion errors."""


class MissingInputFileError(ConversionError):
    """Raised when the input .FNT file is not found."""


class UnsupportedFileSizeError(ConversionError):
    """Raised when the input file is not exactly 1024 bytes."""


class InvalidOutputPathError(ConversionError):
    """Raised when the output directory cannot be created or written to."""


class InvalidRGBValueError(ConversionError):
    """Raised when a custom RGB color specification is invalid."""


class InvalidAtariColorNumberError(ConversionError):
    """Raised when a custom Atari color index is out of bounds or malformed."""


@dataclass(frozen=True)
class ConverterConfig:
    """Configuration options for the FNT to PNG converter."""

    input_path: Path
    output_path: Path
    palette_name: str
    custom_colors: str
    verbose: bool


class ANTICMode5Decoder:
    """Validates input, decodes ANTIC Mode 5 font data, and writes the output PNG."""

    EXPECTED_SIZE: int = 1024
    CHAR_WIDTH: int = 4
    CHAR_HEIGHT: int = 8
    CHARS_HORIZ: int = 32
    CHARS_VERT: int = 4
    IMAGE_WIDTH: int = 128
    IMAGE_HEIGHT: int = 32
    NUM_COLORS: int = 4

    # Default colors (index 0..3)
    DEFAULT_COLORS: List[Tuple[int, int, int]] = [
        (0, 0, 0),        # index 0: RGB(0,0,0)
        (255, 255, 255),  # index 1: RGB(255,255,255)
        (0, 170, 0),      # index 2: RGB(0,170,0)
        (170, 85, 0),     # index 3: RGB(170,85,0)
    ]

    # Predefined Atari palette mapped index values: 0, 15, 202, 36
    ATARI_COLORS_PRESET: List[int] = [0, 15, 202, 36]

    def __init__(self, config: ConverterConfig) -> None:
        self.config = config

    def _convert_atari_to_rgb(self, color_idx: int) -> Tuple[int, int, int]:
        """Translates an Atari color index (0-255) to RGB using reference palette."""
        if not (0 <= color_idx < 256):
            raise InvalidAtariColorNumberError(
                f"Atari color index must be in range 0-255. Got: {color_idx}"
            )
        val = ATARI_PALETTE[color_idx]
        r = (val >> 16) & 0xFF
        g = (val >> 8) & 0xFF
        b = val & 0xFF
        return (r, g, b)

    def _parse_rgb_hex(self, hex_str: str) -> Tuple[int, int, int]:
        """Parses a hex color string like '#FF00FF' or '#FFF' to an RGB tuple."""
        clean_str = hex_str.strip()
        if not re.match(r"^#[0-9a-fA-F]{3}$|^#[0-9a-fA-F]{6}$", clean_str):
            raise InvalidRGBValueError(
                f"RGB hex code must be in #RGB or #RRGGBB format. Got: '{clean_str}'"
            )

        hex_val = clean_str[1:]
        if len(hex_val) == 3:
            r = int(hex_val[0] * 2, 16)
            g = int(hex_val[1] * 2, 16)
            b = int(hex_val[2] * 2, 16)
        else:
            r = int(hex_val[0:2], 16)
            g = int(hex_val[2:4], 16)
            b = int(hex_val[4:6], 16)
        return (r, g, b)

    def resolve_palette(self) -> List[Tuple[int, int, int]]:
        """Resolves the 4-color palette based on command line config."""
        if self.config.custom_colors:
            parts = self.config.custom_colors.split(",")
            if len(parts) != self.NUM_COLORS:
                raise InvalidRGBValueError(
                    f"Palette must specify exactly {self.NUM_COLORS} colors. Got {len(parts)}."
                )

            # Determine parsing strategy: RGB hex vs Atari color indexes
            if parts[0].strip().startswith("#"):
                rgb_colors = []
                for p in parts:
                    rgb_colors.append(self._parse_rgb_hex(p))
                return rgb_colors
            else:
                rgb_colors = []
                for p in parts:
                    p_clean = p.strip()
                    try:
                        color_idx = int(p_clean)
                    except ValueError as e:
                        raise InvalidAtariColorNumberError(
                            f"Failed to parse Atari color number: '{p_clean}'"
                        ) from e
                    rgb_colors.append(self._convert_atari_to_rgb(color_idx))
                return rgb_colors

        # Handle predefined --palette atari option
        if self.config.palette_name == "atari":
            rgb_colors = []
            for color_idx in self.ATARI_COLORS_PRESET:
                rgb_colors.append(self._convert_atari_to_rgb(color_idx))
            return rgb_colors

        # Fallback to default palette
        return self.DEFAULT_COLORS

    def validate_input(self) -> None:
        """Validates that the input file exists and has the exact required size."""
        if not self.config.input_path.is_file():
            raise MissingInputFileError(
                f"Input font file '{self.config.input_path}' not found."
            )
        size = self.config.input_path.stat().st_size
        if size != self.EXPECTED_SIZE:
            raise UnsupportedFileSizeError(
                f"Input file must be exactly {self.EXPECTED_SIZE} bytes. Got {size} bytes."
            )

    def decode_and_generate(self) -> Image.Image:
        """Reads FNT file and decodes characters into a Pillow Image."""
        self.validate_input()

        try:
            fnt_data = self.config.input_path.read_bytes()
        except Exception as e:
            raise MissingInputFileError(f"Failed to read input file: {e}") from e

        # Resolve color palette
        palette = self.resolve_palette()

        # Create indexed PIL image
        img = Image.new("P", (self.IMAGE_WIDTH, self.IMAGE_HEIGHT), 0)

        # Flatten palette to a list of 768 bytes (256 RGB triples)
        flat_palette = []
        for r, g, b in palette:
            flat_palette.extend([r, g, b])
        # Pad palette up to 256 entries
        flat_palette.extend([0] * (768 - len(flat_palette)))
        img.putpalette(flat_palette)

        fnt_offset = 0

        # Decode characters (128 characters total in a 32x4 grid)
        for char_y in range(self.CHARS_VERT):
            for char_x in range(self.CHARS_HORIZ):
                x_start = char_x * self.CHAR_WIDTH
                y_start = char_y * self.CHAR_HEIGHT

                # Decode 8 rows per character
                for row in range(self.CHAR_HEIGHT):
                    b = fnt_data[fnt_offset]
                    fnt_offset += 1

                    # Unpack 4 pixels from the byte (2 bits each, MSB-first)
                    p0 = (b >> 6) & 0x03
                    p1 = (b >> 4) & 0x03
                    p2 = (b >> 2) & 0x03
                    p3 = b & 0x03

                    # Draw pixels in indexed image
                    img.putpixel((x_start + 0, y_start + row), p0)
                    img.putpixel((x_start + 1, y_start + row), p1)
                    img.putpixel((x_start + 2, y_start + row), p2)
                    img.putpixel((x_start + 3, y_start + row), p3)

        return img

    def write_output(self, img: Image.Image) -> None:
        """Writes the generated image to output path."""
        # Ensure output directory exists
        output_dir = self.config.output_path.parent
        if output_dir:
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise InvalidOutputPathError(
                    f"Failed to create output directory '{output_dir}': {e}"
                ) from e

        try:
            img.save(self.config.output_path, format="PNG")
        except Exception as e:
            raise InvalidOutputPathError(
                f"Failed to write output image file '{self.config.output_path}': {e}"
            ) from e


def main() -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description="Convert raw Atari ANTIC Mode 5 character set (.FNT) to PNG"
    )
    parser.add_argument(
        "-i", "--input", required=True, type=Path, help="Input FNT file (1024 B)"
    )
    parser.add_argument(
        "-o", "--output", required=True, type=Path, help="Output PNG file (128x32)"
    )
    parser.add_argument(
        "--palette",
        choices=["atari"],
        help="Use predefined palette (e.g. 'atari')",
    )
    parser.add_argument(
        "--colors",
        help="Custom colors: '#RRGGBB,#RRGGBB,#RRGGBB,#RRGGBB' or 'c0,c1,c2,c3' Atari color indexes",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print verbose status messages",
    )

    args = parser.parse_args()

    # Configure logger
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    config = ConverterConfig(
        input_path=args.input,
        output_path=args.output,
        palette_name=args.palette or "",
        custom_colors=args.colors or "",
        verbose=args.verbose,
    )

    decoder = ANTICMode5Decoder(config)

    try:
        logger.debug("Starting FNT decoding for '%s'...", config.input_path)
        img = decoder.decode_and_generate()
        logger.debug("Saving output image '%s'...", config.output_path)
        decoder.write_output(img)
        logger.info(
            "Successfully created indexed PNG: '%s' (%dx%d).",
            config.output_path,
            img.width,
            img.height,
        )
        return 0
    except ConversionError as e:
        logger.error(str(e))
        return 1
    except Exception as e:
        logger.error("Unexpected error during conversion: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
