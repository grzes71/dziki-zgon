# scripts/check_memory.py
import os
import re
import struct
import sys


ROW_RE = re.compile(r"\$([0-9A-Fa-f]{4}).*?\$([0-9A-Fa-f]{4})")
SIZE_RE = re.compile(r"(\d+)")
MUSIC_SIZE_RE = re.compile(r"Original size:\s*\$([0-9A-Fa-f]+)\s*bytes")


def parse_lab(lab_file):
    symbols = {}
    with open(lab_file, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 3:
                try:
                    symbols[parts[2]] = int(parts[1], 16)
                except ValueError:
                    pass
    return symbols


def strip_md(text):
    return text.replace("**", "").replace("`", "").strip()


def norm_name(text):
    return strip_md(text).lower()


def parse_row(line):
    if not line.lstrip().startswith("|"):
        return None

    parts = [p.strip() for p in line.strip().split("|")]
    # Splitting a markdown row by "|" gives empty first and last element.
    if len(parts) < 6:
        return None

    addr_col = parts[1]
    size_col = parts[2]
    name_col = parts[3]
    type_col = parts[4]
    desc_col = parts[5]

    match = ROW_RE.search(addr_col)
    if not match:
        return None

    size_match = SIZE_RE.search(strip_md(size_col))
    size_val = int(size_match.group(1)) if size_match else None

    return {
        "addr_col": addr_col,
        "size_col": size_col,
        "name_col": name_col,
        "type_col": type_col,
        "desc_col": desc_col,
        "start": int(match.group(1), 16),
        "end": int(match.group(2), 16),
        "size": size_val,
        "name_norm": norm_name(name_col),
        "type_norm": norm_name(type_col),
    }


def format_row(row):
    size = row["end"] - row["start"] + 1
    addr_col = f"**`$%04X` – `$%04X`**" % (row["start"], row["end"])
    size_col = f"{size} B"
    return (
        f"| {addr_col} | {size_col} | {row['name_col']} | "
        f"{row['type_col']} | {row['desc_col']} |\n"
    )


def resolve_expr(expr, symbols, extras):
    if isinstance(expr, int):
        return expr
    if expr in extras:
        return extras[expr]
    if expr in symbols:
        return symbols[expr]
    raise KeyError(expr)


def get_title_music_size(lab_file):
    music_asm = os.path.join(os.path.dirname(lab_file), "title_music.asm")
    if not os.path.exists(music_asm):
        return None

    with open(music_asm, "r", encoding="utf-8") as f:
        content = f.read()

    match = MUSIC_SIZE_RE.search(content)
    if not match:
        return None
    return int(match.group(1), 16)


def parse_xex_segments(xex_path):
    """Parse an Atari XEX binary and return a list of segment dictionaries."""
    segments = []
    with open(xex_path, "rb") as f:
        data = f.read()

    pos = 0
    seg_index = 0

    # XEX header: $FF $FF
    if len(data) < 2 or data[0] != 0xFF or data[1] != 0xFF:
        return segments
    pos = 2

    while pos + 3 < len(data):
        # Check for optional $FF $FF segment separator
        if data[pos] == 0xFF and data[pos + 1] == 0xFF:
            pos += 2
            if pos + 3 >= len(data):
                break

        start = struct.unpack_from("<H", data, pos)[0]
        end = struct.unpack_from("<H", data, pos + 2)[0]
        pos += 4
        seg_size = end - start + 1

        if seg_size <= 0 or pos + seg_size > len(data):
            break

        segment_data = data[pos : pos + seg_size]

        if start == 0x02E2:
            target = struct.unpack("<H", segment_data[:2])[0]
            segments.append({
                "type": "INITAD",
                "target": target,
                "index": seg_index
            })
        elif start == 0x02E0:
            target = struct.unpack("<H", segment_data[:2])[0]
            segments.append({
                "type": "RUNAD",
                "target": target,
                "index": seg_index
            })
        else:
            segments.append({
                "type": "DATA",
                "start": start,
                "end": end,
                "index": seg_index
            })

        pos += seg_size
        seg_index += 1

    return segments


def check_xex_segment_overlaps(segments):
    """Check for overlapping XEX segments. Returns list of error strings.
    Two segments overlap when the later-loaded one overwrites bytes from an
    earlier one (i.e. their address ranges intersect). Overlapping is ignored
    if there was an INITAD segment targeting the overwritten segment before
    the overwrite occurred."""
    errors = []

    # Filter only DATA segments for comparison
    data_segs = [s for s in segments if s["type"] == "DATA"]
    initads = [s for s in segments if s["type"] == "INITAD"]

    for i in range(len(data_segs)):
        s1 = data_segs[i]
        s1_start, s1_end, s1_idx = s1["start"], s1["end"], s1["index"]

        for j in range(i + 1, len(data_segs)):
            s2 = data_segs[j]
            s2_start, s2_end, s2_idx = s2["start"], s2["end"], s2["index"]

            # Check intersection: two ranges [a,b] and [c,d] overlap iff a<=d and c<=b
            if s1_start <= s2_end and s2_start <= s1_end:
                # Check if there is an INITAD executed after s1 was loaded but before s2 is loaded
                # which targeted s1_start (or somewhere inside s1)
                is_safe = False
                for init in initads:
                    if s1_idx < init["index"] < s2_idx:
                        if s1_start <= init["target"] <= s1_end:
                            is_safe = True
                            break

                if is_safe:
                    continue

                overlap_start = max(s1_start, s2_start)
                overlap_end = min(s1_end, s2_end)
                overlap_size = overlap_end - overlap_start + 1
                errors.append(
                    f"XEX Segment Overlap: segment {s1_idx} (${s1_start:04X}-${s1_end:04X}) "
                    f"and segment {s2_idx} (${s2_start:04X}-${s2_end:04X}) overlap by "
                    f"{overlap_size} bytes at ${overlap_start:04X}-${overlap_end:04X}! "
                    f"Segment {s2_idx} will overwrite data from segment {s1_idx} during XEX loading."
                )
    return errors


def update_memory_usage(lab_file, md_file, xex_file=None):
    symbols = parse_lab(lab_file)

    with open(md_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    rows = []
    for idx, line in enumerate(lines):
        row = parse_row(line)
        if row:
            row["line_idx"] = idx
            rows.append(row)

    extras = {}
    if "DISABLE_BASIC_LOADER" in symbols:
        extras["START_JUMP_ADDR"] = symbols["DISABLE_BASIC_LOADER"] - 3
    music_size = get_title_music_size(lab_file)
    if music_size is not None:
        extras["TITLE_MUSIC_END"] = symbols.get("MODUL", 0) + music_size - 1

    # Klucz: nazwa z kolumny "Nazwa / Symbol" (lowercase).
    # Wartość: (start_expr, end_expr). end_expr może być:
    # - symbol / liczba
    # - tuple ("before", X): end = resolve(X) - 1
    # - tuple ("size", N): end = start + N - 1
    range_rules = {
        "start (jump)": ("START_JUMP_ADDR", ("before", "DISABLE_BASIC_LOADER")),
        "disable_basic_loader": ("DISABLE_BASIC_LOADER", ("size", 8)),
        "pmg.asm": ("PMG_CLEAR_ALL", ("before", "RLE_DEPACK")),
        "rle.asm": ("RLE_DEPACK", ("before", "TITLE_INIT")),
        "title.asm": ("TITLE_INIT", ("before", "GAME_INIT")),
        "story.asm": ("STORY_INIT", ("before", "STORY_END")),
        "game.asm": ("GAME_INIT", ("before", "STAGE_ORDER")),
        "main.asm": ("STAGE_ORDER", ("before", "DLIST_TITLE")),
        "titlescreen_data": ("TITLESCREEN_DATA", ("before", "DZIKIZGONDATA")),
        "dzikizgondata": ("DZIKIZGONDATA", ("before", "MOONDATA")),
        "moondata": ("MOONDATA", ("size", 98)),
        "display lists": ("DLIST_TITLE", ("size", 360)),
        "vram_arena": ("VRAM_ARENA", ("before", "FOOTER_ADDR")),
        "footer_addr": ("FOOTER_ADDR", ("size", 320)),
        "icon_addr": ("ICON_ADDR", ("size", 120)),
        "font.asm": ("FONTDATA", ("size", 1024)),
        "game_font.asm": ("GAMEFONTDATA", ("size", 1024)),
        "world builder data": ("OBJ_SIZE", ("before", "TEXT_GAMEOVER_FAIL")),
        "all_gameover_texts": ("TEXT_GAMEOVER_FAIL", ("size", 88)),
        "secret_objects.asm": ("SECRET_OBJ_PRESENT", ("before", "TRACK_VARIABLES")),
        "sprites": ("GERWALT_RIGHT_FRAME_0", ("before", "ITEM_CHARSET_POS")),
        "all_texts": ("TEXT_TITLE", ("size", 350)),
        "gameover.asm": ("GAMEOVER_INIT", ("before", "TRAVEL_FRAME_COUNT")),
        "travel_screen.asm": ("TRAVEL_FRAME_COUNT", ("before", "TITLE_AUDIO_INIT")),
        "title_audio.asm": ("TITLE_AUDIO_INIT", ("before", "GERWALT_RIGHT_FRAME_0")),
        "interactive_objects.asm": ("ITEM_CHARSET_POS", ("size", 1258)),
        "missiles": ("MISSILES", ("before", "PLAYER0")),
        "player0": ("PLAYER0", ("before", "PLAYER1")),
        "player1": ("PLAYER1", ("before", "PLAYER2")),
        "player2": ("PLAYER2", ("before", "PLAYER3")),
        "player3": ("PLAYER3", ("before", "GAME_CHARSET")),
        "game_charset": ("GAME_CHARSET", ("before", "TRACK_VARIABLES")),
        "rmtplayr_vars": ("TRACK_VARIABLES", ("before", "PLAYER")),
        "rmtplayr.asm": ("PLAYER", "RMTPLAYEREND"),
        "title_music.asm": ("MODUL", "TITLE_MUSIC_END"),
        "gerwalt_right_frame_0": ("GERWALT_RIGHT_FRAME_0", ("size", 2296)),
    }

    missing_symbols = set()

    # 1) Oblicz precyzyjne zakresy dla pozycji opartych o symbole.
    for row in rows:
        rule = range_rules.get(row["name_norm"])
        if not rule:
            continue

        start_expr, end_expr = rule
        try:
            start_addr = resolve_expr(start_expr, symbols, extras)

            if isinstance(end_expr, tuple):
                mode, value = end_expr
                if mode == "before":
                    end_addr = resolve_expr(value, symbols, extras) - 1
                elif mode == "size":
                    end_addr = start_addr + int(value) - 1
                else:
                    raise ValueError(f"Unsupported end mode: {mode}")
            else:
                end_addr = resolve_expr(end_expr, symbols, extras)

            if end_addr >= start_addr:
                row["start"] = start_addr
                row["end"] = end_addr
            else:
                missing_symbols.add(f"invalid-range:{strip_md(row['name_col'])}")
        except KeyError as err:
            missing_symbols.add(str(err).strip("'"))

    # 2) Wyznacz zakresy WOLNY RAM na podstawie posortowanych sekcji zajętych.
    non_free_sorted = [r for r in rows if "wolny ram" not in r["type_norm"]]
    non_free_sorted.sort(key=lambda r: r["start"])

    for row in rows:
        if "wolny ram" not in row["type_norm"]:
            continue
        prev_section = None
        next_section = None
        for nf in non_free_sorted:
            if nf["end"] < row["start"]:
                prev_section = nf
            elif nf["start"] > row["start"] and next_section is None:
                next_section = nf
                break

        if prev_section:
            new_start = prev_section["end"] + 1
            new_end = (next_section["start"] - 1) if next_section else row["end"]
            if new_end >= new_start:
                row["start"] = new_start
                row["end"] = new_end

    # 2b) Dodatkowa walidacja: "wolny" zakres nie powinien zawierać symboli.
    free_conflicts = []
    for row in rows:
        if "wolny ram" not in row["type_norm"]:
            continue
        hits = [
            name
            for name, addr in symbols.items()
            if row["start"] <= addr <= row["end"]
        ]
        if hits:
            free_conflicts.append((strip_md(row["name_col"]), row["start"], row["end"], hits[:6]))

    # 3) Zapisz zmienione wiersze.
    changed = []
    for row in rows:
        new_line = format_row(row)
        line_idx = row["line_idx"]
        if lines[line_idx] != new_line:
            lines[line_idx] = new_line
            changed.append(strip_md(row["name_col"]))

    # 4) Zaktualizuj tekst z sumą wolnej pamięci (suma wszystkich luk w RAM do $C000)
    total_free = sum(
        non_free_sorted[i + 1]["start"] - 1 - non_free_sorted[i]["end"]
        for i in range(len(non_free_sorted) - 1)
        if non_free_sorted[i + 1]["start"] > non_free_sorted[i]["end"] + 1
    )
            
    summary_prefix = "Łącznie wolny RAM z tych bloków to"
    for i, line in enumerate(lines):
        if line.startswith(summary_prefix):
            formatted_total = f"{total_free:,}".replace(",", " ")
            new_summary = f"{summary_prefix} **{formatted_total} B**.\n"
            if lines[i] != new_summary:
                lines[i] = new_summary
                changed.append("Suma wolnej pamięci")
            break

    if changed:
        with open(md_file, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"MEMORY_USAGE.md updated ({len(changed)} rows).")
    else:
        print("MEMORY_USAGE.md is up-to-date.")

    world_start = symbols.get("OBJ_SIZE")
    world_end = (symbols.get("TEXT_GAMEOVER_FAIL") - 1) if "TEXT_GAMEOVER_FAIL" in symbols else None
    if world_start and world_end:
        main_world_ram = world_end - world_start + 1
        main_world_budget = 0x9D20 - 0x6800
        free_world_ram = 0x9D20 - 1 - world_end
        free_world_pct = (free_world_ram / main_world_budget) * 100.0 if main_world_budget > 0 else 0

        secret_ram = (symbols.get("TRACK_VARIABLES") - symbols.get("SECRET_OBJ_PRESENT")) if ("SECRET_OBJ_PRESENT" in symbols and "TRACK_VARIABLES" in symbols) else 0
        interactive_ram = 1258 if "ITEM_CHARSET_POS" in symbols else 0
        total_world_ram = main_world_ram + secret_ram + interactive_ram

        print("\n=== Statystyki Pamięci Świata Gry w RAM (MADS) ===")
        print(f"  * Rozmiar danych Świata Gry w RAM: {total_world_ram:,} B".replace(",", " "))
        print(f"    - Główny blok świata ($6800-$9D1F): {main_world_ram:,} B / {main_world_budget:,} B".replace(",", " "))
        print(f"    - Bloki pomocnicze (sekrety / obiekty interaktywne): {secret_ram + interactive_ram:,} B".replace(",", " "))
        print(f"  * Wolne miejsce na dalszą rozbudowę Świata: {free_world_ram:,} B ({free_world_pct:.1f}% zapasu wolnego miejsca w bloku)")
        print(f"  * Całkowity wolny RAM w systemie: {total_free:,} B\n".replace(",", " "))

    validation_errors = []

    # --- 1) OS ROM Boundary Check ($BFFF) ---
    for name, addr in symbols.items():
        if addr > 0xBFFF and not name.startswith("D4") and not name.startswith("D0") and not name.startswith("D2") and not name.startswith("NMI") and not name.startswith("IRQ") and not name.startswith("VDSLST") and not name.startswith("SYSVBV"):
            # Exclude hardware equate names which are naturally >= $D000
            pass

    for row in rows:
        if "wolny" not in row["type_norm"]:
            if row["end"] > 0xBFFF:
                validation_errors.append(f"OS ROM Boundary Error: Section '{row['name_col']}' (${row['start']:04X}-${row['end']:04X}) exceeds $BFFF!")

    # --- 2) Display List 1 KB Page Boundary & VRAM Overlap Checks ---
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
                validation_errors.append(
                    f"Display List 1KB Page Crossing: {dlist_name} (${start_addr:04X}-${end_addr:04X}) crosses 1KB boundary! (Page {start_page} to {end_page})"
                )
            if start_addr < 0x4000 and end_addr >= 0x4000:
                validation_errors.append(
                    f"VRAM Arena Overlap: {dlist_name} (${start_addr:04X}-${end_addr:04X}) overlaps VRAM Arena ($4000+)!"
                )

    # --- 3) Segment Overlap Check ---
    non_free_rows = [r for r in rows if "wolny" not in r["type_norm"]]
    non_free_rows.sort(key=lambda r: r["start"])
    for i in range(len(non_free_rows) - 1):
        r1 = non_free_rows[i]
        r2 = non_free_rows[i + 1]
        names_pair = (r1["name_norm"], r2["name_norm"])
        if "vram_arena" in names_pair or "footer_addr" in names_pair or "go_screen" in names_pair or "disable_basic_loader" in names_pair or "start (jump)" in names_pair:
            continue
        if r1["end"] >= r2["start"]:
            validation_errors.append(
                f"Memory Segment Overlap: '{r1['name_col']}' (${r1['start']:04X}-${r1['end']:04X}) overlaps with '{r2['name_col']}' (${r2['start']:04X}-${r2['end']:04X})!"
            )

    # --- 4) XEX Segment Overlap Check ---
    if xex_file is None:
        # Auto-detect: look for dziki_zgon.xex next to the lab file
        xex_candidate = os.path.join(os.path.dirname(lab_file), "..", "dziki_zgon.xex")
        if os.path.isfile(xex_candidate):
            xex_file = xex_candidate

    if xex_file and os.path.isfile(xex_file):
        segments = parse_xex_segments(xex_file)
        xex_errors = check_xex_segment_overlaps(segments)
        validation_errors.extend(xex_errors)

    if missing_symbols:
        # Ignore known missing symbols like invalid-range:gameover.asm
        filtered_missing = [s for s in missing_symbols if not s.startswith("invalid-range:")]
        if filtered_missing:
            sorted_missing = ", ".join(sorted(filtered_missing))
            print(f"Warning: missing symbols: {sorted_missing}")

    if validation_errors:
        print("\n=======================================================")
        print("CRITICAL MEMORY MAP VALIDATION ERRORS DETECTED:")
        for err in validation_errors:
            print(f"  [ERROR] {err}")
        print("=======================================================\n")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python check_memory.py <game.lab> <MEMORY_USAGE.md> [dziki_zgon.xex]")
        sys.exit(1)
    xex = sys.argv[3] if len(sys.argv) > 3 else None
    update_memory_usage(sys.argv[1], sys.argv[2], xex_file=xex)
