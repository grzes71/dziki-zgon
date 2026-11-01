#!/usr/bin/env python3
"""Generate detailed textual and graphical (PDF) memory maps for Atari 8-bit executable (.xex).

Target: Atari 800XL / 65XE (MOS 6502, 64 KB RAM)
Project: Dziki Zgon

Reports:
1. Terminal breakdown of all memory segments, sizes, and free gaps.
2. Zero Page allocation details ($00-$FF).
3. Publication-quality vector PDF diagram showing full 64 KB address space,
   zoomed User RAM ($2000-$BFFF), Zero Page bar, and sidebar legend with key metrics.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Sequence, List, Tuple

import matplotlib
matplotlib.use("Agg")  # Headless backend
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Patch
import matplotlib.patheffects as path_effects


@dataclass
class MemorySegment:
    start: int
    end: int
    size: int
    name: str
    category: str
    color: str
    is_free: bool = False
    details: str = ""


# Color palette for memory categories
COLORS: dict[str, str] = {
    "CODE": "#2563EB",         # Royal Blue
    "GRAPHICS": "#059669",     # Emerald Green (VRAM)
    "FONTS": "#0D9488",        # Teal (Fonts/Charsets)
    "WORLD": "#0284C7",        # Sky Blue (World Builder)
    "DLIST": "#D97706",        # Amber
    "AUDIO": "#7C3AED",        # Violet
    "SPRITES": "#EC4899",      # Pink
    "PMG": "#DB2777",          # Deep Magenta
    "FREE": "#10B981",         # Mint Green (Free User RAM)
    "SYSTEM": "#64748B",       # Slate Gray (Low RAM / OS)
    "HARDWARE": "#DC2626",     # Crimson Red ($D000-$DFFF)
    "ROM": "#475569",          # Dark Slate ($C000-$CFFF, $E000-$FFFF)
}


def parse_xex_segments(data_or_path: bytes | str | Path) -> List[Tuple[int, int, int]]:
    """Parse segments from an Atari DOS XEX binary file."""
    if isinstance(data_or_path, (str, Path)):
        data = Path(data_or_path).read_bytes()
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

    return sorted(segments, key=lambda s: s[0])


def identify_segment(start: int, end: int, size: int) -> Tuple[str, str, str, str]:
    """Map segment address range to name, category, color, and description."""
    if start == 0x02E0 or start == 0x02E2:
        return "Vector (RUNAD/INITAD)", "SYSTEM", COLORS["SYSTEM"], "DOS Loader Run/Init Address"
    if start == 0x2000 and size <= 16:
        return "Disable BASIC Loader", "SYSTEM", COLORS["SYSTEM"], "One-shot INI loader disabling BASIC ROM"
    if start == 0x0600:
        return "Title Graphics & Screen RLE", "GRAPHICS", COLORS["GRAPHICS"], "Title screen compressed art & logo assets"
    if start == 0x2000 or (0x2000 <= start < 0x2350):
        return "Core Engine (PMG & RLE)", "CODE", COLORS["CODE"], "PMG helpers, RLE depacker & core utils"
    if 0x2350 <= start < 0x3E80:
        return "Gameplay Engine & Logic", "CODE", COLORS["CODE"], "Actor dispatch, input, player movement & collision logic"
    if start == 0x3E80:
        return "Consolidated Display Lists", "DLIST", COLORS["DLIST"], "1KB-aligned Display Lists (Game, Title, Story, GameOver, Travel)"
    if 0x4000 <= start < 0x5E10:
        return "Shared VRAM Arena", "GRAPHICS", COLORS["GRAPHICS"], "ANTIC Mode 5/2 gameplay VRAM + decompressed title screen"
    if 0x5E10 <= start < 0x6000:
        return "HUD Footer & Message Buffers", "GRAPHICS", COLORS["GRAPHICS"], "Status footer, secret item msg & icon header buffers"
    if start == 0x6000:
        return "UI & Playfield Fonts + World Data", "WORLD", COLORS["WORLD"], "Fonts ($6000-$67FF) + screens, objects, secrets & portals ($6800+)"
    if start == 0x9D20:
        return "Story Screen Logic", "CODE", COLORS["CODE"], "Story introduction handler & typography"
    if start == 0xA800:
        return "Audio Player & Music + Sprites", "AUDIO", COLORS["AUDIO"], "POKEY 4-channel audio driver, music tracks & actor sprites ($BB25+)"
    if 0xA000 <= start < 0xA800:
        return "PMG Buffers (2 KB)", "PMG", COLORS["PMG"], "Single-line PMG memory buffer (PMBASE = $A0)"

    return f"Segment ${start:04X}", "CODE", COLORS["CODE"], f"Code/Data segment ({size} bytes)"


def describe_free_gap(start: int, end: int, size: int) -> str:
    """Human-readable description for free memory gaps."""
    if end == 0x1FFF:
        return "Low RAM gap before Program Code ($2000)"
    if end == 0x3E7F:
        return "Free headroom in low code block before Display Lists ($3E80)"
    if end == 0x3FFF:
        return "Small buffer after Display Lists before VRAM Arena ($4000)"
    if end == 0x5FFF:
        return "Headroom in VRAM block before UI Font ($6000)"
    if start < 0x9D20 and end <= 0x9D1F:
        return "World Builder expansion headroom before Story code ($9D20)"
    if end == 0x9FFF:
        return "Expansion headroom in World block before PMG buffers ($A000)"
    if end == 0xBFFF:
        return "Headroom below OS ROM Kernel boundary ($C000)"
    return f"Unallocated headroom: {size} bytes"


def build_memory_map(
    raw_segments: List[Tuple[int, int, int]]
) -> Tuple[List[MemorySegment], List[MemorySegment]]:
    """Build complete list of user segments and free gaps between $2000 and $BFFF."""
    # Filter out DOS vectors, low RAM title graphics ($0600-$1FB8), and transient 0x2000 init loader
    user_segs: List[Tuple[int, int, int]] = []
    for s in raw_segments:
        if s[0] in (0x02E0, 0x02E2):
            continue
        if s[0] < 0x2000:
            continue
        if s[0] == 0x2000 and s[2] <= 16:
            continue
        user_segs.append(s)

    # Inject runtime reserves: VRAM Arena ($4000-$5FFF) and PMG ($A000-$A7FF)
    user_segs.append((0x4000, 0x5FFF, 0x2000))
    user_segs.append((0xA000, 0xA7FF, 0x0800))
    user_segs.sort(key=lambda s: s[0])

    all_regions: List[MemorySegment] = []
    free_gaps: List[MemorySegment] = []

    curr_addr = 0x2000

    for start, end, size in user_segs:
        if start > curr_addr:
            gap_size = start - curr_addr
            gap_end = start - 1
            gap_seg = MemorySegment(
                start=curr_addr,
                end=gap_end,
                size=gap_size,
                name=f"FREE RAM ({gap_size} B)",
                category="FREE",
                color=COLORS["FREE"],
                is_free=True,
                details=describe_free_gap(curr_addr, gap_end, gap_size),
            )
            all_regions.append(gap_seg)
            free_gaps.append(gap_seg)

        name, cat, col, details = identify_segment(start, end, size)
        all_regions.append(
            MemorySegment(
                start=start,
                end=end,
                size=size,
                name=name,
                category=cat,
                color=col,
                is_free=False,
                details=details,
            )
        )
        curr_addr = max(curr_addr, end + 1)

    if curr_addr <= 0xBFFF:
        gap_size = 0xBFFF - curr_addr + 1
        gap_seg = MemorySegment(
            start=curr_addr,
            end=0xBFFF,
            size=gap_size,
            name=f"FREE RAM ({gap_size} B)",
            category="FREE",
            color=COLORS["FREE"],
            is_free=True,
            details=describe_free_gap(curr_addr, 0xBFFF, gap_size),
        )
        all_regions.append(gap_seg)
        free_gaps.append(gap_seg)

    return all_regions, free_gaps


def print_text_report(
    xex_path: Path,
    all_regions: List[MemorySegment],
    free_gaps: List[MemorySegment],
) -> None:
    """Print formatted terminal report of memory segments and free areas."""
    print("=" * 82)
    print(f"ATARI 8-BIT MEMORY MAP REPORT: {xex_path.name}")
    print("=" * 82)
    print(f"{'Address Range':^19} | {'Size':^8} | {'Type':^10} | {'Segment Name / Description'}")
    print("-" * 82)

    total_allocated = 0
    total_free = 0

    for reg in all_regions:
        addr_str = f"${reg.start:04X} - ${reg.end:04X}"
        size_str = f"{reg.size:5d} B"
        if reg.is_free:
            total_free += reg.size
            print(f"\033[32m{addr_str:19} | {size_str:8} | {'[FREE]':^10} | {reg.name:<35}\033[0m")
        else:
            total_allocated += reg.size
            print(f"{addr_str:19} | {size_str:8} | {reg.category:^10} | {reg.name:<35}")

    print("-" * 82)
    print(f"Total User RAM ($2000-$BFFF):  40,960 bytes (100.0%)")
    print(f"Total Allocated Memory:        {total_allocated:5d} bytes ({total_allocated / 40960 * 100:5.1f}%)")
    print(f"Total Free Memory (Headroom):  {total_free:5d} bytes ({total_free / 40960 * 100:5.1f}%)")
    print("-" * 82)

    # Top free blocks
    sorted_free = sorted(free_gaps, key=lambda g: g.size, reverse=True)
    print("\nTOP FREE MEMORY REGIONS:")
    for idx, g in enumerate(sorted_free, 1):
        print(f"  {idx}. ${g.start:04X} - ${g.end:04X} : {g.size:5d} bytes ({g.size / 1024:4.2f} KB) — {g.details}")

    # Zero Page Breakdown
    print("\n" + "=" * 82)
    print("ZERO PAGE ALLOCATION ($00 - $FF / 256 bytes):")
    print("=" * 82)
    zp_info = [
        ("$00 - $7F", 128, "SYSTEM (OS)", "Reserved for Atari OS Kernel"),
        ("$80 - $85", 6, "RLE DEPACK", "SRC_TMP, GAME_STATE, SRC_PTR, DST_PTR"),
        ("$86 - $8A", 5, "WORLD/SCREEN", "SCREEN_PTR, TILE_PTR, GAME_SCREEN_ID"),
        ("$8B - $91", 7, "RENDERER", "Renderer loop registers (X, Y, W, H, CODE, TMP_X, TMP_Y)"),
        ("$92 - $95", 4, "ENGINE", "FrameCounter, InputState_Joy, InputState_Trig, StageAdvance"),
        ("$96 - $9A", 5, "ACTORS", "PMG_PTR, ACTOR_TMP_X, ACTOR_TMP_Y, ACTOR_TMP_HEIGHT"),
        ("$9C - $A6", 11, "TRANSITIONS", "REQ_SCREEN_TRANSITION, NEW_SCREEN_ID, ACTOR coords, PORTAL"),
        ("$CB - $D4", 10, "AUDIO", "POKEY Audio Player base pointers (PLAYER_ZP_BASE)"),
        ("$D5 - $FF", 43, "FREE", "Available for expansion headroom"),
    ]
    for rng, sz, cat, desc in zp_info:
        cat_str = f"[{cat}]"
        col_prefix = "\033[32m" if cat == "FREE" else ""
        col_suffix = "\033[0m" if cat == "FREE" else ""
        print(f"  {col_prefix}{rng:11} ({sz:3d} B) {cat_str:14} : {desc}{col_suffix}")
    print("=" * 82 + "\n")


def generate_graphical_pdf(
    pdf_path: Path,
    xex_name: str,
    all_regions: List[MemorySegment],
    free_gaps: List[MemorySegment],
) -> None:
    """Generate high-resolution graphical vector PDF visualizing the 64 KB memory space."""
    fig = plt.figure(figsize=(16, 10), dpi=300)
    fig.patch.set_facecolor("#0F172A")  # Modern dark background: Slate-900

    # 1. Header Title
    plt.text(
        0.06, 0.94,
        "ATARI 8-BIT MEMORY MAP — DZIKI ZGON",
        fontsize=20,
        fontweight="bold",
        color="#F8FAFC",
        transform=fig.transFigure,
    )
    plt.text(
        0.06, 0.915,
        f"File: {xex_name}  |  Target: Atari 800XL / 65XE (MOS 6502)  |  RAM: 64 KB  |  User RAM: $2000–$BFFF (40 KB)",
        fontsize=11,
        color="#94A3B8",
        transform=fig.transFigure,
    )

    # 2. Left Column: Full 64 KB Space ($0000 - $FFFF)
    ax_full = fig.add_axes([0.06, 0.10, 0.10, 0.77])
    ax_full.set_facecolor("#1E293B")
    ax_full.set_ylim(0x0000, 0x10000)
    ax_full.set_xlim(0, 1)
    ax_full.set_xticks([])

    full_yticks = [0x0000, 0x0800, 0x2000, 0x4000, 0x6000, 0x8000, 0xA000, 0xC000, 0xD000, 0xE000, 0xFFFF]
    ax_full.set_yticks(full_yticks)
    ax_full.set_yticklabels([f"${y:04X}" for y in full_yticks], fontsize=9, color="#94A3B8", fontfamily="monospace")
    ax_full.tick_params(axis="y", colors="#64748B", length=6)
    for spine in ax_full.spines.values():
        spine.set_color("#334155")

    macro_blocks = [
        (0x0000, 0x07FF, "System RAM\n(ZP, Stack, OS)", COLORS["SYSTEM"]),
        (0x0800, 0x1FFF, "Title Screen Art\n& DOS ($0800)", "#334155"),
        (0x2000, 0xBFFF, "USER PROGRAM\nSPACE (40 KB)\n[ZOOMED ->]", "#1E3A8A"),
        (0xC000, 0xCFFF, "OS ROM Kernel", COLORS["ROM"]),
        (0xD000, 0xDFFF, "Hardware I/O\n(GTIA/ANTIC/POKEY)", COLORS["HARDWARE"]),
        (0xE000, 0xFFFF, "OS ROM Kernel", COLORS["ROM"]),
    ]

    for start, end, label, col in macro_blocks:
        height = end - start + 1
        rect = Rectangle((0, start), 1, height, facecolor=col, edgecolor="#0F172A", linewidth=1.5)
        ax_full.add_patch(rect)
        mid_y = start + height / 2
        ax_full.text(
            0.5, mid_y, label,
            ha="center", va="center",
            fontsize=8, fontweight="bold",
            color="#FFFFFF" if col != "#334155" else "#94A3B8",
        )

    ax_full.set_title("64 KB Space", color="#CBD5E1", fontsize=11, fontweight="bold", pad=10)

    # 3. Center Column: Detailed User RAM ($2000 - $BFFF)
    ax_user = fig.add_axes([0.22, 0.10, 0.38, 0.77])
    ax_user.set_facecolor("#1E293B")
    ax_user.set_ylim(0x2000, 0xC000)
    ax_user.set_xlim(0, 100)
    ax_user.set_xticks([])

    user_yticks = [0x2000, 0x3000, 0x3E80, 0x4000, 0x5E10, 0x6000, 0x6800, 0x8000, 0x9D20, 0xA000, 0xA800, 0xB8E6, 0xC000]
    ax_user.set_yticks(user_yticks)
    ax_user.set_yticklabels([f"${y:04X}" for y in user_yticks], fontsize=9, color="#94A3B8", fontfamily="monospace")
    ax_user.tick_params(axis="y", colors="#64748B", length=6)
    for spine in ax_user.spines.values():
        spine.set_color("#334155")

    for reg in all_regions:
        h = reg.size
        rect = Rectangle((0, reg.start), 100, h, facecolor=reg.color, edgecolor="#0F172A", linewidth=1.0)
        ax_user.add_patch(rect)

        if h >= 180:
            mid_y = reg.start + h / 2
            txt = ax_user.text(
                50, mid_y, f"{reg.name} ({reg.size} B)",
                ha="center", va="center",
                fontsize=8, fontweight="bold",
                color="#FFFFFF" if not reg.is_free else "#064E3B",
            )
            txt.set_path_effects([path_effects.withStroke(linewidth=2, foreground="#000000" if not reg.is_free else "#A7F3D0")])

    ax_user.set_title("User RAM Space ($2000 – $BFFF)", color="#CBD5E1", fontsize=11, fontweight="bold", pad=10)

    # 4. Right Column: Summary Cards & Legend
    ax_card = fig.add_axes([0.65, 0.10, 0.31, 0.77])
    ax_card.set_facecolor("#1E293B")
    ax_card.axis("off")

    total_alloc = sum(r.size for r in all_regions if not r.is_free)
    total_free = sum(g.size for g in free_gaps)

    ax_card.text(0.05, 0.95, "MEMORY UTILIZATION", fontsize=13, fontweight="bold", color="#F8FAFC")
    ax_card.text(0.05, 0.89, f"Total User RAM: 40,960 Bytes (100.0%)", fontsize=10, color="#CBD5E1")
    ax_card.text(0.05, 0.84, f"Allocated:      {total_alloc:5d} Bytes ({total_alloc / 40960 * 100:4.1f}%)", fontsize=10, color="#60A5FA", fontfamily="monospace")
    ax_card.text(0.05, 0.79, f"Free Headroom:  {total_free:5d} Bytes ({total_free / 40960 * 100:4.1f}%)", fontsize=10, color="#34D399", fontfamily="monospace")

    # Legend Categories
    ax_card.text(0.05, 0.70, "CATEGORY LEGEND", fontsize=12, fontweight="bold", color="#F8FAFC")
    cats = [
        ("CODE", "Game & Engine Code", COLORS["CODE"]),
        ("DLIST", "Consolidated Display Lists", COLORS["DLIST"]),
        ("GRAPHICS", "Shared VRAM & HUD Buffers", COLORS["GRAPHICS"]),
        ("FONTS", "UI & Playfield Fonts", COLORS["FONTS"]),
        ("WORLD", "World Builder Screens & Objects", COLORS["WORLD"]),
        ("AUDIO", "POKEY Music & Audio Driver", COLORS["AUDIO"]),
        ("SPRITES", "Player & Enemies Sprites", COLORS["SPRITES"]),
        ("PMG", "Hardware PMG Buffers (2 KB)", COLORS["PMG"]),
        ("FREE", "Free Expansion Headroom", COLORS["FREE"]),
    ]

    y_pos = 0.64
    for cat_key, label, col in cats:
        rect = Rectangle((0.05, y_pos), 0.08, 0.035, facecolor=col, edgecolor="#0F172A", transform=ax_card.transAxes)
        ax_card.add_patch(rect)
        ax_card.text(0.16, y_pos + 0.008, label, fontsize=9, color="#E2E8F0", transform=ax_card.transAxes)
        y_pos -= 0.05

    # Top Free Regions
    ax_card.text(0.05, y_pos - 0.02, "TOP FREE REGIONS", fontsize=12, fontweight="bold", color="#F8FAFC")
    y_pos -= 0.07
    sorted_free = sorted(free_gaps, key=lambda g: g.size, reverse=True)
    for idx, g in enumerate(sorted_free[:4], 1):
        ax_card.text(0.05, y_pos, f"{idx}. ${g.start:04X}-${g.end:04X} ({g.size} B)", fontsize=9, fontweight="bold", color="#34D399", transform=ax_card.transAxes)
        ax_card.text(0.05, y_pos - 0.03, f"{g.details[:42]}...", fontsize=8, color="#94A3B8", transform=ax_card.transAxes)
        y_pos -= 0.07

    plt.savefig(pdf_path, facecolor=fig.get_facecolor(), edgecolor="none", format="pdf")
    plt.close(fig)
    print(f"Generated graphical vector memory map: {pdf_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate detailed Atari 8-bit memory map.")
    parser.add_argument("xex", nargs="?", default="dziki_zgon.xex", type=Path, help="Path to .xex executable")
    parser.add_argument("--pdf", type=Path, help="Path to export PDF diagram (e.g. memory_map.pdf)")

    args = parser.parse_args()

    if not args.xex.is_file():
        print(f"Error: Executable '{args.xex}' not found.", file=sys.stderr)
        return 1

    segments = parse_xex_segments(args.xex)
    all_regions, free_gaps = build_memory_map(segments)

    print_text_report(args.xex, all_regions, free_gaps)

    if args.pdf:
        generate_graphical_pdf(args.pdf, args.xex.name, all_regions, free_gaps)

    return 0


if __name__ == "__main__":
    sys.exit(main())
