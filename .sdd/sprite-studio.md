# Sprite Studio Specification (Spec-Driven Development)

**Version:** 1.1

## 1. Purpose
Sprite Studio is a desktop GUI application for creating Atari 8-bit Player/Missile Graphics (PMG) sprites.

JSON is the Single Source of Truth.

ASM generation is out of scope for this app and is handled by a separate Sprite Builder.

## 2. Scope

### In scope
- Create/Open/Save sprite projects in JSON.
- Edit 1-bit sprite frames (fixed width 8 px, variable height).
- Manage multiple sprites and multiple animation frames per sprite.
- Live animation preview.
- Onion skin preview.
- Undo/Redo.
- Copy/Paste frame data.
- Flip and Shift operations.

### Out of scope
- ASM export.
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
- `id` (string)
- `width` (int)
- `height` (int)
- `color` (int)
- `animation` (Animation)
- `frames` (array of Frame)

Constraints:
- `id` regex: `^[A-Z0-9_]{1,64}$`
- `id` must be unique within project.
- `width` must be exactly `8`.
- `height` range: `1..256`.
- `color` range: `0..255`.
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
- Allowed chars: `0`, `1`.

## 5. JSON Example (Valid)

```json
{
  "version": 1,
  "sprites": [
    {
      "id": "GERWANT_WALK_LEFT",
      "width": 8,
      "height": 24,
      "color": 88,
      "animation": {
        "frame_duration": 4,
        "loop": true
      },
      "frames": [
        {
          "pixels": [
            "00011000",
            "00111100",
            "01111110",
            "01111110",
            "00111100",
            "00011000",
            "00011000",
            "00111100",
            "01111110",
            "01111110",
            "00111100",
            "00011000",
            "00011000",
            "00111100",
            "01111110",
            "01111110",
            "00111100",
            "00011000",
            "00011000",
            "00111100",
            "01111110",
            "01111110",
            "00111100",
            "00011000"
          ]
        }
      ]
    }
  ]
}
```

Interpretation:
- Each string is one row of 8 pixels.
- `1` means set pixel.
- `0` means clear pixel.

## 6. Validation
Validation runs on:
- Load.
- Save.
- Optional explicit "Validate" action.

Error categories:
- `duplicate_sprite_id`
- `invalid_sprite_id`
- `invalid_width`
- `invalid_height`
- `invalid_color`
- `invalid_animation`
- `invalid_frame_count`
- `invalid_frame_data`

Behavior:
- Load fails on schema/validation errors and project remains unchanged.
- Save is blocked when validation errors exist.
- Error report should include message and JSON path (for example: `sprites[2].frames[0].pixels[10]`).

## 7. Editing Semantics

### 7.1 Pixel editing
- Left click: set pixel to `1`.
- Right click: set pixel to `0`.
- Drag applies current paint mode.

### 7.2 Copy/Paste
- Copy copies full active frame (8 x height).
- Paste replaces full active frame.
- Paste requires matching source/destination heights.

### 7.3 Flip
- Flip Horizontal mirrors each row.
- Flip Vertical reverses row order.
- Operates on active frame only.

### 7.4 Shift
- Shift Left/Right/Up/Down moves pixels by one cell.
- Non-cyclic behavior: shifted-out pixels are dropped, new cells become `0`.
- Operates on active frame only.

### 7.5 Undo/Redo
- History is global for the entire project (modifying pixels, adding sprites, changing height, reordering frames, etc., all share one queue).
- Granularity: one user command = one history entry.
- Minimum history depth: 100 commands.
- Executing a new command after Undo clears Redo stack.
- New/Open project resets history.

### 7.6 Sprite Dimensions
- Changing the `height` of an existing sprite modifies all its frames.
- If height is increased, new rows filled with `0`s are appended to the bottom.
- If height is decreased, rows are cropped from the bottom.
- Modifying height creates an entry in the global Undo/Redo system.

### 7.7 Color Editing
- The `color` property is managed via a color picker in the GUI.
- The selected color is used to render the sprite in both the Pixel Editor and Animation Preview.

## 8. Animation Preview
- Preview renders frames in sequence for active sprite.
- Display time for frame = `frame_duration / preview_fps` seconds.
- Default `preview_fps`: 50.
- Controls: Play, Pause, Stop.
- Stop resets to first frame.
- If `loop=false`, playback stops on last frame.

## 9. Onion Skin
- Shows previous frame relative to active frame.
- Active frame is rendered on top.
- If the first frame is active and the animation is set to `loop`, the onion layer shows the last frame.
- If the first frame is active and `loop` is false, the onion layer is empty.

## 10. GUI
Required panels:
- Sprite list
- Pixel editor (with a Zoom slider to adjust scale)
- Timeline (supports Drag & Drop reordering)
- Properties (edit `id`, `height`, `color` via color picker, `frame_duration`, `loop`)
- Animation preview (with a Zoom slider to adjust scale)

Required interactions:
- Selecting sprite updates timeline, properties, editor, preview.
- Selecting frame updates editor and preview current frame.
- Add/Delete/Duplicate sprite.
- Add/Delete/Duplicate frame.
- Insert frame between existing frames.
- Reorder frames.
- New/Open/Save/Save As.

Unsaved changes flow:
- On close/open/new with dirty state: prompt Save / Discard / Cancel.

## 11. File Format and Persistence
- Default extension: `.sprite.json`.
- Save uses UTF-8 JSON, indent 2 spaces.
- Stable key order in Sprite object: `id`, `width`, `height`, `color`, `animation`, `frames`.
- Atomic save recommended (tmp file + replace).

## 12. Acceptance Criteria
Functional:
- JSON load/save works for valid data.
- Invalid JSON/schema is rejected with clear errors.
- Graphical editing updates frame data correctly.
- Multiple sprites and multiple frames are supported.
- Animation preview works with `frame_duration`.
- Onion skin works as specified.
- Flip/Shift/Copy/Paste follow defined semantics.
- Undo/Redo behavior matches spec.
- Save is blocked on validation errors.

Quality:
- Ruff clean.
- Black clean.
- mypy clean.
- pytest passes.
