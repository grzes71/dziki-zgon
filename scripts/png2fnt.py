#!/usr/bin/env python3
"""PNG to ANTIC Mode 5 character set converter.

Converts an indexed 128x32 PNG image with exactly 4 colors to a 1024-byte
binary Atari 8-bit .FNT file.
"""

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Set
from PIL import Image

# Setup logging
logging.basicConfig(format="%(levelname)s: %(message)s")
logger = logging.getLogger("png2fnt")


class ConversionError(Exception):
    """Base exception class for png2fnt conversion errors."""


class MissingInputFileError(ConversionError):
    """Raised when the input file does not exist."""


class InvalidPNGError(ConversionError):
    """Raised when the input file is not a valid PNG."""


class UnsupportedDimensionsError(ConversionError):
    """Raised when the image dimensions are not exactly 128x32."""


class UnsupportedColorCountError(ConversionError):
    """Raised when the image does not contain exactly four colors."""


class AlphaChannelDetectedError(ConversionError):
    """Raised when an alpha channel or transparency is detected."""


class OutputWriteFailureError(ConversionError):
    """Raised when writing the output file fails."""


@dataclass(frozen=True)
class ConverterConfig:
    """Configuration options for the converter."""

    input_path: Path
    output_path: Path
    verbose: bool
    strict: bool


class ANTICMode5Converter:
    """Performs validation and conversion of PNG images to ANTIC Mode 5 FNT format."""

    REQUIRED_WIDTH: int = 128
    REQUIRED_HEIGHT: int = 32
    REQUIRED_COLOR_COUNT: int = 4
    CHAR_WIDTH: int = 4
    CHAR_HEIGHT: int = 8
    CHARS_HORIZ: int = 32
    CHARS_VERT: int = 4
    TOTAL_CHARS: int = 128
    FONT_SIZE_BYTES: int = 1024

    def __init__(self, config: ConverterConfig) -> None:
        self.config = config

    def validate_input_file(self) -> None:
        """Validates that the input file exists and is accessible."""
        if not self.config.input_path.is_file():
            raise MissingInputFileError(
                f"Input file '{self.config.input_path}' not found."
            )

    def validate_image_properties(self, img: Image.Image) -> None:
        """Validates all image requirements (dimensions, indexing, color count, alpha)."""
        # Validate dimensions
        if img.width != self.REQUIRED_WIDTH or img.height != self.REQUIRED_HEIGHT:
            raise UnsupportedDimensionsError(
                f"Image dimensions must be exactly {self.REQUIRED_WIDTH}x{self.REQUIRED_HEIGHT}. "
                f"Got {img.width}x{img.height}."
            )

        # Validate PNG format
        if img.format != "PNG":
            raise InvalidPNGError(
                f"Image format must be PNG. Got {img.format}."
            )

        # Validate indexed mode (palette-based)
        if img.mode != "P":
            raise InvalidPNGError(
                f"Image mode must be indexed ('P'). Got '{img.mode}'."
            )

        # Check for transparency/alpha channel
        if "transparency" in img.info or img.palette is None:
            raise AlphaChannelDetectedError(
                "Alpha channel or transparency detected in the indexed image."
            )

        # Count unique colors used in pixel data
        pixels = list(img.tobytes())
        unique_colors: Set[int] = set(pixels)

        # Verify that all pixels use indices in the valid range for 2 bits (0-3)
        if any(color >= self.REQUIRED_COLOR_COUNT for color in unique_colors):
            raise UnsupportedColorCountError(
                "Pixel palette index out of bounds (must be 0-3)."
            )

        # Strict color validation
        if self.config.strict:
            if len(unique_colors) != self.REQUIRED_COLOR_COUNT:
                raise UnsupportedColorCountError(
                    f"Image must contain exactly {self.REQUIRED_COLOR_COUNT} unique colors in strict mode. "
                    f"Found {len(unique_colors)} colors: {unique_colors}."
                )
        else:
            if len(unique_colors) > self.REQUIRED_COLOR_COUNT:
                raise UnsupportedColorCountError(
                    f"Image contains {len(unique_colors)} colors, exceeding the limit of {self.REQUIRED_COLOR_COUNT}."
                )

    def convert(self) -> bytearray:
        """Loads, validates, and converts the PNG image into a FNT bytearray."""
        self.validate_input_file()

        try:
            with Image.open(self.config.input_path) as img:
                img.load()
                self.validate_image_properties(img)

                fnt_data = bytearray(self.FONT_SIZE_BYTES)
                fnt_offset = 0

                # Convert characters (32 horizontal x 4 vertical = 128 total)
                for char_y in range(self.CHARS_VERT):
                    for char_x in range(self.CHARS_HORIZ):
                        # Extract character coordinates
                        x_start = char_x * self.CHAR_WIDTH
                        y_start = char_y * self.CHAR_HEIGHT

                        # Pack 8 rows
                        for row in range(self.CHAR_HEIGHT):
                            # Read 4 pixels for the current row
                            p0 = img.getpixel((x_start + 0, y_start + row))
                            p1 = img.getpixel((x_start + 1, y_start + row))
                            p2 = img.getpixel((x_start + 2, y_start + row))
                            p3 = img.getpixel((x_start + 3, y_start + row))

                            # Pack 4 pixels (2 bits each) into 1 byte (MSB-first)
                            packed_byte = (
                                ((p0 & 0x03) << 6)
                                | ((p1 & 0x03) << 4)
                                | ((p2 & 0x03) << 2)
                                | (p3 & 0x03)
                            )
                            fnt_data[fnt_offset] = packed_byte
                            fnt_offset += 1

                return fnt_data

        except (IOError, SyntaxError) as e:
            raise InvalidPNGError(f"Failed to parse PNG file: {e}") from e

    def write_output(self, data: bytearray) -> None:
        """Writes the converted bytearray to the output file path."""
        # Ensure output directory exists
        output_dir = self.config.output_path.parent
        if output_dir:
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise OutputWriteFailureError(
                    f"Failed to create output directory '{output_dir}': {e}"
                ) from e

        try:
            self.config.output_path.write_bytes(data)
        except Exception as e:
            raise OutputWriteFailureError(
                f"Failed to write output file '{self.config.output_path}': {e}"
            ) from e


def main() -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description="Convert indexed PNG to Atari ANTIC Mode 5 character set (.FNT)"
    )
    parser.add_argument(
        "-i", "--input", required=True, type=Path, help="Input PNG image (128x32)"
    )
    parser.add_argument(
        "-o", "--output", required=True, type=Path, help="Output .FNT file (1024 B)"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print verbose status messages",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enforce exactly 4 colors used in image",
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
        verbose=args.verbose,
        strict=args.strict,
    )

    converter = ANTICMode5Converter(config)

    try:
        logger.debug("Starting conversion of '%s'...", config.input_path)
        fnt_data = converter.convert()
        logger.debug("Writing output file '%s'...", config.output_path)
        converter.write_output(fnt_data)
        logger.info(
            "Successfully created ANTIC Mode 5 font: '%s' (%d bytes).",
            config.output_path,
            len(fnt_data),
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
