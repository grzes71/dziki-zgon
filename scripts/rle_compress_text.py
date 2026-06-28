#!/usr/bin/env python3
import argparse
import os
import sys

def to_atari_screencode(c):
    val = ord(c)
    if 32 <= val <= 95:
        return val - 32
    elif 96 <= val <= 127:
        return val
    elif 0 <= val <= 31:
        return val + 64
    else:
        return val

def rle_compress(data):
    """Run-Length Encoding (RLE) with $80 EOF marker.
    Format:
      Bit 7 = 1 -> repeated run: bits 6..0 = count - 1 (1..128)
      Bit 7 = 0 -> literal run: bits 6..0 = count - 1 (1..128)
    """
    result = bytearray()
    i = 0
    n = len(data)

    while i < n:
        # Search for repeating bytes
        run_len = 1
        while i + run_len < n and run_len < 128 and data[i + run_len] == data[i]:
            run_len += 1

        if run_len >= 3:
            result.append(0x80 | (run_len - 1))
            result.append(data[i])
            i += run_len
        else:
            # Literal run
            lit_start = i
            i += 1
            while i < n and (i - lit_start) < 128:
                future_run = 1
                while i + future_run < n and future_run < 3 and data[i + future_run] == data[i]:
                    future_run += 1
                if future_run >= 3:
                    break
                i += 1
            lit_len = i - lit_start
            result.append(lit_len - 1)
            result.extend(data[lit_start:i])

    result.append(0x80)  # EOF marker
    return result

def main():
    parser = argparse.ArgumentParser(description="Kompresuje tekst do RLE dla Atari 8-bit")
    parser.add_argument("-i", "--input", required=True, help="Nazwa zasobu ('story' lub 'gameover') lub plik tekstowy")
    parser.add_argument("-o", "--output", required=True, help="Plik wyjściowy .asm")
    args = parser.parse_args()

    # Wczytaj tekst
    if args.input == "story":
        input_file = "texts/story.txt"
    elif args.input == "gameover":
        input_file = "texts/gameover.txt"
    else:
        input_file = args.input

    if not os.path.exists(input_file):
        print(f"Error: Plik {input_file} nie istnieje.", file=sys.stderr)
        sys.exit(1)

    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Przygotuj dane wejściowe
    raw_bytes = bytearray()
    if "story" in input_file.lower():
        # Story oczekuje 8 linii po dokładnie 40 znaków
        for line in lines[:8]:
            line = line.rstrip("\r\n")
            line = line.ljust(40)[:40]
            for c in line:
                raw_bytes.append(to_atari_screencode(c))
        # Upewnij się, że mamy dokładnie 320 bajtów
        while len(raw_bytes) < 320:
            raw_bytes.append(0) # spacja to 0 w screencodes
    elif "gameover" in input_file.lower():
        # Game Over oczekuje dokładnie 32 znaków
        text = "".join(lines).replace("\r", "").replace("\n", "")
        text = text.ljust(32)[:32]
        for c in text:
            raw_bytes.append(to_atari_screencode(c))
    else:
        # Ogólne przetwarzanie plików tekstowych
        text = "".join(lines)
        for c in text:
            raw_bytes.append(to_atari_screencode(c))

    # Kompresuj
    compressed = rle_compress(raw_bytes)

    # Zapisz jako plik .asm
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write("; Plik wygenerowany automatycznie przez rle_compress_text.py\n")
        f.write(f"; Oryginalny rozmiar: {len(raw_bytes)} B, Skompresowany: {len(compressed)} B\n")
        
        # Zapisz bajty w liniach po 8
        for idx in range(0, len(compressed), 8):
            chunk = compressed[idx:idx+8]
            bytes_str = ", ".join(f"${b:02x}" for b in chunk)
            f.write(f"    .byte {bytes_str}\n")

    print(f"Skompresowano {input_file} -> {args.output} ({len(compressed)} B, oszczędność {len(raw_bytes) - len(compressed)} B)")

if __name__ == "__main__":
    main()
