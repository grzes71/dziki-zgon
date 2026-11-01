"""Unit and integration tests for memory validation and memory map generator."""

from __future__ import annotations

from pathlib import Path
import pytest

from scripts.check_memory import (
    parse_xex_segments as check_parse_xex_segments,
    check_xex_segment_overlaps,
    check_display_lists,
    parse_lab,
    check_memory,
)
from scripts.generate_memory_map import (
    parse_xex_segments,
    identify_segment,
    build_memory_map,
    generate_graphical_pdf,
)


def test_parse_xex_segments_from_built_binary():
    xex_path = Path("dziki_zgon.xex")
    if not xex_path.is_file():
        pytest.skip("dziki_zgon.xex not found, build binary first")

    segments = check_parse_xex_segments(str(xex_path))
    assert len(segments) >= 5
    starts = [s[0] for s in segments]
    assert 0x0600 in starts  # Title graphics
    assert 0x2000 in starts  # Engine / code
    assert 0x3E80 in starts  # Display Lists
    assert 0x6000 in starts  # Fonts / World
    assert 0xA800 in starts  # Audio player / sprites


def test_xex_segment_no_overlaps():
    """Parse the compiled dziki_zgon.xex binary and verify that no two XEX load
    segments occupy overlapping address ranges (except INITAD)."""
    xex_path = Path("dziki_zgon.xex")
    if not xex_path.is_file():
        pytest.skip("dziki_zgon.xex not found, build binary first")

    segments = check_parse_xex_segments(str(xex_path))
    errors = check_xex_segment_overlaps(segments)
    assert not errors, "XEX segment overlap detected!\n" + "\n".join(errors)


def test_check_display_lists():
    """Check Display List 1KB page crossing and VRAM arena overlaps."""
    lab_file = Path("gen/game.lab")
    if not lab_file.is_file():
        pytest.skip("gen/game.lab not found, build binary first")

    symbols = parse_lab(str(lab_file))
    errors = check_display_lists(symbols)
    assert not errors, "Display List checks failed:\n" + "\n".join(errors)


def test_identify_segment():
    name, cat, col, _ = identify_segment(0x2000, 0x2321, 802)
    assert cat == "CODE"
    assert "Engine" in name

    name, cat, col, _ = identify_segment(0x3E80, 0x3F87, 264)
    assert cat == "DLIST"
    assert "Display Lists" in name

    name, cat, col, _ = identify_segment(0x6000, 0x9B2C, 15149)
    assert cat == "WORLD"
    assert "World Data" in name

    name, cat, col, _ = identify_segment(0xA800, 0xBCA8, 5289)
    assert cat == "AUDIO"
    assert "Audio" in name


def test_build_memory_map_bounds_and_continuity():
    xex_path = Path("dziki_zgon.xex")
    if not xex_path.is_file():
        pytest.skip("dziki_zgon.xex not found, build binary first")

    data = xex_path.read_bytes()
    raw_segments = parse_xex_segments(data)
    all_regions, free_gaps = build_memory_map(raw_segments)

    # All regions must span exactly $2000 to $BFFF contiguously
    assert all_regions[0].start == 0x2000
    assert all_regions[-1].end == 0xBFFF

    for i in range(len(all_regions) - 1):
        assert all_regions[i].end + 1 == all_regions[i + 1].start, (
            f"Discontinuity between {all_regions[i].name} and {all_regions[i+1].name}"
        )

    # Total bytes must sum to exactly 40,960 bytes ($2000 to $BFFF)
    total_bytes = sum(r.size for r in all_regions)
    assert total_bytes == 40960

    # Ensure free gaps are detected and non-empty
    assert len(free_gaps) >= 3
    largest_gap = max(g.size for g in free_gaps)
    assert largest_gap >= 100


def test_generate_graphical_pdf(tmp_path: Path):
    xex_path = Path("dziki_zgon.xex")
    if not xex_path.is_file():
        pytest.skip("dziki_zgon.xex not found, build binary first")

    data = xex_path.read_bytes()
    raw_segments = parse_xex_segments(data)
    all_regions, free_gaps = build_memory_map(raw_segments)

    out_pdf = tmp_path / "test_memory_map.pdf"
    generate_graphical_pdf(out_pdf, xex_path.name, all_regions, free_gaps)

    assert out_pdf.is_file()
    assert out_pdf.stat().st_size > 10_000  # Ensure valid non-trivial vector PDF


def test_check_memory_full_validation():
    xex_path = Path("dziki_zgon.xex")
    lab_path = Path("gen/game.lab")
    md_path = Path("MEMORY_USAGE.md")
    if not xex_path.is_file() or not lab_path.is_file():
        pytest.skip("Binary or lab file missing")

    ret = check_memory(str(xex_path), str(lab_path), str(md_path))
    assert ret == 0
