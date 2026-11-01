from __future__ import annotations

import os
from pathlib import Path
from typing import List, Tuple
import numpy as np
from PIL import Image

from sprite_studio.models import Frame

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp"}
MAX_DIMENSION = 8192


class ImageImportError(Exception):
    """Raised when image loading, slicing, or conversion fails."""
    pass


def compute_slice_ranges(total: int, count: int) -> List[Tuple[int, int]]:
    """
    Compute start and end coordinates for dividing `total` into `count` parts.
    Remainder pixels are distributed evenly across the first slices so that
    no dimension difference exceeds 1 pixel, no pixel is skipped or duplicated.
    """
    if count < 1:
        raise ImageImportError("Frame count must be at least 1.")
    if count > total:
        raise ImageImportError(f"Frame count ({count}) cannot exceed image dimension ({total} px).")

    base = total // count
    rem = total % count
    ranges = []
    current = 0
    for i in range(count):
        size = base + (1 if i < rem else 0)
        ranges.append((current, current + size))
        current += size
    return ranges


def load_image(path: Path | str) -> Image.Image:
    """
    Load and validate an image file (PNG, JPG/JPEG, BMP).
    """
    p = Path(path)
    if not p.exists():
        raise ImageImportError(f"File not found: {p}")
    if not p.is_file():
        raise ImageImportError(f"Path is not a regular file: {p}")
    if p.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ImageImportError(
            f"Unsupported file format '{p.suffix}'. Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    try:
        img = Image.open(p)
        img.load()  # Force reading entire file to detect corruption early
    except Exception as e:
        raise ImageImportError(f"Failed to read/decode image file: {e}")

    w, h = img.size
    if w <= 0 or h <= 0:
        raise ImageImportError(f"Invalid image dimensions: {w}x{h}")
    if w > MAX_DIMENSION or h > MAX_DIMENSION:
        raise ImageImportError(
            f"Image dimension ({w}x{h}) exceeds maximum supported size ({MAX_DIMENSION}x{MAX_DIMENSION})."
        )

    return img


def detect_image_color_mode(image: Image.Image) -> Tuple[int, str]:
    """
    Detect whether an image should default to 2-color or 4-color mode
    based on indexed palette or unique color count.
    Returns (color_mode, description).
    """
    if image.mode == "1":
        return 2, "Binary 1-bit (2 colors)"

    if image.mode == "P":
        colors = image.getcolors(maxcolors=256)
        if colors is not None:
            num = len(colors)
            if num <= 2:
                return 2, f"Indexed ({num} colors)"
            elif num <= 4:
                return 4, f"Indexed ({num} colors)"
            else:
                return 4, f"Indexed ({num} colors, >4)"
        return 4, "Indexed palette"

    # For RGB / RGBA / L: check unique colors
    colors = image.getcolors(maxcolors=16)
    if colors is not None:
        num = len(colors)
        if num <= 2:
            return 2, f"Unique ({num} colors)"
        elif num <= 4:
            return 4, f"Unique ({num} colors)"

    return 2, f"{image.mode} image (continuous)"


def slice_image(image: Image.Image, frame_count: int, direction: str) -> List[Image.Image]:
    """
    Slice an image into `frame_count` frames either horizontally or vertically.
    """
    if frame_count < 1:
        raise ImageImportError("Frame count must be at least 1.")

    w, h = image.size
    dir_norm = direction.strip().lower()

    if dir_norm in ("horizontal", "h"):
        ranges = compute_slice_ranges(w, frame_count)
        return [image.crop((x0, 0, x1, h)) for (x0, x1) in ranges]
    elif dir_norm in ("vertical", "v"):
        ranges = compute_slice_ranges(h, frame_count)
        return [image.crop((0, y0, w, y1)) for (y0, y1) in ranges]
    else:
        raise ImageImportError(f"Invalid slice direction '{direction}'. Must be 'horizontal' or 'vertical'.")


def prepare_rgb_image(image: Image.Image) -> Image.Image:
    """
    Convert image to RGB. If alpha transparency exists, composite over a black background.
    """
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (0, 0, 0, 255))
        return Image.alpha_composite(bg, rgba).convert("RGB")
    elif image.mode == "L":
        return image.convert("RGB")
    else:
        return image.convert("RGB")


def convert_frame_to_pixels(
    frame_image: Image.Image,
    target_width: int = 8,
    target_height: int = 24,
    color_mode: int = 2,
    threshold: float = 50.0,
    inverse: bool = False,
    fit_mode: str = "fit",
) -> List[str]:
    """
    Convert `frame_image` into a `target_width` x `target_height` sprite frame.
    Supports both:
    - color_mode = 2: binary '0' and '1'
    - color_mode = 4: multi-color '0', '1', '2', '3'

    If frame_image is indexed ('P' or '1') and already matches target dimensions (8 x target_height),
    pixel values are mapped directly without resampling distortion.
    Otherwise, luminance is computed across cells and thresholded into 2 or 4 levels.
    """
    if target_width != 8:
        raise ImageImportError(f"Target width must be 8, got {target_width}.")
    if not (1 <= target_height <= 255):
        raise ImageImportError(f"Target height must be between 1 and 255, got {target_height}.")
    if not (0.0 <= threshold <= 100.0):
        raise ImageImportError(f"Threshold must be between 0 and 100, got {threshold}.")
    if color_mode not in (2, 4):
        raise ImageImportError(f"color_mode must be 2 or 4, got {color_mode}.")

    # Direct pixel-perfect extraction for exact sized indexed images
    if frame_image.mode in ("P", "1") and frame_image.size == (target_width, target_height):
        grid: List[str] = []
        for r in range(target_height):
            row_chars = []
            for c in range(target_width):
                px = int(frame_image.getpixel((c, r)))
                if color_mode == 4:
                    val = px % 4
                    if inverse:
                        val = (3 - val) % 4
                    row_chars.append(str(val))
                else:
                    val = 1 if px else 0
                    if inverse:
                        val = 1 - val
                    row_chars.append(str(val))
            grid.append("".join(row_chars))
        return grid

    src_rgb = prepare_rgb_image(frame_image)
    src_w, src_h = src_rgb.size
    if src_w <= 0 or src_h <= 0:
        raise ImageImportError(f"Frame has invalid dimensions: {src_w}x{src_h}")

    # Determine sub-sampling resolution per cell (S x S pixels per cell)
    s = max(32, min(512, max(src_w // target_width * 2, src_h // target_height * 2)))
    canvas_w = target_width * s
    canvas_h = target_height * s

    fit_norm = fit_mode.strip().lower()

    if fit_norm == "stretch":
        scaled_w = canvas_w
        scaled_h = canvas_h
        scaled_img = src_rgb.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
        canvas = scaled_img
        mask_in_bounds = np.ones((target_height, target_width), dtype=bool)

    elif fit_norm == "crop":
        scale = max(canvas_w / src_w, canvas_h / src_h)
        scaled_w = max(1, int(round(src_w * scale)))
        scaled_h = max(1, int(round(src_h * scale)))
        scaled_img = src_rgb.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
        cx = (scaled_w - canvas_w) // 2
        cy = (scaled_h - canvas_h) // 2
        canvas = scaled_img.crop((cx, cy, cx + canvas_w, cy + canvas_h))
        mask_in_bounds = np.ones((target_height, target_width), dtype=bool)

    else:  # "fit" (letterbox / keep aspect ratio)
        scale = min(canvas_w / src_w, canvas_h / src_h)
        scaled_w = max(1, int(round(src_w * scale)))
        scaled_h = max(1, int(round(src_h * scale)))

        if scaled_w >= src_w and scaled_h >= src_h and (scaled_w % src_w == 0) and (scaled_h % src_h == 0):
            resample_filter = Image.Resampling.NEAREST
        else:
            resample_filter = Image.Resampling.LANCZOS

        scaled_img = src_rgb.resize((scaled_w, scaled_h), resample_filter)

        corners = [
            src_rgb.getpixel((0, 0)),
            src_rgb.getpixel((src_w - 1, 0)),
            src_rgb.getpixel((0, src_h - 1)),
            src_rgb.getpixel((src_w - 1, src_h - 1)),
        ]
        avg_corner_lum = sum(0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2] for c in corners) / 4.0
        pad_color = (255, 255, 255) if avg_corner_lum >= 128 else (0, 0, 0)

        paste_x = (canvas_w - scaled_w) // 2
        paste_y = (canvas_h - scaled_h) // 2

        canvas = Image.new("RGB", (canvas_w, canvas_h), pad_color)
        canvas.paste(scaled_img, (paste_x, paste_y))

        mask_in_bounds = np.zeros((target_height, target_width), dtype=bool)
        for r in range(target_height):
            cell_y0 = r * s
            cell_y1 = (r + 1) * s
            if cell_y1 > paste_y and cell_y0 < paste_y + scaled_h:
                for c in range(target_width):
                    cell_x0 = c * s
                    cell_x1 = (c + 1) * s
                    if cell_x1 > paste_x and cell_x0 < paste_x + scaled_w:
                        mask_in_bounds[r, c] = True

    # Calculate luminance Y in [0, 1]
    arr = np.asarray(canvas, dtype=np.float32) / 255.0
    luminance = 0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]
    brightness = luminance * 100.0

    reshaped = brightness.reshape(target_height, s, target_width, s)
    cell_avg = reshaped.mean(axis=(1, 3))  # shape: (target_height, target_width)

    # Multi-level thresholds for 4-color mode
    t1 = threshold * 0.5
    t2 = threshold
    t3 = threshold + (100.0 - threshold) * 0.5

    result_grid: List[str] = []
    for r in range(target_height):
        row_chars = []
        for c in range(target_width):
            if not mask_in_bounds[r, c]:
                row_chars.append("0")
            else:
                val_lum = cell_avg[r, c]
                if color_mode == 4:
                    if val_lum < t1:
                        lvl = 0
                    elif val_lum < t2:
                        lvl = 1
                    elif val_lum < t3:
                        lvl = 2
                    else:
                        lvl = 3

                    if inverse:
                        lvl = 3 - lvl
                    row_chars.append(str(lvl))
                else:
                    if not inverse:
                        row_chars.append("1" if val_lum >= threshold else "0")
                    else:
                        row_chars.append("0" if val_lum >= threshold else "1")
        result_grid.append("".join(row_chars))

    return result_grid


def convert_frame_to_binary(
    frame_image: Image.Image,
    target_width: int = 8,
    target_height: int = 24,
    threshold: float = 50.0,
    inverse: bool = False,
    fit_mode: str = "fit",
) -> List[str]:
    """Backward compatibility wrapper for convert_frame_to_pixels with color_mode=2."""
    return convert_frame_to_pixels(
        frame_image=frame_image,
        target_width=target_width,
        target_height=target_height,
        color_mode=2,
        threshold=threshold,
        inverse=inverse,
        fit_mode=fit_mode,
    )


def import_raster_frames(
    path: Path | str,
    frame_count: int = 1,
    direction: str = "horizontal",
    target_height: int = 24,
    color_mode: int | None = None,
    threshold: float = 50.0,
    inverse: bool = False,
    fit_mode: str = "fit",
) -> List[Frame]:
    """
    Full pipeline: load image, slice into N frames, fit and convert each frame.
    If color_mode is None, it is auto-detected from image palette / unique colors.
    Returns list of Frame objects with .pixels matching target_height.
    """
    img = load_image(path)
    if color_mode is None:
        color_mode, _ = detect_image_color_mode(img)

    slices = slice_image(img, frame_count, direction)

    frames: List[Frame] = []
    for s_img in slices:
        pixels = convert_frame_to_pixels(
            frame_image=s_img,
            target_width=8,
            target_height=target_height,
            color_mode=color_mode,
            threshold=threshold,
            inverse=inverse,
            fit_mode=fit_mode,
        )
        frames.append(Frame(pixels=pixels))

    return frames
