# scripts/check_memory.py
import os
import re
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


def update_memory_usage(lab_file, md_file):
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
        "title.asm": ("TITLE_INIT", ("before", "STORY_INIT")),
        "story.asm": ("STORY_INIT", ("before", "GAME_INIT")),
        "game.asm": ("GAME_INIT", ("before", "STAGE_ORDER")),
        "main.asm": ("STAGE_ORDER", ("before", "DLIST_TITLE")),
        "titlescreen_data": ("TITLESCREEN_DATA", ("before", "DZIKIZGONDATA")),
        "dzikizgondata": ("DZIKIZGONDATA", ("before", "MOONDATA")),
        "moondata": ("MOONDATA", ("size", 98)),
        "display lists": ("DLIST_TITLE", ("size", 360)),
        "vram_arena": ("VRAM_ARENA", ("before", "FOOTER_ADDR")),
        "footer_addr": ("FOOTER_ADDR", ("size", 320)),
        "font.asm": ("FONTDATA", ("size", 1024)),
        "game_font.asm": ("GAMEFONTDATA", ("size", 1024)),
        "world builder data": ("OBJ_SIZE", ("before", "TEXT_TITLE")),
        "title_audio.asm": ("TITLE_AUDIO_INIT", ("size", 155)),
        "all_texts": ("TEXT_TITLE", ("before", "TITLE_AUDIO_INIT")),
        "travel_screen.asm": ("TRAVEL_SCREEN_SHOW", ("before", "GO_CHARSET")),
        "gameover.asm": ("GAMEOVER_INIT", ("before", "GAMEOVERSUCCESS_DATA")),
        "titlefooterrom": ("TITLEFOOTERROM", ("size", 289)),
        "go_charset": ("GO_CHARSET", ("size", 1024)),
        "sprites": ("GERWALT_RIGHT_FRAME_0", ("size", 399)),
        "gameoverfail_data": ("GAMEOVERFAIL_DATA", ("size", 920)),
        "gameoversuccess_data": ("GAMEOVERSUCCESS_DATA", ("size", 920)),
        "travelscreen_data": ("TRAVELSCREEN_DATA", ("size", 920)),
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

    # 2) Wyznacz zakresy WOLNY RAM z sąsiadów po aktualizacji sekcji zajętych.
    for idx, row in enumerate(rows):
        if "wolny ram" not in row["type_norm"]:
            continue
        if idx == 0:
            continue

        if idx == len(rows) - 1:
            prev_row = rows[idx - 1]
            new_start = prev_row["end"] + 1
            if row["end"] >= new_start:
                row["start"] = new_start
            continue

        prev_row = rows[idx - 1]
        next_row = rows[idx + 1]
        new_start = prev_row["end"] + 1
        new_end = next_row["start"] - 1
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

    # 4) Zaktualizuj tekst z sumą wolnej pamięci
    total_free = 0
    for row in rows:
        if "wolny ram" in row["type_norm"]:
            total_free += (row["end"] - row["start"] + 1)
            
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
    if len(sys.argv) != 3:
        print("Usage: python check_memory.py <game.lab> <MEMORY_USAGE.md>")
        sys.exit(1)
    update_memory_usage(sys.argv[1], sys.argv[2])

