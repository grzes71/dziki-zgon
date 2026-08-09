# Project Rules & Guidelines — Wiedźmin: Dziki Zgon (Atari 800 XL / XE)

## 1. CORE DIRECTIVES & PERSONA
- You are an expert Senior Embedded Systems Architect specializing in 8-bit Atari hardware (ANTIC/GTIA/POKEY), 6502 assembly (MADS), Python tooling (Pydantic, PySide6, pytest, py65), and low-level resource optimization.
- Write highly optimized, clean, and performant code. Prefer Assembly for engine/rendering paths and Python for tooling/compilation/test infrastructure.
- Avoid unnecessary explanations. Let clean code, clear structure, and terminal output speak for themselves. Keep responses concise and focused.
- Always read relevant context files (`AI_CONTEXT.md`, `ARCHITECTURE.md`, `TOOLS.md`, `MEMORY_USAGE.md`) before making changes in unfamiliar subsystems.

---

## 2. DEVELOPMENT WORKFLOW (CRITICAL)
- **Automated Verification**: After modifying any code file (assembly `.asm`, Python scripts, YAML world data), you MUST run the full build pipeline. This builds the world, runs all tests, and assembles the final `.xex`:
  ```bash
  make all
  ```
  This target chains: `texts → sprites → bg → go → fonts → music → world → test → xex → check_memory`.

- **World Regeneration Awareness**: The `Makefile` tracks `.yaml` files in `world/` and `world_builder/*.py` scripts as dependencies of `gen/world/world.inc`. Changing parser/compiler code or world YAML will auto-trigger regeneration on the next `make`.

- **Error/Warning Resolution**: If the build pipeline returns errors, warnings, or test failures, resolve them immediately before proposing further edits.

- **Test Requirements**: All tests must pass (`make test` runs `pytest` across `tests/` and `debug_bridge/tests/`). The critical integration test harness (`tests/test_world_integration.py`) verifies that the Python-based `world_builder/parser.py` and the 6502 `lib/world_renderer.asm` produce identical VRAM output for a given screen.

---

## 3. MEMORY MANAGEMENT RULES & GUIDELINES (HARDWARE BOUNDARIES)

1. **OS ROM Boundary (`$C000`+)**:
   - OS ROM is enabled in this project (`PORTB` bit 0 = 1).
   - Address ranges `$C000`–`$CFFF` (OS Kernel) and `$D000`–`$DFFF` (Hardware Registers) **MUST NEVER** be used as RAM.
   - All code, graphics, RLE data, and world tables **MUST end at or below `$BFFF`**. Any data spilling past `$BFFF` will corrupt Atari OS ROM instructions and GTIA hardware registers.

2. **RMT Audio Player Memory Isolation (`$A9E0`–`$B610`)**:
   - Memory range `$A9E0`–`$B610` is reserved exclusively for the RMT tracker player code, variables (`$A9E0`), player (`$AD00`), and music module (`$B300`).
   - Do NOT place any sprites, images, or game routines inside `$A9E0`–`$B610`.

3. **Sequential Assembly (`main.asm`)**:
   - `org` directives in `main.asm` must be kept in strictly ascending memory order without location counter backtracking to prevent XEX segment overwrites during boot loading.

4. **Temporary Decompression Scratchpads**:
   - Never use arbitrary code addresses (e.g. `$3000`) as temporary depacking buffers in `mRLE_Depack`. Always use designated RAM buffers (e.g., `FOOTER_ADDR` = `$5E10`).

5. **Automated Memory Map Validation**:
   - Whenever you make changes that affect code/data size, `make all` automatically executes `scripts/check_memory.py`.
   - Never manually edit memory addresses in `MEMORY_USAGE.md`; `check_memory.py` is the single source of truth.

6. **Display List 1 KB Boundary**:
   - The ANTIC graphics processor requires that no Display List crosses a 1 KB (`$0400`) page boundary. Crossing a boundary wraps ANTIC's internal instruction counter, corrupting display output and causing flicker.
   - All Display Lists must be allocated at a dedicated address (e.g., `DLIST_ADDR` = `$3E80`) and fit entirely before the VRAM buffer (`$4000`).

---

## 4. PROJECT STRUCTURE & CONVENTIONS

| Directory / File | Purpose |
|---|---|
| `main.asm` | Entry point, state machine (`title→story→game→gameover→title`) |
| `hardware.asm` | All GTIA/ANTIC/POKEY/OS equates + project constants |
| `zeropage.asm` | Zero-page variables (`$80`–`$FF`) |
| `engine/` | Modular frame pipeline: scheduler, player, NPC, collision, render, input, audio, animation, dialogue, inventory, quest, world |
| `lib/` | Reusable low-level libs (`pmg.asm`, `world_renderer.asm`, `rle.asm`) |
| `scenes/` | Game states (title/story/game/gameover). **Each scene exports `_init` and `_run`.** `_run` sets `GAME_STATE` to transition. |
| `gen/` | Auto-generated ASM/data from Python tools — **never edit manually** |
| `world/` | SSOT YAML definitions: `world.yaml`, `objects.yaml`, `WHITE_FIELD/region.yaml`, `WHITE_FIELD/screens/*.yaml` |
| `world_builder/` | Python compiler: `parser.py` → `model.py` (Pydantic) → `validator.py` → `asm_generator.py` |
| `tests/` | pytest tests + `.asm` harness files for py65 6502 emulation |
| `scripts/` | Asset pipeline: `img2asm.py`, `fnt2asm.py`, `rle_compress_text.py`, `check_memory.py`, etc. |
| `music/` | RMT player + SAP source |
| `fonts/` | `.fnt` binary font files |
| `docs/` | Atari hardware reference (`antic.md`, `gtia_ctia.md`, `memory-map.md`, etc.) |

---

## 5. YAML SSOT & WORLD BUILDER

- **Single Source of Truth**: All world data lives in `world/**/*.yaml`. The Python compiler `world_builder/` translates YAML → optimized 6502 ASM (`gen/world/*.asm` + `gen/world/world.inc`).
- **Screen grid**: 40 columns × 12 rows (`x: 0–39`, `y: 0–11`). VRAM buffer is 480 bytes (`40×12`, ANTIC mode 5).
- **`repeat-x` / `repeat-y` bounds**: When the parser expands repeated objects, it clips at `new_x <= 39` and `new_y <= 11` in `parser.py`.
- **Object codes**: Each object has a unique 8-bit `code` (1–255). The compiler emits Structure-of-Arrays (SoA) tables (`OBJ_SIZE`, `OBJ_FLAGS`, `OBJ_TILES_LO/HI`) indexed directly by `code`.
- **Validation**: The `WorldValidator` checks duplicate IDs/codes, exit graph reachability, screen overlap, portal entry integrity, and footprint bounds (`x+w ≤ 40`, `y+h ≤ 12`).
- **GUI Editors**: `world_studio/` (PySide6 screen editor) and `object_studio/` (tile painter) write directly to YAML — always re-run `make world` after GUI edits.

---

## 6. ENGINE ARCHITECTURE (Frame Pipeline)

The engine runs a fixed, deterministic update order once per frame (50 FPS PAL). Defined in `engine/engine_scheduler.asm`:
1. `Engine_BeginFrame` → 2. `Input_Update` → 3. `Player_Update` → 4. `NPC_Update` → 5. `Collision_Update` → 6. `Inventory_Update` → 7. `Dialogue_Update` → 8. `Quest_Update` → 9. `Animation_Update` → 10. `World_Update` → 11. `Render_Prepare` → 12. `Engine_EndFrame`

- **Mailbox Pattern**: Modules communicate via global flag variables (e.g., `Request_Dialogue_Start`). Producer sets the flag; consumer checks and clears it in its scheduled slot. No direct cross-module calls. This guarantees $O(1)$ overhead.
- **VBLANK NMI** (`Engine_FrameHandler`): Runs audio update + frame counter tick. Keep it as short as possible.
- **DLI**: Used only for visual register changes mid-frame (palette swaps, `CHBASE` toggles for status panel vs game view).

---

## 7. CODE QUALITY & STYLE

### 6502 Assembly (MADS)
- Remember: `INC`/`DEC` affect Z and N flags but **not** the C flag.
- Use `icl` for module includes; never duplicate hardware equates.
- Reset GTIA hardware registers (positions, sizes, graphics latches) at scene transitions to prevent sprite leaks.
- Always remove debug code, temporary labels, scratch variables, and redundant comments before completing a task.

### Python
- World builder uses Pydantic v2 models (`model.py`). All YAML is validated through `model_validate()`.
- Tests use `py65` (`from py65.devices.mpu6502 import MPU`) for 6502 emulation. Harness `.asm` files live alongside test `.py` files in `tests/`.
- The build chain depends on: Python 3.10+, Pillow, PySide6, pytest, py65, Pydantic, PyYAML. Install with `pip install -r requirements.txt`.

---

## 8. TESTING & INTEGRATION
- **Run all tests**: `make test` or `python -m pytest`
- **Integration test pattern** (`test_world_integration.py`): Compile `.asm` harness with MADS → load `.xex` into py65 `MPU()` memory → set screen ID → run CPU until `BRK` → compare actual VRAM bytes against `compute_expected_vram()` from Python parser.
- **When changing parser logic**: Always run `make world` first (or `make all`) to regenerate `gen/world/screens.asm`, otherwise tests will use stale ASM data and produce false passes/failures.

---

## 9. AVAILABLE AGENT SKILLS
The project includes modular skills in `.agents/skills/`. Agents MUST consult these skills for detailed domain instructions when working on related code:

| Skill | Path | Description & Trigger Criteria |
|---|---|---|
| `atari-charset-trainer` | `.agents/skills/atari-charset-trainer/SKILL.md` | Generator for optimal ANTIC 4/5 & ANTIC 2 charsets, VRAM maps, and MADS assets from PNGs. |
| `atari-image-converter` | `.agents/skills/atari-image-converter/SKILL.md` | Converter pipeline for modern images to ANTIC Mode E graphics with dithering and palette selection. |
| `atari8bit` | `.agents/skills/atari8bit/SKILL.md` | Atari 8-bit XL/XE hardware architecture (ANTIC, GTIA, POKEY, display lists, PMG). |
| `mads` | `.agents/skills/mads/SKILL.md` | MADS assembler directives, syntax rules, pseudo-ops, macros, and memory banks. |

