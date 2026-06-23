#!/usr/bin/env python3
"""
Konwerter obrazów (PNG/BMP/GIF) dla Atari 8-bit (ANTIC).

Generuje:
  - title.bin               surowe dane binarne (spakowane piksele MSB-first)
  - title.asm               dane .byte dla MADS-a
  - title_colors.asm        inicjalizacja rejestrów kolorów (COLBK, COLPF0–2)
  - title_displaylist.asm   ANTIC Display List dla danego trybu
  - title.rle               dane skompresowane RLE (+ opcjonalny depacker .asm)

Użycie:
  python img2asm.py title.png 2                     # 2 bpp → 4 kolory
  python img2asm.py title.png 2 --all               # wszystkie pliki wyjściowe
  python img2asm.py title.png 2 -c rle              # kompresja RLE
  python img2asm.py title.png 2 -o nazwa.bin        # tylko .bin
"""

import argparse
import math
import os
import struct
import subprocess
import sys
from pathlib import Path

from PIL import Image

# =============================================================================
# Paleta Atari 8-bit (PAL GTIA, 256 kolorów) + dopasowanie CIELAB/CIE2000
# =============================================================================

# Rzeczywista paleta Atari PAL (256 wartości 0xRRGGBB)
# Źródło: pomiary z rzeczywistego sprzętu, wartości identyczne z rgb2a8.cpp
_ATARI_PALETTE_RAW = [
    0x323132, 0x3f3e3f, 0x4d4c4d, 0x5b5b5b,
    0x6a696a, 0x797879, 0x888788, 0x979797,
    0xa1a0a1, 0xafafaf, 0xbebebe, 0xcecdce,
    0xdbdbdb, 0xebeaeb, 0xfafafa, 0xffffff,
    0x612e00, 0x6c3b00, 0x7a4a00, 0x885800,
    0x94670c, 0xa5761b, 0xb2842a, 0xc1943a,
    0xca9d43, 0xdaad53, 0xe8bb62, 0xf8cb72,
    0xffd87f, 0xffe88f, 0xfff79f, 0xffffae,
    0x6c2400, 0x773000, 0x844003, 0x924e11,
    0x9e5d22, 0xaf6c31, 0xbc7b41, 0xcc8a50,
    0xd5935b, 0xe4a369, 0xf2b179, 0xffc289,
    0xffcf97, 0xffdfa6, 0xffedb5, 0xfffdc4,
    0x751618, 0x812324, 0x8f3134, 0x9d4043,
    0xaa4e50, 0xb85e60, 0xc66d6f, 0xd57d7f,
    0xde8787, 0xed9596, 0xfca4a5, 0xffb4b5,
    0xffc2c4, 0xffd1d3, 0xffe0e1, 0xffeff0,
    0x620e71, 0x6e1b7c, 0x7b2a8a, 0x8a3998,
    0x9647a5, 0xa557b5, 0xb365c3, 0xc375d1,
    0xcd7eda, 0xdc8de9, 0xea97f7, 0xf9acff,
    0xffbaff, 0xffc9ff, 0xffd9ff, 0xffe8ff,
    0x560f87, 0x611d90, 0x712c9e, 0x7f3aac,
    0x8d48ba, 0x9b58c7, 0xa967d5, 0xb877e5,
    0xc280ed, 0xd090fc, 0xdf9fff, 0xeeafff,
    0xfcbdff, 0xffccff, 0xffdbff, 0xffeaff,
    0x461695, 0x5122a0, 0x6032ac, 0x6e41bb,
    0x7c4fc8, 0x8a5ed6, 0x996de3, 0xa87cf2,
    0xb185fb, 0xc095ff, 0xcfa3ff, 0xdfb3ff,
    0xeec1ff, 0xfcd0ff, 0xffdfff, 0xffefff,
    0x212994, 0x2d359f, 0x3d44ad, 0x4b53ba,
    0x5961c7, 0x686fd5, 0x777ee2, 0x878ef2,
    0x9097fa, 0x96a6ff, 0xaeb5ff, 0xbfc4ff,
    0xcdd2ff, 0xdae3ff, 0xeaf1ff, 0xfafeff,
    0x0f3584, 0x1c418d, 0x2c509b, 0x3a5eaa,
    0x486cb7, 0x587bc5, 0x678ad2, 0x7699e2,
    0x80a2eb, 0x8fb2f9, 0x9ec0ff, 0xadd0ff,
    0xbdddff, 0xcbecff, 0xdbfcff, 0xeaffff,
    0x043f70, 0x114b79, 0x215988, 0x2f6896,
    0x3e75a4, 0x4d83b2, 0x5c92c1, 0x6ca1d2,
    0x74abd9, 0x83bae7, 0x93c9f6, 0xa2d8ff,
    0xb1e6ff, 0xc0f5ff, 0xd0ffff, 0xdeffff,
    0x005918, 0x006526, 0x0f7235, 0x1d8144,
    0x2c8e50, 0x3b9d60, 0x4aac6f, 0x59bb7e,
    0x63c487, 0x72d396, 0x82e2a5, 0x92f1b5,
    0x9ffec3, 0xaeffd2, 0xbeffe2, 0xcefff1,
    0x075c00, 0x146800, 0x227500, 0x328300,
    0x3f910b, 0x4fa01b, 0x5eae2a, 0x6ebd3b,
    0x77c644, 0x87d553, 0x96e363, 0xa7f373,
    0xb3fe80, 0xc3ff8f, 0xd3ffa0, 0xe3ffb0,
    0x1a5600, 0x286200, 0x367000, 0x457e00,
    0x538c00, 0x629b07, 0x70a916, 0x80b926,
    0x89c22f, 0x99d13e, 0xa8df4d, 0xb7ef5c,
    0xc5fc6b, 0xd5ff7b, 0xe3ff8b, 0xf3ff99,
    0x334b00, 0x405700, 0x4d6500, 0x5d7300,
    0x6a8200, 0x7a9100, 0x889e0f, 0x98ae1f,
    0xa1b728, 0xbac638, 0xbfd548, 0xcee458,
    0xdcf266, 0xebff75, 0xfaff85, 0xffff95,
    0x4b3c00, 0x584900, 0x655700, 0x746500,
    0x817400, 0x908307, 0x9f9116, 0xaea126,
    0xb7aa2e, 0xc7ba3e, 0xd5c74d, 0xe5d75d,
    0xf2e56b, 0xfef47a, 0xffff8b, 0xffff9a,
    0x602e00, 0x6d3a00, 0x7a4900, 0x895800,
    0x95670a, 0xa4761b, 0xb2832a, 0xc2943a,
    0xcb9d44, 0xdaac53, 0xe8ba62, 0xf8cb73,
    0xffd77f, 0xffe791, 0xfff69f, 0xffffaf,
]

# Rozpakuj do listy krotek (R, G, B)
_ATARI_PALETTE_RGB = [
    ((c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF)
    for c in _ATARI_PALETTE_RAW
]


def _rgb_to_lab(r, g, b):
    """Konwertuje RGB (0–255) do CIELAB (L*, a*, b*).

    Algorytm identyczny z rgb2a8.cpp:
      sRGB → liniowe RGB → XYZ (D65, 2°) → CIELAB
    """
    # sRGB → liniowe RGB
    var_r = r / 255.0
    var_g = g / 255.0
    var_b = b / 255.0

    var_r = pow((var_r + 0.055) / 1.055, 2.4) if var_r > 0.04045 else var_r / 12.92
    var_g = pow((var_g + 0.055) / 1.055, 2.4) if var_g > 0.04045 else var_g / 12.92
    var_b = pow((var_b + 0.055) / 1.055, 2.4) if var_b > 0.04045 else var_b / 12.92

    var_r *= 100.0
    var_g *= 100.0
    var_b *= 100.0

    # Liniowe RGB → XYZ (D65, 2°)
    x = var_r * 0.4124 + var_g * 0.3576 + var_b * 0.1805
    y = var_r * 0.2126 + var_g * 0.7152 + var_b * 0.0722
    z = var_r * 0.0193 + var_g * 0.1192 + var_b * 0.9505

    # XYZ → CIELAB
    var_x = x / 95.047
    var_y = y / 100.000
    var_z = z / 108.883

    var_x = pow(var_x, 1.0 / 3.0) if var_x > 0.008856 else (7.787 * var_x) + (16.0 / 116.0)
    var_y = pow(var_y, 1.0 / 3.0) if var_y > 0.008856 else (7.787 * var_y) + (16.0 / 116.0)
    var_z = pow(var_z, 1.0 / 3.0) if var_z > 0.008856 else (7.787 * var_z) + (16.0 / 116.0)

    L = (116.0 * var_y) - 16.0
    a = 500.0 * (var_x - var_y)
    b_lab = 200.0 * (var_y - var_z)

    return (L, a, b_lab)


# Pre-konwertuj paletę Atari do CIELAB (jednorazowo przy imporcie)
_ATARI_PALETTE_LAB = [_rgb_to_lab(r, g, b) for r, g, b in _ATARI_PALETTE_RGB]


def rgb_to_atari(r, g, b):
    """Znajduje najbliższy kolor Atari (0x00–0xFF) dla danego RGB.

    Używa przestrzeni CIELAB i uproszczonej formuły CIE2000
    (identycznie jak rgb2a8.cpp), co daje znacznie lepsze
    perceptualne dopasowanie niż odległość Euklidesowa w RGB.
    """
    K1, K2 = 0.045, 0.015
    target_L, target_a, target_b = _rgb_to_lab(r, g, b)

    C1 = math.sqrt(target_a * target_a + target_b * target_b)
    Sl = 1.0
    Sc = 1.0 + K1 * C1
    Sh = 1.0 + K2 * C1

    best_idx = 0
    best_dist = float("inf")

    for idx, (pL, pa, pb) in enumerate(_ATARI_PALETTE_LAB):
        C2 = math.sqrt(pa * pa + pb * pb)

        Dl = target_L - pL
        Dc = C1 - C2

        a2 = (target_a - pa) ** 2
        b2 = (target_b - pb) ** 2
        Dh_sq = a2 + b2 - Dc * Dc
        Dh = math.sqrt(max(Dh_sq, 0.0))

        dist = (Dl / Sl) ** 2 + (Dc / Sc) ** 2 + (Dh / Sh) ** 2

        if dist < best_dist:
            best_dist = dist
            best_idx = idx
            if dist == 0.0:
                break

    return best_idx


def atari_to_hex(color_idx):
    """Konwertuje indeks koloru Atari (0..255) na string $XX."""
    return f"${color_idx:02X}"


def atari_color_name(color_idx):
    """Przybliżona nazwa koloru Atari (hue, lum)."""
    h = (color_idx >> 4) & 0xF
    l = color_idx & 0xF
    hues = [
        "szary", "złoty", "pomarańczowy", "czerwony",
        "różowy", "fioletowy", "niebieski", "błękitny",
        "turkusowy", "zielono-niebieski", "zielony",
        "żółto-zielony", "oliwkowy", "brązowy", "beżowy", "jasnoszary",
    ]
    return f"hue={h} ({hues[h]}), lum={l}"


# =============================================================================
# Ładowanie obrazu
# =============================================================================

def load_image(image_path, bits_per_pixel):
    """Wczytuje obraz i konwertuje do trybu indeksowanego.

    Returns:
        (img, pixels, palette_rgb)
        img      – obiekt PIL.Image (indeksowany)
        pixels   – płaska lista indeksów palety
        palette_rgb – lista krotek (R, G, B) dla każdego indeksu
    """
    img = Image.open(image_path)
    width, height = img.size

    max_colors = 1 << bits_per_pixel

    if img.mode != "P":
        img = img.convert("P", palette=Image.Palette.ADAPTIVE, colors=max_colors)
    else:
        # Sprawdź, czy obraz nie ma za dużo kolorów
        used = len(set(img.get_flattened_data()))
        if used > max_colors:
            print(
                f"⚠ Obraz używa {used} kolorów, redukuję do {max_colors}…"
            )
            img = img.convert("P", palette=Image.Palette.ADAPTIVE, colors=max_colors)

    pixels = list(img.get_flattened_data())

    # Wyciągnij paletę RGB (Pillow: 768 bajtów, trójki R,G,B)
    raw_pal = img.getpalette()
    num_entries = min(max_colors, len(raw_pal) // 3)
    palette_rgb = [
        (raw_pal[i * 3], raw_pal[i * 3 + 1], raw_pal[i * 3 + 2])
        for i in range(num_entries)
    ]

    return img, width, height, pixels, palette_rgb


# =============================================================================
# Pakowanie pikseli
# =============================================================================

def pack_pixels(width, height, pixels, bits_per_pixel, screen_base_address=0x4000):
    """Pakuje piksele w bajty (MSB-first) z wyrównaniem do granic 4KB.

    Gdy linia obrazu przekracza granicę bloku 4KB, wstawiane są bajty
    dopełnienia (padding $00) tak, aby kolejna linia zaczynała się
    od równego adresu $x000. Dzięki temu ANTIC nie zawija licznika
    w trakcie pobierania linii — każda linia mieści się w całości
    w swoim bloku 4KB.

    Returns:
        bytearray spakowanych bajtów (z paddingiem)
    """
    pixels_per_byte = 8 // bits_per_pixel
    pixel_mask = (1 << bits_per_pixel) - 1
    packed = bytearray()

    bytes_per_line = (width * bits_per_pixel) // 8
    current_abs_addr = screen_base_address

    for y in range(height):
        # Czy ta linia zmieści się przed granicą 4KB?
        bytes_until_boundary = 4096 - (current_abs_addr & 0x0FFF)
        if bytes_until_boundary < bytes_per_line:
            # Linia przekroczyłaby granicę — dodaj padding do $x000
            packed.extend(b"\x00" * bytes_until_boundary)
            current_abs_addr += bytes_until_boundary

        # Pakuj piksele dla bieżącej linii
        for x in range(0, width, pixels_per_byte):
            byte_val = 0
            for i in range(pixels_per_byte):
                px = x + i
                if px < width:
                    p = pixels[y * width + px] & pixel_mask
                    shift = 8 - bits_per_pixel * (i + 1)
                    byte_val |= p << shift
            packed.append(byte_val)

        current_abs_addr += bytes_per_line

    return packed


# =============================================================================
# Kompresja RLE
# =============================================================================

def rle_compress(data):
    """Kompresja RLE (run-length encoding).

    Format:
      Bajt flagi:
        bit 7 = 1 → powtórzenie: bity 6..0 = liczba_powtórzeń - 1  (1..128)
        bit 7 = 0 → ciąg literałów: bity 6..0 = długość - 1 (1..128)
      Dane:
        powtórzenie → 1 bajt do powtórzenia
        literały    → N bajtów

    Returns:
        bytearray ze skompresowanymi danymi
    """
    result = bytearray()
    i = 0
    n = len(data)

    while i < n:
        # Szukaj ciągu powtarzających się bajtów
        run_len = 1
        while i + run_len < n and run_len < 128 and data[i + run_len] == data[i]:
            run_len += 1

        if run_len >= 3:
            # Opłaca się kompresować (oszczędność ≥ 1 bajt)
            result.append(0x80 | (run_len - 1))
            result.append(data[i])
            i += run_len
        else:
            # Ciąg literałów
            lit_start = i
            i += 1
            # Zbieraj literały, aż trafimy na powtórzenie ≥ 3 lub limit 128
            while i < n and (i - lit_start) < 128:
                future_run = 1
                while i + future_run < n and future_run < 3 and data[i + future_run] == data[i]:
                    future_run += 1
                if future_run >= 3:
                    break
                i += 1
            lit_len = i - lit_start
            result.append(lit_len - 1)          # bit 7 = 0
            result.extend(data[lit_start:i])

    return result


# =============================================================================
# Generatory plików wyjściowych
# =============================================================================

def generate_bin(packed_data, output_path):
    """Zapisuje surowe dane binarne."""
    with open(output_path, "wb") as f:
        f.write(packed_data)
    print(f"  ✔ {output_path}  ({len(packed_data)} bajtów)")


def generate_asm_data(packed_data, output_path, label, bytes_per_line=8):
    """Zapisuje dane w formacie .byte (MADS)."""
    lines = []
    lines.append(f"; Dane obrazu: {label}")
    lines.append(f"; Rozmiar:      {len(packed_data)} bajtów")
    lines.append("")

    for i in range(0, len(packed_data), bytes_per_line):
        chunk = packed_data[i : i + bytes_per_line]
        hex_vals = ",".join(f"${b:02X}" for b in chunk)
        prefix = f"{label}\t.byte " if i == 0 else "\t.byte "
        lines.append(prefix + hex_vals)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  ✔ {output_path}")


def generate_asm_colors(palette_rgb, output_path, label_prefix, bits_per_pixel):
    """Generuje plik .asm z inicjalizacją rejestrów kolorów.

    Zapisuje wartości do rejestrów **cieniowych** OS (shadow registers),
    dzięki czemu zmiany są trwałe — VBLANK skopiuje je do GTIA.

    Dla 2 bpp (4 kolory):
        indeks 0 → COLOR4 ($02C8) = shadow COLBK
        indeks 1 → COLOR0 ($02C4) = shadow COLPF0
        indeks 2 → COLOR1 ($02C5) = shadow COLPF1
        indeks 3 → COLOR2 ($02C6) = shadow COLPF2

    Dla 1 bpp (2 kolory):
        indeks 0 → COLOR4 ($02C8)
        indeks 1 → COLOR0 ($02C4)
    """
    max_colors = 1 << bits_per_pixel

    # Mapowanie: indeks piksela → (nazwa_shadow, adres_shadow, adres_hw, opis)
    reg_map = {
        0: ("COLOR4", "$02C8", "$D01A", "tło (COLBK)"),
        1: ("COLOR0", "$02C4", "$D016", "playfield 0 (COLPF0)"),
        2: ("COLOR1", "$02C5", "$D017", "playfield 1 (COLPF1)"),
        3: ("COLOR2", "$02C6", "$D018", "playfield 2 (COLPF2)"),
    }

    lines = []
    lines.append(f"; Kolory dla: {label_prefix}")
    lines.append(f"; Automatycznie dopasowane do palety Atari (PAL)")
    lines.append(";")
    lines.append("; Zapis do rejestrów CIENIOWYCH OS (shadow registers).")
    lines.append("; VBLANK skopiuje je automatycznie do sprzętowych GTIA.")
    lines.append(";")
    lines.append(";   COLOR4 ($02C8) → COLBK  ($D01A)")
    lines.append(";   COLOR0 ($02C4) → COLPF0 ($D016)")
    lines.append(";   COLOR1 ($02C5) → COLPF1 ($D017)")
    lines.append(";   COLOR2 ($02C6) → COLPF2 ($D018)")
    lines.append(";")

    # Wypisz mapowanie jako komentarze
    for i in range(min(max_colors, len(palette_rgb))):
        r, g, b = palette_rgb[i]
        atari_idx = rgb_to_atari(r, g, b)
        hex_val = atari_to_hex(atari_idx)
        name = atari_color_name(atari_idx)
        if i in reg_map:
            reg_shadow, reg_shadow_addr, reg_hw, reg_desc = reg_map[i]
            lines.append(f";   indeks {i} → {reg_shadow:7s} {reg_shadow_addr} = {hex_val}  "
                         f"(RGB #{r:02X}{g:02X}{b:02X} → {name})")
        else:
            lines.append(f";   indeks {i} → ??? = {hex_val}  "
                         f"(RGB #{r:02X}{g:02X}{b:02X} → {name})")

    lines.append("")
    lines.append("; --- Inicjalizacja kolorów (shadow registers) ---")

    for i in range(min(max_colors, len(palette_rgb))):
        if i >= len(reg_map):
            break
        reg_shadow, reg_shadow_addr, reg_hw, reg_desc = reg_map[i]
        r, g, b = palette_rgb[i]
        atari_idx = rgb_to_atari(r, g, b)
        hex_val = atari_to_hex(atari_idx)
        lines.append(f"\tlda #{hex_val}")
        lines.append(f"\tsta {reg_shadow_addr}\t; {reg_shadow} → {reg_hw} ({reg_desc})")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  ✔ {output_path}")


def _compute_dl_segments(width, height, bits_per_pixel, screen_base_address):
    """Oblicza podział ekranu na segmenty Display List z wyrównaniem do granic 4KB.

    Zamiast oznaczać linie przekraczające granicę jako „crossing”,
    algorytm przeskakuje offset danych do początku następnego bloku 4KB
    (z pominięciem paddingu), dzięki czemu każdy segment LMS zaczyna się
    od równego adresu $x000.

    Returns:
        Lista krotek (line_start, line_count, data_offset, lms_abs_addr)
        gdzie:
          line_start   – indeks pierwszej linii segmentu
          line_count   – liczba linii w segmencie
          data_offset  – offset w spakowanych danych (uwzględnia padding)
          lms_abs_addr – bezwzględny adres LMS (hex string, zawsze $x000)
    """
    bytes_per_line = (width * bits_per_pixel) // 8
    segments = []
    line = 0
    current_offset = 0  # rzeczywisty offset w spakowanych danych (z paddingiem)

    while line < height:
        absolute_address = screen_base_address + current_offset
        bytes_until_boundary = 4096 - (absolute_address & 0x0FFF)

        if bytes_until_boundary >= bytes_per_line:
            # Linie mieszczą się w obecnym bloku 4KB
            lines_before_boundary = bytes_until_boundary // bytes_per_line
            remaining = height - line
            line_count = min(remaining, lines_before_boundary)

            lms_abs_addr = f"${absolute_address:04X}"
            segments.append((line, line_count, current_offset, lms_abs_addr))

            line += line_count
            current_offset += line_count * bytes_per_line
        else:
            # Obecna linia przekroczyłaby granicę 4KB
            # → pomijamy końcówkę bloku (padding) i zaczynamy od $x000
            current_offset += bytes_until_boundary
            absolute_address = screen_base_address + current_offset

            # Nowy blok 4KB — pełna przestrzeń
            lines_before_boundary = 4096 // bytes_per_line
            remaining = height - line
            line_count = min(remaining, lines_before_boundary)

            lms_abs_addr = f"${absolute_address:04X}"
            segments.append((line, line_count, current_offset, lms_abs_addr))

            line += line_count
            current_offset += line_count * bytes_per_line

    return segments


def generate_asm_displaylist(
    width,
    height,
    bits_per_pixel,
    output_path,
    label_prefix,
    data_label,
    screen_base_address=0x4000,
):
    """Generuje ANTIC Display List dla danego trybu graficznego.

    Obsługuje tryby ANTIC (wartości w Display List):
      1 bpp → $F  (Graphics 8,  np. 320×192, 2 kolory)
      2 bpp → $E  (Graphics 7,  np. 160×192, 4 kolory)
      4 bpp → $F  (GTIA mode,   np.  80×192, 16 kolorów – wymaga PRIOR=$40)

    Args:
        screen_base_address: bezwzględny adres początku danych ekranu
                             (np. 0x4000). Używany do poprawnego wykrywania
                             granic 4KB w przestrzeni adresowej ANTIC-a.
    """
    # --- Wybór trybu ANTIC (wartość w Display List) -------------------------
    antic_map = {
        1: 0x0F,   # ANTIC F – Graphics 8
        2: 0x0E,   # ANTIC E – Graphics 7
        4: 0x0F,   # ANTIC F + GTIA – Graphics 9/10/11
    }
    antic_mode = antic_map.get(bits_per_pixel)
    if antic_mode is None:
        print(
            f"⚠ Display List: brak obsługi dla {bits_per_pixel} bpp "
            f"(obsługiwane: {sorted(antic_map.keys())}).",
            file=sys.stderr,
        )
        return

    bytes_per_line = (width * bits_per_pixel) // 8

    segments = _compute_dl_segments(width, height, bits_per_pixel, screen_base_address)

    lines = []
    lines.append(f"; ANTIC Display List dla: {label_prefix}")
    lines.append(f"; Tryb ANTIC:   ${antic_mode:02X}  ({width}×{height}, "
                 f"{1 << bits_per_pixel} kolory)")
    lines.append(f"; Bajtów/linia: {bytes_per_line}")
    lines.append(f"; Adres ekranu: ${screen_base_address:04X}")

    # Podsumowanie segmentów
    total_check = sum(sc for _, sc, _, _ in segments)
    lines.append(f"; Segmentów:    {len(segments)}  (linii łącznie: {total_check})")

    # Rozmiar całkowity z paddingiem — z ostatniego segmentu
    last_seg = segments[-1]
    total_bytes = last_seg[2] + (last_seg[1] * bytes_per_line)
    lines.append(f"; Danych (z paddingiem): {total_bytes} bajtów")
    lines.append("")

    lines.append("DLIST")

    # Górny margines: 24 puste linie (3 × $70)
    lines.append("\t; 24 puste linie (górna ramka)")
    lines.append("\tdta $70, $70, $70")
    lines.append("")

    antic_no_lms = antic_mode          # np. $0E
    antic_lms    = antic_mode | 0x40    # np. $4E

    for seg_idx, (line_start, line_count, data_offset, lms_addr) in enumerate(segments, 1):
        end_line = line_start + line_count - 1

        lines.append(f"\t; --- Segment {seg_idx}: LMS = {lms_addr}")
        lines.append(f"\t;     linie {line_start}..{end_line} "
                     f"({line_count} linii, offset danych {data_offset}) ---")

        # LMS z rzeczywistym offsetem (uwzględniającym padding)
        lines.append(f"\tdta ${antic_lms:02X}, a({data_label} + {data_offset})")

        # Kolejne linie segmentu (bez LMS)
        extra = line_count - 1
        if extra > 0:
            lines.append(f"\t.rept {extra}")
            lines.append(f"\tdta ${antic_no_lms:02X}")
            lines.append("\t.endr")

    lines.append("")
    lines.append("\t; Koniec Display List")
    lines.append("\tdta $41, a(DLIST)\t; JVB – skok z oczekiwaniem na VBLANK")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  ✔ {output_path}")


def generate_rle_asm_depacker(output_path):
    """Generuje procedurę depackera RLE w asemblerze 6502 (MADS)."""
    code = r"""; =============================================================================
; Depacker RLE (run-length encoding) dla 6502
;
; Format RLE:
;   Bajt flagi:
;     bit 7 = 1 → powtórzenie, bity 6..0 = liczba - 1
;     bit 7 = 0 → literały,   bity 6..0 = długość - 1
;
; Wejście:
;   srcPtr  (word) – adres skompresowanych danych
;   dstPtr  (word) – adres docelowy (bufor docelowy)
;
; Niszczy: A, X, Y
; =============================================================================

srcPtr  equ $80        ; wskaźnik źródła (2 bajty, page zero)
dstPtr  equ $82        ; wskaźnik celu   (2 bajty, page zero)

.proc RLE_Depack
        ldy #0

loop
        ; --- Odczytaj bajt flagi ---
        lda (srcPtr),Y
        inc srcPtr
        bne skip_inc_src
        inc srcPtr+1
skip_inc_src

        bmi do_repeat       ; bit 7 = 1 → powtórzenie

        ; --- Literały (bit 7 = 0) ---
        tax                 ; X = liczba literałów - 1
        inx                 ; X = liczba literałów (1..128)
        ldy #0
@lit_copy
        lda (srcPtr),Y
        sta (dstPtr),Y
        inc srcPtr
        bne @lit_skip_src
        inc srcPtr+1
@lit_skip_src
        inc dstPtr
        bne @lit_skip_dst
        inc dstPtr+1
@lit_skip_dst
        dex
        bne @lit_copy
        beq loop            ; zawsze

        ; --- Powtórzenie (bit 7 = 1) ---
do_repeat
        and #$7F            ; liczba powtórzeń - 1
        tax
        inx                 ; X = liczba powtórzeń (1..128)
        ldy #0
        lda (srcPtr),Y      ; bajt do powtórzenia
        inc srcPtr
        bne @rep_skip_src
        inc srcPtr+1
@rep_skip_src
        ldy #0
@rep_store
        sta (dstPtr),Y
        inc dstPtr
        bne @rep_skip_dst
        inc dstPtr+1
@rep_skip_dst
        dex
        bne @rep_store
        beq loop            ; zawsze
.endp
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"  ✔ {output_path}")


def compress_zx5(data, output_path):
    """Kompresuje dane za pomocą zewnętrznego narzędzia zx5."""
    # Zapisz tymczasowy plik z nieskompresowanymi danymi
    tmp_in = output_path + ".tmp"
    with open(tmp_in, "wb") as f:
        f.write(data)

    try:
        result = subprocess.run(
            ["zx5", tmp_in, output_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            print(f"  ✗ zx5: {result.stderr.strip()}", file=sys.stderr)
            return None
        print(f"  ✔ {output_path}  (ZX5, {os.path.getsize(output_path)} bajtów)")
        return output_path
    except FileNotFoundError:
        print(
            "  ✗ Narzędzie 'zx5' nie zostało znalezione w PATH.\n"
            "    Pobierz z: https://github.com/einar-saukas/ZX5",
            file=sys.stderr,
        )
        return None
    finally:
        if os.path.exists(tmp_in):
            os.remove(tmp_in)


# =============================================================================
# Główna funkcja konwersji
# =============================================================================

def convert(
    image_path,
    bits_per_pixel,
    *,
    output_base=None,
    generate_all=False,
    bin_output=False,
    asm_output=False,
    colors_output=False,
    dl_output=False,
    compression=None,
    bytes_per_line=8,
    screen_base=0x4000,
):
    """Główna funkcja konwertująca obraz na formaty Atari.

    Args:
        image_path:      Ścieżka do pliku PNG/BMP/GIF.
        bits_per_pixel:  1, 2, 4 lub 8.
        output_base:     Bazowa ścieżka wyjściowa (bez rozszerzenia).
        generate_all:    Generuj wszystkie formaty.
        bin_output:      Generuj .bin.
        asm_output:      Generuj .asm (dane .byte).
        colors_output:   Generuj _colors.asm.
        dl_output:       Generuj _displaylist.asm.
        compression:     'rle', 'zx5' lub None.
        bytes_per_line:  Bajtów na linię w .asm (domyślnie 8).
        screen_base:     Adres bazowy ekranu (np. 0x4000).
    """
    if not os.path.exists(image_path):
        print(f"Błąd: plik '{image_path}' nie istnieje.", file=sys.stderr)
        sys.exit(1)

    stem = Path(image_path).stem
    if output_base is None:
        output_base = stem

    # --- 1. Wczytaj i przygotuj obraz ---------------------------------------
    img, width, height, pixels, palette_rgb = load_image(image_path, bits_per_pixel)
    print(f"Obraz: {width}×{height}, {bits_per_pixel} bpp "
          f"({1 << bits_per_pixel} kolorów)")
    print(f"Paleta: {len(palette_rgb)} kolorów")

    # --- 2. Pakuj piksele --------------------------------------------------
    packed = pack_pixels(width, height, pixels, bits_per_pixel,
                         screen_base_address=screen_base)
    expected_size = (width * height * bits_per_pixel) // 8
    print(f"Dane:   {len(packed)} bajtów (bez paddingu: {expected_size})")

    # --- 3. Generuj etykiety -----------------------------------------------
    safe_label = "".join(c for c in stem if c.isalnum() or c == "_")
    if safe_label and safe_label[0].isdigit():
        safe_label = "_" + safe_label
    if not safe_label:
        safe_label = "Image"
    data_label = safe_label[0].upper() + safe_label[1:] + "Data"

    # --- 4. Generuj pliki wyjściowe ----------------------------------------
    generated = []

    # .bin – surowe dane binarne
    if generate_all or bin_output:
        bin_path = f"{output_base}.bin"
        generate_bin(packed, bin_path)
        generated.append(bin_path)

    # .asm – dane .byte
    if generate_all or asm_output:
        asm_path = f"{output_base}.asm"
        generate_asm_data(packed, asm_path, data_label, bytes_per_line)
        generated.append(asm_path)

    # _colors.asm – kolory
    if generate_all or colors_output:
        colors_path = f"{output_base}_colors.asm"
        generate_asm_colors(palette_rgb, colors_path, stem, bits_per_pixel)
        generated.append(colors_path)

    # _displaylist.asm – Display List
    if generate_all or dl_output:
        dl_path = f"{output_base}_displaylist.asm"
        generate_asm_displaylist(
            width, height, bits_per_pixel, dl_path, stem, data_label,
            screen_base_address=screen_base,
        )
        generated.append(dl_path)

    # --- 5. Kompresja ------------------------------------------------------
    if compression:
        if compression == "rle":
            rle_data = rle_compress(packed)
            rle_path = f"{output_base}.rle"
            with open(rle_path, "wb") as f:
                f.write(rle_data)
            ratio = len(packed) / max(len(rle_data), 1)
            print(f"  ✔ {rle_path}  ({len(rle_data)} bajtów, "
                  f"{ratio:.1f}× mniej niż oryginał)")
            generated.append(rle_path)

            # Generuj też depacker
            depack_path = f"{output_base}_rle_depack.asm"
            generate_rle_asm_depacker(depack_path)
            generated.append(depack_path)

        elif compression == "zx5":
            zx5_in = packed
            zx5_path = f"{output_base}.zx5"
            compress_zx5(zx5_in, zx5_path)
            generated.append(zx5_path)

    # --- 6. Podsumowanie ---------------------------------------------------
    print(f"\nWygenerowano {len(generated)} plików:")
    for g in generated:
        size = os.path.getsize(g)
        print(f"  {g}  ({size} bajtów)")

    return generated


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Konwerter obrazów na formaty Atari 8-bit (ANTIC).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady:
  python img2asm.py title.png 2                    # tylko .asm
  python img2asm.py title.png 2 --all              # .bin + .asm + kolory + DL
  python img2asm.py title.png 2 -c rle             # z kompresją RLE
  python img2asm.py title.png 2 -o ekran.bin       # konkretna nazwa wyjściowa
  python img2asm.py sprite.bmp 1 --bin --colors    # 1 bpp, .bin + kolory
        """,
    )
    parser.add_argument(
        "image",
        nargs="?",
        help="Ścieżka do pliku graficznego (PNG, BMP, GIF).",
    )
    parser.add_argument(
        "bits",
        nargs="?",
        type=int,
        choices=[1, 2, 4, 8],
        help="Liczba bitów na piksel: 1=2 kolory, 2=4 kolory, 4=16, 8=256.",
    )
    parser.add_argument(
        "-o", "--output",
        help="Bazowa ścieżka wyjściowa (bez rozszerzenia) lub konkretna nazwa pliku.",
    )

    # Grupa: formaty wyjściowe
    fmt = parser.add_argument_group("Formaty wyjściowe")
    fmt.add_argument(
        "--all",
        action="store_true",
        help="Generuj wszystkie formaty: .bin, .asm, _colors.asm, _displaylist.asm.",
    )
    fmt.add_argument(
        "--bin",
        action="store_true",
        dest="bin_output",
        help="Generuj surowy plik .bin.",
    )
    fmt.add_argument(
        "--asm",
        action="store_true",
        dest="asm_output",
        help="Generuj plik .asm z danymi .byte.",
    )
    fmt.add_argument(
        "--colors",
        action="store_true",
        dest="colors_output",
        help="Generuj plik _colors.asm z inicjalizacją rejestrów kolorów.",
    )
    fmt.add_argument(
        "--dl",
        action="store_true",
        dest="dl_output",
        help="Generuj plik _displaylist.asm z ANTIC Display List.",
    )

    # Grupa: kompresja
    comp = parser.add_argument_group("Kompresja")
    comp.add_argument(
        "-c", "--compress",
        choices=["rle", "zx5"],
        help="Kompresuj dane wyjściowe (RLE lub ZX5). ZX5 wymaga narzędzia 'zx5' w PATH.",
    )

    # Opcje formatowania .asm
    fmt_grp = parser.add_argument_group("Formatowanie .asm")
    fmt_grp.add_argument(
        "-l", "--bytes-per-line",
        type=int,
        default=8,
        help="Liczba bajtów w jednej linii .byte (domyślnie: 8).",
    )
    fmt_grp.add_argument(
        "--screen-base",
        type=lambda x: int(x, 0),
        default=0x4000,
        help="Adres bazowy ekranu w pamięci Atari (domyślnie: 0x4000). "
             "Akceptuje zapis hex: 0x4000, $4000 lub dziesiętny.",
    )

    # Testy
    parser.add_argument(
        "--test",
        action="store_true",
        help="Uruchom testy jednostkowe algorytmu Display List.",
    )

    args = parser.parse_args()

    if args.test:
        _run_tests()
        return

    if not args.image or args.bits is None:
        parser.error("wymagane argumenty: image, bits")

    # Jeśli nie podano żadnego formatu, domyślnie generuj .asm
    if not any([args.all, args.bin_output, args.asm_output,
                args.colors_output, args.dl_output]):
        args.asm_output = True

    # Jeśli podano konkretną nazwę pliku z rozszerzeniem,
    # użyj jej bazy jako output_base i nadpisz typ wyjścia
    output_base = None
    if args.output:
        p = Path(args.output)
        if p.suffix:
            # Konkretny plik – użyj bazy bez rozszerzenia
            output_base = str(p.with_suffix(""))
            # Nadpisz: tylko ten format
            ext = p.suffix.lower()
            if ext == ".bin":
                args.bin_output = True
                args.asm_output = False
            elif ext == ".asm":
                args.asm_output = True
                args.bin_output = False
        else:
            output_base = args.output

    convert(
        args.image,
        args.bits,
        output_base=output_base,
        generate_all=args.all,
        bin_output=args.bin_output,
        asm_output=args.asm_output,
        colors_output=args.colors_output,
        dl_output=args.dl_output,
        compression=args.compress,
        bytes_per_line=args.bytes_per_line,
        screen_base=args.screen_base,
    )


# =============================================================================
# Testy jednostkowe
# =============================================================================

def _run_tests():
    """Testy algorytmu _compute_dl_segments dla ANTIC E (160×192)."""
    width, height, bpp = 160, 192, 2
    bytes_per_line = (width * bpp) // 8

    test_addrs = [0x2000, 0x3000, 0x4000, 0x5000, 0x6000]

    print("=" * 70)
    print("Testy Display List — ANTIC E (160×192, 40 bajtów/linia)")
    print("=" * 70)

    all_ok = True

    for addr in test_addrs:
        segments = _compute_dl_segments(width, height, bpp, addr)
        total = sum(sc for _, sc, _, _ in segments)

        exact_192 = total == 192
        no_gaps = True

        prev_end = -1
        for ls, sc, _, _ in segments:
            if prev_end >= 0 and ls != prev_end + 1:
                no_gaps = False
                break
            prev_end = ls + sc - 1

        # Sprawdź, czy wszystkie LMS-y wskazują na równe adresy $x000
        all_aligned = all(
            int(lms[1:], 16) & 0x0FFF == 0
            for _, _, _, lms in segments
        )

        ok = exact_192 and no_gaps and all_aligned

        print(f"\nAdres ekranu: ${addr:04X}")
        print(f"  Segmentów:  {len(segments)}")
        for i, (ls, sc, offset, lms) in enumerate(segments, 1):
            print(f"    {i}. LMS={lms}  linie {ls:3d}..{ls+sc-1:3d}  "
                  f"({sc:3d} linii, offset={offset})")

        print(f"  Łącznie linii: {total}/192  {'✓' if exact_192 else '✗'}")
        print(f"  Ciągłość:      {'✓' if no_gaps else '✗ LUKA!'}")
        print(f"  LMS $x000:     {'✓' if all_aligned else '✗'}")
        print(f"  Wynik:         {'✓ OK' if ok else '✗ BŁĄD!'}")

        if not ok:
            all_ok = False

    print("\n" + "=" * 70)
    print(f"Wynik całościowy: {'✓ WSZYSTKIE TESTY OK' if all_ok else '✗ BŁĘDY!'}")
    print("=" * 70)

    return all_ok


if __name__ == "__main__":
    main()