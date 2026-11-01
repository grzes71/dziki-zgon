#!/usr/bin/env python3
"""Validate memory map and bounds for Atari 8-bit executable (.xex).

Target: Atari 800XL / 65XE (MOS 6502, 64 KB RAM)
Project: Dziki Zgon

Enforces project rules:
1. All user segments must end at or below $BFFF (OS ROM boundary).
2. OS ROM ($C000-$CFFF, $E000-$FFFF) and Hardware registers ($D000-$DFFF) must never be overwritten.
3. Display lists must not cross a 1 KB ($0400) boundary.
4. No two data segments in the XEX may overlap (unless an intermediate INITAD safely consumed the earlier segment).
5. Code and data must not collide with runtime VRAM ($4000-$5FFF) or PMG ($A000-$A7FF).
6. Reports memory allocations and remaining headroom.
"""

from __future__ import annotations

import argparse
import os
import re
import struct
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

ROW_RE = re.compile(r"\$([0-9A-Fa-f]{4}).*?\$([0-9A-Fa-f]{4})")
SIZE_RE = re.compile(r"(\d+)")


def parse_lab(lab_file: str | Path) -> Dict[str, int]:
    """Parse MADS symbol table (.lab)."""
    symbols: Dict[str, int] = {}
    p = Path(lab_file)
    if not p.is_file():
        return symbols

    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 3:
                try:
                    symbols[parts[2]] = int(parts[1], 16)
                except ValueError:
                    pass
    return symbols


def parse_xex_segments(data_or_path: bytes | str | Path) -> List[Tuple[int, int, int]]:
    """Parse segments from an Atari DOS XEX binary file.

    Returns list of (start_addr, end_addr, size).
    """
    if isinstance(data_or_path, (str, Path)):
        p = Path(data_or_path)
        if not p.is_file():
            return []
        data = p.read_bytes()
    else:
        data = data_or_path

    segments: List[Tuple[int, int, int]] = []
    if len(data) < 2 or data[0] != 0xFF or data[1] != 0xFF:
        return segments

    pos = 2
    while pos + 4 <= len(data):
        if data[pos] == 0xFF and data[pos + 1] == 0xFF:
            pos += 2
            if pos + 4 > len(data):
                break

        start = data[pos] | (data[pos + 1] << 8)
        end = data[pos + 2] | (data[pos + 3] << 8)
        pos += 4

        size = end - start + 1
        if size <= 0 or pos + size > len(data):
            break

        segments.append((start, end, size))
        pos += size

    return segments


def check_xex_segment_overlaps(segments: List[Tuple[int, int, int]]) -> List[str]:
    """Check for overlapping XEX segments in load order.
    Overwriting is allowed only if an INITAD ($02E2) occurred in between
    and consumed the previous segment (e.g. disabling BASIC).
    """
    errors: List[str] = []
    data_segs: List[Tuple[int, int, int, int]] = []  # (start, end, size, load_order)
    initad_orders: List[int] = []

    for idx, (start, end, size) in enumerate(segments):
        if start == 0x02E2:
            initad_orders.append(idx)
        elif start != 0x02E0:
            data_segs.append((start, end, size, idx))

    for i in range(len(data_segs)):
        s1_start, s1_end, s1_size, s1_idx = data_segs[i]
        for j in range(i + 1, len(data_segs)):
            s2_start, s2_end, s2_size, s2_idx = data_segs[j]

            # Range intersection: s1_start <= s2_end and s2_start <= s1_end
            if s1_start <= s2_end and s2_start <= s1_end:
                # Safe if an INITAD executed between s1 and s2
                is_safe = any(s1_idx < init_idx < s2_idx for init_idx in initad_orders)
                if is_safe:
                    continue

                overlap_start = max(s1_start, s2_start)
                overlap_end = min(s1_end, s2_end)
                overlap_size = overlap_end - overlap_start + 1
                errors.append(
                    f"XEX Segment Overlap: segment {s1_idx} (${s1_start:04X}-${s1_end:04X}) "
                    f"and segment {s2_idx} (${s2_start:04X}-${s2_end:04X}) overlap by "
                    f"{overlap_size} bytes at ${overlap_start:04X}-${overlap_end:04X}!"
                )
    return errors


def identify_segment(start: int, end: int, size: int) -> Tuple[str, str]:
    """Map segment address range to human-readable name and category."""
    if start == 0x02E0:
        return "RUNAD Vector", "SYSTEM"
    if start == 0x02E2:
        return "INITAD Vector (Disable BASIC)", "SYSTEM"
    if start == 0x2000 and size <= 16:
        return "Disable BASIC Loader", "CODE"
    if start == 0x0600:
        return "Title Graphics & Screen RLE", "GRAPHICS"
    if start == 0x2000 or (0x2000 <= start < 0x2350):
        return "Core Engine (PMG & RLE Depacker)", "CODE"
    if 0x2350 <= start < 0x3E80:
        return "Gameplay Engine & Logic", "CODE"
    if start == 0x3E80:
        return "Consolidated Display Lists", "DLIST"
    if 0x4000 <= start < 0x5E10:
        return "Shared VRAM Arena", "GRAPHICS"
    if start == 0x6000:
        return "UI & Playfield Fonts + World Data", "WORLD/DATA"
    if start == 0x9D20:
        return "Story Screen Logic", "CODE"
    if start == 0xA800:
        return "Audio Player & Music Tracks + Sprites", "AUDIO/SPRITES"
    if 0xA000 <= start < 0xA800:
        return "PMG Buffers (2 KB)", "PMG"

    return f"Data Segment (${start:04X})", "DATA"


def check_display_lists(symbols: Dict[str, int]) -> List[str]:
    """Check that all Display Lists do not cross 1 KB ANTIC page boundaries."""
    errors: List[str] = []
    dlist_sizes = {
        "DLIST_TITLE": 206,
        "DLIST_STORY": 29,
        "DLIST_GAME": 26,
        "DLIST_GAMEOVER": 37,
        "DLIST_TRAVEL": 37,
    }

    for dlist_name, size in dlist_sizes.items():
        if dlist_name in symbols:
            start_addr = symbols[dlist_name]
            end_addr = start_addr + size - 1
            start_page = start_addr // 1024
            end_page = end_addr // 1024
            if start_page != end_page:
                errors.append(
                    f"Display List 1KB Boundary Crossing: {dlist_name} (${start_addr:04X}-${end_addr:04X}) "
                    f"crosses 1 KB page boundary! (Page {start_page} to {end_page})"
                )
            if start_addr < 0x4000 and end_addr >= 0x4000:
                errors.append(
                    f"VRAM Arena Overlap: {dlist_name} (${start_addr:04X}-${end_addr:04X}) "
                    f"overlaps VRAM Arena ($4000+)!"
                )
    return errors


def update_memory_usage_md(
    md_file: Path,
    segments: List[Tuple[int, int, int]],
    symbols: Dict[str, int]
) -> None:
    """Synchronize MEMORY_USAGE.md summary with current binary segment data."""
    if not md_file.is_file():
        return

    # Calculate actual free gaps in User RAM ($2000-$BFFF)
    user_segs = [s for s in segments if s[0] not in (0x02E0, 0x02E2)]
    # Filter out initial small init loader at 0x2000 if it was replaced
    filtered_segs: List[Tuple[int, int]] = []
    for s, e, sz in sorted(user_segs, key=lambda x: x[0]):
        if s == 0x2000 and sz <= 16:
            continue
        filtered_segs.append((s, e))

    # Also account for runtime VRAM ($4000-$5FFF) and PMG ($A000-$A7FF)
    filtered_segs.append((0x4000, 0x5FFF))
    filtered_segs.append((0xA000, 0xA7FF))
    filtered_segs.sort(key=lambda x: x[0])

    # Merge overlapping or touching ranges
    merged: List[Tuple[int, int]] = []
    for s, e in filtered_segs:
        if not merged:
            merged.append((s, e))
        else:
            prev_s, prev_e = merged[-1]
            if s <= prev_e + 1:
                merged[-1] = (prev_s, max(prev_e, e))
            else:
                merged.append((s, e))

    # Compute free gaps between $2000 and $BFFF
    free_gaps: List[Tuple[int, int, int]] = []
    curr = 0x2000
    for s, e in merged:
        if s > curr:
            free_gaps.append((curr, s - 1, s - curr))
        curr = max(curr, e + 1)
    if curr <= 0xBFFF:
        free_gaps.append((curr, 0xBFFF, 0xBFFF - curr + 1))

    total_free = sum(sz for _, _, sz in free_gaps)

    # Update summary line in markdown
    content = md_file.read_text(encoding="utf-8")
    summary_re = re.compile(r"Łącznie .*?wolny RAM.*?to \*\*([0-9\s]+) B\*\*\.")
    new_str = f"Łącznie czysty, bezpośrednio dostępny wolny RAM w tej chwili to **{total_free:,} B**.".replace(",", " ")

    if summary_re.search(content):
        new_content = summary_re.sub(new_str, content)
        if new_content != content:
            md_file.write_text(new_content, encoding="utf-8")
            print(f"Updated {md_file.name} (Total free RAM: {total_free:,} B)".replace(",", " "))


def check_memory(
    xex_path: Union[str, Path],
    lab_path: Optional[Union[str, Path]] = None,
    md_path: Optional[Union[str, Path]] = None,
) -> int:
    """Main verification routine."""
    xex_path = Path(xex_path)
    lab_path = Path(lab_path) if lab_path else None
    md_path = Path(md_path) if md_path else None

    if not xex_path.is_file():
        print(f"Error: XEX file '{xex_path}' not found.", file=sys.stderr)
        return 1

    data = xex_path.read_bytes()
    segments = parse_xex_segments(data)
    symbols = parse_lab(lab_path) if lab_path else {}

    print("=" * 70)
    print(f"ATARI 8-BIT MEMORY VALIDATION: {xex_path.name}")
    print("=" * 70)

    errors: List[str] = []
    total_user_bytes = 0

    for start, end, size in segments:
        name, category = identify_segment(start, end, size)
        is_vector = start in (0x02E0, 0x02E2)
        if not is_vector:
            total_user_bytes += size

        print(f"Segment: ${start:04X} - ${end:04X}  ({size:5d} B)  [{category:<12}] {name}")

        # Rule 1 & 2: Boundary checks
        if not is_vector:
            if start >= 0xC000:
                errors.append(f"Segment ${start:04X}-${end:04X} overlaps OS ROM ($C000+)!")
            elif end >= 0xC000:
                errors.append(f"Segment ${start:04X}-${end:04X} exceeds $BFFF user limit into OS ROM!")
            elif 0xD000 <= start <= 0xDFFF or 0xD000 <= end <= 0xDFFF:
                errors.append(f"Segment ${start:04X}-${end:04X} overlaps Hardware Registers ($D000-$DFFF)!")

            # Rule 5: Code/data must not overlap runtime VRAM Arena or PMG
            if (0x4000 <= start < 0x5E10 or 0x4000 <= end < 0x5E10) and category not in ("GRAPHICS",):
                errors.append(f"Segment ${start:04X}-${end:04X} collides with runtime VRAM Arena ($4000-$5E0F)!")
            if (0xA000 <= start < 0xA800 or 0xA000 <= end < 0xA800) and category not in ("PMG",):
                errors.append(f"Segment ${start:04X}-${end:04X} collides with PMG memory buffer ($A000-$A7FF)!")

    # Check XEX segment overlaps
    overlap_errors = check_xex_segment_overlaps(segments)
    errors.extend(overlap_errors)

    # Check Display List boundary crossings
    if symbols:
        dlist_errors = check_display_lists(symbols)
        errors.extend(dlist_errors)

    # Headroom report
    # User RAM available: $0000-$BFFF (minus OS low RAM $0000-$07FF, VRAM arena $4000-$5FFF, and PMG $A000-$A7FF)
    print("-" * 70)
    print(f"Total XEX Code/Data Payload: {total_user_bytes:,} bytes".replace(",", " "))

    # World data headroom ($6800-$9FFF)
    world_seg = next((s for s in segments if s[0] == 0x6000), None)
    if world_seg:
        w_start, w_end, w_size = world_seg
        w_headroom = 0x9D20 - w_end - 1
        print(f"World & Fonts Block (${w_start:04X}-$9D1F): {w_size:,} B used, {w_headroom:,} B free headroom".replace(",", " "))
        if w_headroom < 0:
            errors.append(f"World & Fonts block exceeds $9D20 boundary into Story Screen by {-w_headroom} bytes!")

    # Audio & Sprites headroom ($A800-$BFFF)
    audio_seg = next((s for s in segments if s[0] == 0xA800), None)
    if audio_seg:
        a_start, a_end, a_size = audio_seg
        a_headroom = 0xC000 - a_end - 1
        print(f"Audio & Sprites Block (${a_start:04X}-$BFFF): {a_size:,} B used, {a_headroom:,} B free headroom".replace(",", " "))
        if a_headroom < 0:
            errors.append(f"Audio/Sprites block exceeds $BFFF into OS ROM by {-a_headroom} bytes!")

    print("=" * 70)

    # Update MEMORY_USAGE.md if provided
    if md_path and md_path.is_file():
        update_memory_usage_md(md_path, segments, symbols)

    if errors:
        print("\nCRITICAL MEMORY MAP VALIDATION ERRORS DETECTED:", file=sys.stderr)
        for err in errors:
            print(f"  [ERROR] {err}", file=sys.stderr)
        print("", file=sys.stderr)
        return 1

    print("SUCCESS: All segments pass memory architecture validation.\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check Atari 8-bit memory boundaries for Dziki Zgon."
    )
    # Flexible argument parsing supporting both positional conventions
    parser.add_argument("args", nargs="*", help="[xex_file] OR [lab_file] [md_file] [xex_file]")
    parser.add_argument("--lab", type=Path, help="Path to MADS .lab file")
    parser.add_argument("--md", type=Path, help="Path to MEMORY_USAGE.md")
    parser.add_argument("--xex", type=Path, help="Path to .xex binary")

    parsed = parser.parse_args()

    xex_path: Optional[Path] = parsed.xex
    lab_path: Optional[Path] = parsed.lab
    md_path: Optional[Path] = parsed.md

    # Support legacy positional convention:
    # check_memory.py gen/game.lab MEMORY_USAGE.md [dziki_zgon.xex]
    # OR check_memory.py dziki_zgon.xex
    if parsed.args:
        first = Path(parsed.args[0])
        if first.suffix.lower() == ".xex":
            xex_path = first
        elif first.suffix.lower() == ".lab":
            lab_path = first
            if len(parsed.args) > 1:
                md_path = Path(parsed.args[1])
            if len(parsed.args) > 2:
                xex_path = Path(parsed.args[2])

    if not xex_path:
        # Default fallback: check dziki_zgon.xex in current directory
        candidate = Path("dziki_zgon.xex")
        if candidate.is_file():
            xex_path = candidate
        else:
            print("Error: No XEX binary specified and 'dziki_zgon.xex' not found.", file=sys.stderr)
            return 1

    if not lab_path:
        cand_lab = Path("gen/game.lab")
        if cand_lab.is_file():
            lab_path = cand_lab

    if not md_path:
        cand_md = Path("MEMORY_USAGE.md")
        if cand_md.is_file():
            md_path = cand_md

    return check_memory(xex_path, lab_path=lab_path, md_path=md_path)


if __name__ == "__main__":
    sys.exit(main())
