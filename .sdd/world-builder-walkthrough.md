# World Builder Implementation Walkthrough

The `world-builder` compiler has been successfully implemented and tested according to the specification. The entire pipeline—from parsing YAML to outputting optimized MADS Assembly files—is now fully functional.

## Core Architecture

The compiler has been built as a highly structured Python package located in the `world_builder/` directory, adhering strictly to Single Responsibility Principles:

- **`model.py`**: Utilizes `pydantic` to enforce a strict data schema (`GameWorld`, `RegionDef`, `ScreenDef`, etc.). This ensures that all inputs match expected data types and structural rules immediately upon loading.
- **`parser.py`**: Discovers files traversing the `world/` directory tree, dynamically discovering regions and screens based on folder layouts.
- **`validator.py`**: Performs cross-referential validation. It enforces global ID uniqueness, out-of-bounds validations (calculating the full footprint based on width and height offsets), reference resolving, and overlap checking.
- **`asm_generator.py`**: The heart of the exporter. It transforms the in-memory Python models into raw 6502-optimized tables. It automatically generates parallel arrays (SoA layout) for objects to enable blazing-fast indexing `LDA OBJ_SIZE,x`, and auto-generates memory pointer tables (LO/HI) for screens and regions.
- **`cli.py` & `compiler.py`**: High-level orchestrators that allow standard CLI invocation via `python -m world_builder`.

## 6502 Assembly Generation Output

The generator adheres to your latest requirements:

- **Object Array Format**: Missing `code` entries are cleanly padded with zero bytes, making direct hardware indexing completely safe. Size calculations correctly use the `width-1` and `height-1` bit-shifting methodology.
- **Global Pointers**: The assembler automatically manages pointers. Example generated output in `screens.asm` will now look like this:
  ```asm
  SCREEN_POINTERS_LO
      dta <SCREEN_CROSSROADS
      dta <SCREEN_TAVERN
  SCREEN_POINTERS_HI
      dta >SCREEN_CROSSROADS
      dta >SCREEN_TAVERN
  ```

## Automated Testing

An automated test suite was constructed under `tests/test_world_builder.py`. It utilizes a temporary directory to build a mock YAML environment containing a Tavern and Crossroads in a test region.

All mandatory tests explicitly pass:
1. **Happy Path**: Confirms a clean build from YAML directly into the 5 final `.asm` files.
2. **Duplicate Detection**: Safely catches when two identical Screen IDs are declared.
3. **Out of Bounds Footprint Test**: Throws an exception when a large object breaches the right edge limit (X + Width > 40).
4. **Resolution Verification**: Validates the 4-bit size subtraction shifting precisely matches hex logic (`PackedSize = ((W-1)<<4) | ((H-1)&0x0F)`).
5. **Invalid Spawn Reference**: Successfully blocks compilation when pointing the start coordinates to a non-existent entity.

## Usage

You can now start invoking the builder whenever you need to compile your `.yaml` maps:
```bash
python -m world_builder path/to/world path/to/output_dir
```
