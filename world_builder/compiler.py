from pathlib import Path
import sys
from pydantic import ValidationError as PydanticValidationError
from .parser import parse_world_dir
from .validator import WorldValidator, ValidationError
from .asm_generator import AsmGenerator

def compile_world(input_dir: str, output_dir: str) -> bool:
    in_path = Path(input_dir)
    out_path = Path(output_dir)
    
    print(f"Compiling world from '{in_path}' to '{out_path}'...")
    
    try:
        # Parse & Load Model
        world = parse_world_dir(in_path)
        
        # Validate
        validator = WorldValidator(world)
        validator.validate()
        
        # Print warnings
        for warning in validator.warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
            
        # Generate ASM
        generator = AsmGenerator(world, out_path)
        generator.generate()

        stats = generator.get_stats()
        print("\n=== Podsumowanie Pamięci Świata Gry (World Builder) ===")
        print(f"  * Elementy Świata: {stats['num_regions']} regionów | {stats['num_screens']} ekranów | {stats['num_object_defs']} typów obiektów | {stats['placed_objects_count']} postawionych obiektów")
        print(f"  * Rozmiar danych Świata Gry: {stats['total_world_bytes']:,} B".replace(",", " "))
        print(f"    - Definicje obiektów i kafelki: {stats['objects_bytes']:,} B".replace(",", " "))
        print(f"    - Ekrany i postawione obiekty: {stats['screens_bytes']:,} B".replace(",", " "))
        print(f"    - Regiony i palety barw: {stats['regions_bytes']:,} B".replace(",", " "))
        print(f"    - Wyjścia z ekranów: {stats['exits_bytes']:,} B".replace(",", " "))
        print(f"    - Obiekty interaktywne & sekrety: {stats['interactive_bytes'] + stats['secret_bytes']:,} B".replace(",", " "))
        print(f"  * Główny blok pamięci świata ($6800-$9D1F): {stats['main_world_bytes']:,} B / {stats['main_budget']:,} B".replace(",", " "))
        print(f"  * Wolne miejsce na rozbudowę Świata: {stats['free_main']:,} B ({stats['free_main_pct']:.1f}% wolnego miejsca)\n".replace(",", " "))
        
        print("Compilation successful.")
        return True
        
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return False
    except ValidationError as e:
        print(f"VALIDATION ERROR: {e}", file=sys.stderr)
        return False
    except PydanticValidationError as e:
        print(f"SCHEMA VALIDATION ERROR: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"FATAL ERROR: {e}", file=sys.stderr)
        return False
