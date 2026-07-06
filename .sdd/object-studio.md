# Object Studio Specification (Spec-Driven Development)

## Purpose
Object Studio is a desktop GUI application for creating reusable Atari ANTIC Mode 5 game objects.

YAML is the single source of truth for object definitions.

## Goals
- Load a raw Atari .fnt charset (1024 bytes, 128 characters).
- Display the charset using configurable ANTIC 4/5 colors.
- Build reusable objects graphically.
- Load existing objects.yaml to edit previously created objects.
- Export objects.yaml.
- Never contain game logic.

## Input
Charset:
- Format: .fnt
- Size: 1024 bytes
- 128 characters
- ANTIC Mode 5 encoding

Project File:
- Format: `objects.yaml` (existing database of objects)

## Color Configuration
Support configuration of all five ANTIC 4/5 colors:
- Background
- Playfield 0
- Playfield 1
- Playfield 2
- Playfield 3 (inverse)

Allow RGB values or Atari color numbers.
Provide sensible defaults.

## Charset Palette
Display all 128 characters in a 32x4 grid.
A selected character becomes the active brush.

## Object Editor
Canvas:
- Maximum size: 8x8 characters
- Recommended limit: 7x7 characters

Editing:
- Paint
- Erase (fills with tile index 0)
- Replace
- Copy/Paste
- Undo/Redo
- Clear

Rules:
- Bounding Box: Width and height are strictly derived from the minimum rectangle enclosing all non-zero tiles on the canvas.
- Empty Tiles: Any unpainted tile falling within the bounding box bounds will be saved as tile index 0 (assumed transparent/empty).

## Object Properties
Each object contains:
- id
- code
- width
- height
- blocking
- interactive

Width and height are calculated automatically.

## YAML Output

Example:

```yaml
objects:
  - id: HOUSE_SMALL
    code: 1
    size:
      width: 4
      height: 2
    flags:
      blocking: true
      interactive: false
    tiles: [1,2,3,4,65,66,163,164]
```

Rules:
- Export tiles row-by-row.
- Tile values are charset indices.
- Export only the rectangle defined by width and height.

## Validation
Errors:
- duplicate id
- duplicate code
- empty object
- invalid tile index
- object exceeds maximum size
- missing charset

Saving must fail on validation errors.

## GUI

Suggested layout:

+-------------------------------------------------------------+
| Objects | Charset | Canvas                   | Properties   |
| List    | Palette |                          |              |
| [+] [-] |         |                          |              |
+-------------------------------------------------------------+
| Preview                                              Zoom   |
+-------------------------------------------------------------+

Recommended technology:
- Python 3.12+
- PySide6 (Qt)
- PyYAML
- Pillow (optional)
- pathlib
- dataclasses

## Architecture

Modules:
- main.py
- models.py
- charset.py
- palette.py
- editor.py
- validation.py
- yaml_export.py
- settings.py

## Internal Model

Charset
  Tile[128]

ObjectDefinition
  id
  code
  width
  height
  flags
  tiles[]

Project
  Charset
  ObjectDefinitions

## Future Extensions
Design for:
- animated objects
- object categories
- thumbnails
- PNG export
- ASM export
- drag & drop to World Studio

## Acceptance Criteria
- Correct ANTIC Mode 5 decoding.
- Five-color preview.
- Graphical object editing.
- YAML matches schema.
- Ruff, Black, mypy clean.
- Unit tests pass.
