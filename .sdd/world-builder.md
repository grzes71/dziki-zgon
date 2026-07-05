# World Builder Specification (SDD)

Version: 1.2

## Goal

Implement a Python 3.12 application named **world-builder**.

The application compiles the game world described in YAML into optimized MADS Assembly include files.

YAML files are the **single source of truth** (SSOT).

Generated ASM files must never be edited manually.

---

# Responsibilities

The World Builder shall:

* Parse YAML world definitions.
* Validate world consistency.
* Build an internal world model.
* Generate MADS Assembly include files.
* Stop the build on validation errors.

It shall NOT contain game logic.

---

# Project Layout & Scoping

```text
world/

    world.yaml
    objects.yaml

    white_field/

        region.yaml

        screens/
            000.yaml
            001.yaml
            002.yaml

    drunk_hare_forest/
    old_wyzima/

```

### Global World Configuration

The file `world/world.yaml` defines global world properties, including the player's initial spawn point.

Example `world/world.yaml`:

```yaml
world:
  start_region: WHITE_FIELD
  start_screen: TAVERN
  start_position:
    x: 5
    y: 5
```

* **start_region**: The `id` of the region where the player begins the game. Must match an existing region directory/`region.yaml`.
* **start_screen**: The logical screen `id` within `start_region` where the player begins. Must match an existing screen.
* **start_position**: The player's initial tile coordinates on `start_screen`. Strictly constrained to `X: 0 to 39`, `Y: 0 to 9`.

### Identifier Uniqueness & Scope

* **Screen IDs**: A screen's `id` (e.g., `TAVERN`) must be **globally unique** across all regions. The YAML filename (e.g., `000.yaml`) is arbitrary and shall not be used as an identifier.
* **Region-Screen Relation**: A screen belongs to the region whose directory contains it. Exits can seamlessly target any screen identifier in any region.

---

# Objects

Global object definitions are stored in `world/objects.yaml`.

Example:

```yaml
objects:

  - id: HOUSE_SMALL
    code: 1
    size:
      width: 4
      height: 3
    flags:
      blocking: true
      interactive: false

  - id: WELL
    code: 3
    size:
      width: 2
      height: 2
    flags:
      blocking: true
      interactive: true

```

### Binary Packing Rules for Objects

* **ObjectSize Byte**: The compiler packs width and height into a single byte by subtracting 1 from each dimension (supporting ranges 1–16 instead of 0–15):
`PackedSize = ((width - 1) << 4) | ((height - 1) & 0x0F)`
* **Flags Byte**: Object boolean flags are packed into a single byte field:
  * **Bit 7**: `blocking` (1 = true, 0 = false)
  * **Bit 6**: `interactive` (1 = true, 0 = false)
  * **Bits 5-0**: Reserved, must be set strictly to `0`.
* **Object Code Range**: The `code` field is a user-assigned numeric identifier in the range `1` to `255`. Code `0` is reserved for an empty tile.
* **Object Definition Indexing**: Object definitions are emitted in `objects.asm` as a Structure of Arrays (SoA). The arrays are sized exactly up to the maximum `code` value encountered. Missing intermediate codes are padded with zeroes (`$00`). This allows the 6502 to perform direct `code`-based hardware indexing without sequential searching.



---

# Region

Each region directory contains exactly one `region.yaml`. The `id` declared inside `region.yaml` must match the containing directory name exactly; a mismatch is a validation error.

Example:

```yaml
id: WHITE_FIELD

name: White Field

layout:
  rows: 4
  columns: 5

start_screen: TAVERN

music: WHITE_FIELD

```

`layout` describes the logical structural screen grid only.

---

# Screens & Exits

Each screen is stored in an individual YAML file under its region's `screens/` subdirectory.

Example `screens/000.yaml`:

```yaml
id: TAVERN

exits:
  north: null
  south: VILLAGE
  west: null
  east: CROSSROADS

objects:

  - object: HOUSE_SMALL
    x: 10
    y: 6

```

### Constraints & Id Assignment

* **RegionId Allocation**: `RegionId`s are global numeric indices assigned automatically by the compiler. They start sequentially from `0` up to the number of regions, sorted in **alphabetical order of the global region string `id`**.
* **ScreenId Allocation**: `ScreenId`s are global numeric indices assigned automatically by the compiler. They start sequentially from `0` up to `254`, sorted in **alphabetical order of the global screen string `id`**. The value `255` ($FF) is reserved as the null/sentinel value for exits.
* **Exit Constraints**: All four cardinal direction keys (`north`, `south`, `east`, `west`) must be explicitly present in the YAML schema.
* **Null Exits**: If an exit is `null`, it must be compiled into the binary sentinel value `$FF` (255). Valid target names are resolved to their global numeric `ScreenId` byte.
* **Optional Fields**: The `objects` array block in a screen file is optional. If missing, it defaults to an empty list.

---

# Validation

The build compiler **SHALL fail** (returning Exit Code `1`) if:

* **Duplicate Identifiers**: Duplicate Region ids, duplicate Screen ids, duplicate Object ids, or duplicate Object `code` values.
* **Region Directory Mismatch**: A region's `id` does not match its containing directory name.
* **Unresolved References**: Unknown ObjectDefinition, an Exit destination targeting a non-existent Screen `id`, or a `start_screen`/`start_region` referencing a non-existent entity.
* **Invalid Spawn Position**: The global `start_position` is outside tile bounds (`X: 0 to 39`, `Y: 0 to 9`).
* **Out-of-Bounds Positions**: Objects whose full footprint (`X + width` or `Y + height`) exceeds screen hardware boundaries. Boundaries are measured in **tile coordinates** (characters), strictly constrained to: `X: 0 to 39`, `Y: 0 to 9`.
* **Structural Errors**: Missing expected YAML files.

The compiler **SHALL emit warnings** (but continue compilation with Exit Code `0`) for:

* Unreachable screens (no exits lead to them).
* Isolated screen groups.
* Overlapping blocking objects on the same coordinate space.

---

# CLI Interface

The application must provide a command-line interface utilizing `argparse`.

### Usage Syntax

```bash
python3 -m world_builder <input_world_dir> <output_asm_dir>

```

* **Behavior**: The output directory must be created automatically if it does not exist.
* **Exit Codes**: Returns `0` on successful compilation (including warnings). Returns `1` on any validation failure or fatal crash.

---

# Output & Binary Layout

The compiler generates 5 clean MADS Assembly files under the designated output directory:

### 1. `objects.asm`

Contains global definitions for game objects stored as parallel arrays (SoA) indexed by Object `code`.

```asm
; Global Object Arrays (Index = Object Code)
MAX_OBJECT_CODE = 3

; PackedSize (W/H)
OBJ_SIZE
    dta $00 ; Code 0 (Empty/Reserved)
    dta $32 ; Code 1 (HOUSE_SMALL, 4x3)
    dta $12 ; Code 2 (TREE_SMALL, 2x3)
    dta $11 ; Code 3 (WELL, 2x2)

; PackedFlags (Bit 7: blocking, Bit 6: interactive)
OBJ_FLAGS
    dta $00 ; Code 0 (Empty/Reserved)
    dta $80 ; Code 1 (HOUSE_SMALL)
    dta $80 ; Code 2 (TREE_SMALL)
    dta $C0 ; Code 3 (WELL)

```

### 2. `regions.asm`

Maps global region properties and provides a 16-bit address lookup table.

```asm
; Global Regions Table
REGION_COUNT = 1

; Pointers Table (Indexed by RegionId)
REGION_POINTERS_LO
    dta <REGION_WHITE_FIELD
REGION_POINTERS_HI
    dta >REGION_WHITE_FIELD

; Region Data Structures
REGION_WHITE_FIELD
    dta 4, 5        ; Rows, Columns layout
    dta 0           ; Start ScreenId (resolved TAVERN = 0)

```

### 3. `exits.asm`

A flat array matching global `ScreenId` offsets containing 4 bytes per screen.

```asm
; Global Exits Table (4 bytes per ScreenId: N, S, W, E)
EXITS_TABLE
    dta $FF, 01, $FF, 02 ; ScreenId 0 (TAVERN): S->VILLAGE(1), E->CROSSROADS(2)
    dta $FF, $FF, $FF, $FF ; ScreenId 1 (VILLAGE)

```

### 4. `screens.asm`

Contains separate data structures representing entity layouts for individual screens, along with a 16-bit lookup table.

```asm
; Screen Pointers Table (Indexed by ScreenId)
SCREEN_POINTERS_LO
    dta <SCREEN_TAVERN
    dta <SCREEN_VILLAGE
    dta <SCREEN_CROSSROADS
SCREEN_POINTERS_HI
    dta >SCREEN_TAVERN
    dta >SCREEN_VILLAGE
    dta >SCREEN_CROSSROADS

; Screen Layout Configurations
SCREEN_TAVERN
    dta 1            ; Object instance count
    ; Instance: Object Code, X, Y
    dta 1, 10, 6    ; HOUSE_SMALL instance

SCREEN_VILLAGE
    dta 0

SCREEN_CROSSROADS
    dta 0

```

### 5. `world.inc`

The master configuration file exporting global symbols, constants, and layout offset mappings.

```asm
; World Builder Master Include File
SCREEN_COUNT = 3

; Global Screen Translation Constants
SCREEN_ID_TAVERN = 0
SCREEN_ID_VILLAGE = 1
SCREEN_ID_CROSSROADS = 2

; Player Spawn Configuration
START_REGION_ID = 0     ; Index of WHITE_FIELD in regions table
START_SCREEN_ID = 0     ; Resolved ScreenId of TAVERN
START_POS_X = 5
START_POS_Y = 5

```

---

# Technical Dependencies

The system must run strictly on native Python 3.12 standard libraries with the exception of structural parsing and data validations:

* `PyYAML` (>= 6.0)
* `pydantic` (>= 2.0) - For strict, automatic data-type model validation.

## Package Structure

The application must be implemented as an importable Python package named `world_builder/` with the following modules, each having a single responsibility:

* `parser.py` — YAML parsing into raw data structures.
* `validator.py` — world consistency validation and error reporting.
* `model.py` — internal `GameWorld` model (`Regions`, `Screens`, `Exits`, `ObjectInstances`, `ObjectDefinitions`).
* `asm_generator.py` — MADS Assembly output generation from the internal model.
* `compiler.py` — orchestration: parse → validate → build model → generate ASM.
* `cli.py` — command-line interface entry point.

---

# Verification & Test Scenarios

The test suite (executed via `pytest`) must enforce a minimum of 90% coverage over the core modules (`parser`, `validator`, `model`, `asm_generator`, `compiler`), including specific automated test blocks:

1. **Happy Path Test**: Verifies successful binary representation parsing of a sample valid multi-region world, including correct resolution of `start_region`, `start_screen`, and `start_position`.
2. **Duplicate Detection Test**: Confirms failure when two screens inside different folders declare the same string `id`.
3. **Out of Bounds Test**: Guarantees compile failure if an object's footprint or the global `start_position` exceeds tile position limits (`X=40` or `Y=10`).
4. **Resolution Verification Test**: Checks that bit-shifting properties for `ObjectSize` and `Flags` match expected Hex value outcomes precisely.
5. **Invalid Spawn Test**: Confirms compile failure when `start_screen` or `start_region` references a non-existent entity.

