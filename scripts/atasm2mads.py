#!/usr/bin/env python3
import sys
import re
import argparse

def main():
    parser = argparse.ArgumentParser(description="Convert ATasm syntax to MADS syntax for RMT music integration")
    parser.add_argument("-i", "--input", required=True, help="Input ATasm file")
    parser.add_argument("-o", "--output", required=True, help="Output MADS file")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    lines = content.splitlines()
    converted_lines = []
    has_local = False

    for line in lines:
        # Detect if it contains a .local block
        if re.search(r'(?i)(?<!\w)\.local\b', line):
            has_local = True

        # 1. Replace ATasm .ALIGN 256 with MADS page alignment org pattern
        line = re.sub(r'(?i)(?<!\w)\.(align|ALIGN)\s+256\b', 'org *+$ff & $ff00', line)

        # 2. Replace .word or .WORD directives with dta a(...)
        line = re.sub(
            r'(?<!\w)\.(word|WORD)\b\s*([^;\n]+)',
            lambda m: f"dta a({m.group(2).strip()})",
            line
        )

        # 3. Replace .byte or .BYTE directives with dta
        line = re.sub(r'(?i)(?<!\w)\.(byte|BYTE)\b', 'dta', line)

        # 4. In rmtplayr.asm, update the include for rmtFeat.asm to music/rmt_feat.asm
        line = re.sub(r'(?i)icl\s+["\']rmtFeat\.asm["\']', 'icl "music/rmt_feat.asm"', line)

        # 5. Comment out duplicate PLAYER definitions inside player routines
        line = re.sub(r'(?i)^\s*PLAYER\b\s+(equ|=)\s+\S+', '; PLAYER defined externally', line)

        converted_lines.append(line)

    if has_local:
        converted_lines.append(".endl")

    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(converted_lines) + "\n")

    print(f"Successfully converted {args.input} -> {args.output}")

if __name__ == "__main__":
    main()
