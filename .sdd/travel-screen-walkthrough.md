# Walkthrough — Implementation of Travel Screen (Ekran Podróży)

Implemented the 5-second **Travel Screen** interlude shown when Geralt travels between regions using portal objects.

## Key Changes

1. **Asset Pipeline & Shared Charset Consolidation**:
   - Created `img/screens/` containing all 3 full-screen graphics (`game_over-fail.png`, `game_over-success.png`, and `travel.png`).
   - Updated `Makefile` to convert all 3 images in **one single command** into `gen/screens/` (`charset.bin`, `game_over-fail_screen.bin`, `game_over-success_screen.bin`, `travel_screen.bin`).

2. **ANTIC Hardware Alignment Fix**:
   - Relocated `GO_CHARSET` to `$9000` (`CHBASE = $90`). ANTIC hardware in modes 2/4/5 requires charsets to be strictly **1 KB aligned** (multiples of $0400). Address `$9100` was causing ANTIC to ignore lower address bits and misread from `$9000`, causing garbage display.
   - Updated memory placement: `GO_CHARSET` ($9000), `GameOverFail_Data` ($9400), `GameOverSuccess_Data` ($97A0), `TravelScreen_Data` ($9B40).


2. **Travel Screen Engine Module**:
   - Created `engine/travel_screen.asm` exporting `travel_screen_show`, `DLI_Travel_Top`, and `DLI_Travel_Bottom`.
   - Fixed VRAM copy loop offset (`+$300` instead of `+$298`) in `engine/travel_screen.asm` and `scenes/gameover/gameover.asm`, resolving screen map distortion for lines 17–23.
   - Fixed region name string length logic to scan backward from byte 19 down to 0, ensuring internal spaces in region names (e.g. "białe pole", "las pijanego zająca") are included without truncating text at space (`$00`).
   - Uses shared `GO_CHARSET` (`CHBASE = $91`) for rendering the image.
   - Text line dynamically formats `"podróż do <nazwa regionu>"` in **lowercase screen codes** (`p=$70`, `o=$6F`, `d=$64`, `r=$72`, `ó=$5F`, `ż=$5C`).
   - Dynamically calculates length $L_{total} = 10 + L_{name}$ and centers text line at `start_offset = (40 - L_total) / 2` across the 40-character line.
   - DLI #2 renders a 10-line scanline raster rainbow effect on `COLPF2`.
   - Disables PMG (sprites and missiles) DMA (`SDMCTL = $22`, `GRACTL = 0`) during travel and restores them (`SDMCTL = $2E`, `GRACTL = 3`) upon arrival.
   - Runs for 250 frames (5.0s at 50 Hz PAL) via `Engine_WaitFrame` while RMT audio continues in VBI.


3. **Portal & World Integration**:
   - Set `IS_PORTAL_TRANSITION = 1` in `engine/iis.asm` when Geralt activates a portal interactive object.
   - Checked `IS_PORTAL_TRANSITION` in `World_Update` (`engine/world.asm`) to trigger `travel_screen_show` before rendering destination screen.
   - Added `redraw_status_bar` in `scenes/game/game.asm` called by `World_Update` to completely wipe out leftover travel image bytes from `GAME_SCREEN_A2` ($41E0–$422F) and redraw default status line, region name, timer, and inventory icons.

5. **Smooth VBLANK Screen Transitions & Post-Travel VBI Fix**:
   - Resolved screen flickering/mignięcie when transitioning between screens (e.g. `TAVERN` <-> `CROSSROADS`).
   - `World_Update` (`engine/world.asm`) now immediately blanks display DMA (`SDMCTL = 0`, `DMACTL = 0`) at start of transition.
   - Fixed CPU freeze after Travel Screen: `travel_screen_show` previously set `NMIEN = 0`, disabling VBI interrupts and causing `Engine_WaitFrame` to deadlock. `travel_screen_show` now leaves `NMIEN = $40` (VBI active), and `World_Update` restores `NMIEN = $C0` before `Engine_WaitFrame`.
   - Rebuilds VRAM, updates GTIA stage color registers (`update_stage_colors`), and updates PMG while DMA is off.
6. **Charset Animation Suppression During Travel**:
   - Added `travel_screen_active` flag in `engine/travel_screen.asm` set to 1 at start of `travel_screen_show` and 0 at exit.
   - Clears `anim_chars_active_mask = 0` during travel screen preparation.
   - Updated `Engine_FrameHandler` (`engine/engine_frame.asm`) to check `IS_PORTAL_TRANSITION` and `travel_screen_active` and bypass `animate_charset` and `update_animated_charset` during travel interludes.
   - Prevents background VBI routines from mutating font byte memory at `$6400` while `GO_CHARSET` ($9000) is being displayed.







---

## Verification Results

### Automated Tests
- Executed `make all`:
  - `atari_charset_trainer` successfully trained and exported `gen/travel/charset.bin` & `gen/travel/travel_screen.bin`.
  - All 102 unit tests in `pytest tests/` passed (100%).
  - MADS assembled `main.asm` to `dziki_zgon.xex` (32,005 bytes).
  - `check_memory.py` verified memory map validity (ending well below `$BFFF`).
