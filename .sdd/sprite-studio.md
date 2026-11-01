# Sprite Studio Specification (Spec-Driven Development)

**Version:** 2.0

## 1. Purpose
Sprite Studio is a desktop GUI application for creating Atari 8-bit Player/Missile Graphics (PMG) sprites.

JSON is the Single Source of Truth.

ASM generation is out of scope for this app and is handled by a separate Sprite Builder (`scripts/sprite2asm.py`).

## 2. Scope

### In scope
- Create/Open/Save sprite projects in JSON.
- Edit 1-bit (2-color) and 2-bit (4-color GTIA dual-player overlap) sprite frames (fixed width 8 px, variable height).
- Manage multiple sprites and multiple animation frames per sprite.
- Live animation preview with authentic Atari GTIA color palette.
- Onion skin preview.
- Undo/Redo.
- Copy/Paste frame data.
- Flip, Invert and Shift operations.
- Combine two 2-color sprites into one 4-color sprite.
- Split a 4-color sprite into two 2-color sprites (P0 and P1 layers).
- Layer filtering (Combined, P0 layer, P1 layer).

### Out of scope
- Runtime PMG integration into game code.

## 3. Technology
- Python 3.12+
- PySide6 (Qt)
- json
- pathlib
- dataclasses

## 4. JSON Contract

### 4.1 Root object
Required fields:
- `version` (int)
- `sprites` (array of Sprite)

Constraints:
- `version` must be `1`.
- `sprites` may be empty.

### 4.2 Sprite object
Required fields:
- `id` (string or integer)
- `width` (int)
- `height` (int)
- `color` (int)
- `animation` (Animation)
- `frames` (array of Frame)

Optional fields:
- `description` (string, max 40 chars)
- `color_mode` (int: `2` or `4`, default `2`)
- `color2` (int: `0..255`, required when `color_mode` is `4`)

Constraints:
- `id`: unique within project. If string, regex: `^[A-Za-z0-9_]{1,64}$`. If int, `1..255`.
- `width` must be exactly `8`.
- `height` range: `1..256`.
- `color` range: `0..255` (Color for Player A / Layer 0).
- `color2` range: `0..255` (Color for Player B / Layer 1 in 4-color mode).
- `frames` count: `>= 1`.

### 4.3 Animation object
Required fields:
- `frame_duration` (int)
- `loop` (bool)

Constraints:
- `frame_duration` range: `1..255` (ticks).

### 4.4 Frame object
Required fields:
- `pixels` (array of strings)

Constraints:
- Number of rows in `pixels` must equal sprite `height`.
- Each row must have exactly 8 chars.
- Allowed chars:
  - If `color_mode == 2`: `0`, `1`.
  - If `color_mode == 4`: `0`, `1`, `2`, `3`.

## 5. Atari GTIA 4-Color Hardware Model
When two PMG players overlap (e.g. Player 0 and Player 1) and GTIA register `PRIOR` ($D01B) bit 5 is enabled:
- `0`: Transparent (Background)
- `1`: Player 0 color (`COLPM0` / `color`)
- `2`: Player 1 color (`COLPM1` / `color2`)
- `3`: Hardware mix (`COLPM0 OR COLPM1` / `color | color2`)

## 6. Editing Semantics

### 6.1 Pixel editing
- Left click: paint active pen (`0`..`3`).
- Right click: paint `0` (eraser / transparent).
- Pen selection via Palette Bar or keyboard keys `0`, `1`, `2`, `3`.

### 6.2 Layer View
- Combined: full 4-color view.
- Layer P0: highlights bits belonging to Player A (characters `1` and `3`).
- Layer P1: highlights bits belonging to Player B (characters `2` and `3`).

### 6.3 Combine and Split
- **Combine**: merges two 2-color sprites (Layer 0 and Layer 1) into a single 4-color sprite.
- **Split**: decomposes a 4-color sprite into two separate 2-color sprites (`_P0` and `_P1`).

### 6.4 Undo/Redo
- Global history queue for the entire project. Minimum depth: 100 commands.
