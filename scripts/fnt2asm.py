#!/usr/bin/env python3
import argparse
import os
import sys

def main():
    parser = argparse.ArgumentParser(description="Convert raw Atari 8-bit .fnt to MADS-compatible .asm format")
    parser.add_argument("-i", "--input", required=True, help="Path to the input raw .fnt file")
    parser.add_argument("-o", "--output", required=True, help="Path to the output .asm file")
    parser.add_argument("-l", "--label", default="FontData", help="Assembly label name (default: FontData)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' does not exist.", file=sys.stderr)
        return 1

    try:
        with open(args.input, "rb") as f:
            data = f.read()
    except Exception as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        return 1

    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    try:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(f"\t; Size: {len(data)} bytes\n")
            # Write 8 bytes per DTA statement
            for i in range(0, len(data), 8):
                chunk = data[i:i+8]
                bytes_str = ",".join(str(b) for b in chunk)
                if i == 0:
                    f.write(f"{args.label} DTA {bytes_str}\n")
                else:
                    f.write(f"\tDTA {bytes_str}\n")
    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        return 1

    print(f"Successfully converted '{args.input}' ({len(data)} bytes) to '{args.output}'")
    return 0

if __name__ == "__main__":
    sys.exit(main())
