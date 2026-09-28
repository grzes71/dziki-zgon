"""scripts/compile_music.py — Kompilator utworów Atari POKEY z JSON do relokowalnego MADS ASM."""
import argparse
from pathlib import Path
from atari_music.ai.client import load_composition_json, generate_music_from_composition
from atari_music.mads_exporter import export_mads_asm


def main():
    parser = argparse.ArgumentParser(description="Kompilacja muzyki Atari POKEY z JSON do MADS ASM")
    parser.add_argument("-i", "--input", required=True, help="Ścieżka do wejściowego pliku JSON")
    parser.add_argument("-o", "--output", required=True, help="Ścieżka do wyjściowego pliku ASM")
    parser.add_argument("-l", "--label", default="song_data", help="Etykieta bazowa danych utworu")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    comp = load_composition_json(input_path)
    res = generate_music_from_composition(comp)
    export_mads_asm(res.pokey_ir, output_path, song_label=args.label)
    print(f"Kompilacja {input_path} -> {output_path} (etykieta: {args.label}) zakończona sukcesem.")


if __name__ == "__main__":
    main()
