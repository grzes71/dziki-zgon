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
