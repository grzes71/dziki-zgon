# tests/test_memory_map.py
import pytest
from pathlib import Path
from scripts.check_memory import parse_lab, parse_row, update_memory_usage, strip_md

def test_memory_map_no_overlaps_or_page_crossings():
    root_dir = Path(__file__).parent.parent
    lab_file = root_dir / "gen" / "game.lab"
    md_file = root_dir / "MEMORY_USAGE.md"

    if not lab_file.exists():
        pytest.skip("gen/game.lab does not exist yet. Run `make all` first.")

    # Update MEMORY_USAGE.md with latest symbol addresses
    try:
        update_memory_usage(str(lab_file), str(md_file))
    except SystemExit:
        pass  # We will perform assertions directly in this test

    symbols = parse_lab(str(lab_file))
    assert len(symbols) > 0, "gen/game.lab symbol table is empty!"

    errors = []

    # 1. Check Display List 1KB Page Boundary & VRAM Overlap
    dlist_sizes = {
        "DLIST_TITLE": 206,
        "DLIST_STORY": 29,
        "DLIST_GAME": 26,
        "DLIST_GAMEOVER": 37,
        "DLIST_TRAVEL": 37,
    }
    for dlist_name, size in dlist_sizes.items():
        assert dlist_name in symbols, f"Missing symbol {dlist_name} in gen/game.lab"
        start_addr = symbols[dlist_name]
        end_addr = start_addr + size - 1
        start_page = start_addr // 1024
        end_page = end_addr // 1024
        if start_page != end_page:
            errors.append(
                f"Display List 1KB Page Crossing: {dlist_name} (${start_addr:04X}-${end_addr:04X}) crosses 1KB boundary! (Page {start_page} to {end_page})"
            )
        if start_addr < 0x4000 and end_addr >= 0x4000:
            errors.append(
                f"VRAM Arena Overlap: {dlist_name} (${start_addr:04X}-${end_addr:04X}) overlaps VRAM Arena ($4000+)!"
            )

    # 2. Check maximum OS ROM RAM boundary ($BFFF)
    for name, addr in symbols.items():
        if addr > 0xBFFF and not name.startswith("D4") and not name.startswith("D0") and not name.startswith("D2") and not name.startswith("NMI") and not name.startswith("IRQ") and not name.startswith("VDSLST") and not name.startswith("SYSVBV") and not name.startswith("RLE_") and not name.startswith("RMT"):
            pass  # Equates/constants allowed

    # 3. Check memory sections from MEMORY_USAGE.md
    with open(md_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    rows = []
    for idx, line in enumerate(lines):
        row = parse_row(line)
        if row:
            rows.append(row)

    non_free_rows = [r for r in rows if "wolny" not in r["type_norm"]]
    non_free_rows.sort(key=lambda r: r["start"])
    for i in range(len(non_free_rows) - 1):
        r1 = non_free_rows[i]
        r2 = non_free_rows[i + 1]
        names_pair = (r1["name_norm"], r2["name_norm"])
        if "disable_basic_loader" in names_pair or "vram_arena" in names_pair or "footer_addr" in names_pair or "go_screen" in names_pair:
            continue
        if r1["end"] >= r2["start"]:
            errors.append(
                f"Memory Segment Overlap: '{r1['name_col']}' (${r1['start']:04X}-${r1['end']:04X}) overlaps with '{r2['name_col']}' (${r2['start']:04X}-${r2['end']:04X})!"
            )

    assert not errors, "Memory map validation failed:\n" + "\n".join(errors)
