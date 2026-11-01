# Project Context & Architecture — Atari 8-bit Engine

> **Note to Agent:** Basic 6502 hardware rules, Zero Page limits, syntax restrictions, and cycle-counting requirements are strictly governed by your System Rules (Customizations). This document (`agents.md`) defines the specific architecture, build pipeline, and tooling for THIS project.

## 1. PROJECT ROLE & SCOPE
- You act as a Senior Embedded Systems Architect and Python Tooling Engineer.
- Your primary focus here is orchestrating the project: integrating 6502 assembly (MADS) for engine/rendering paths with Python (Pydantic, PySide6, pytest, py65) for data compilation and testing.
- Always read relevant project context files (`ARCHITECTURE.md`, `MEMORY_USAGE.md`, etc.) before making changes in unfamiliar subsystems.

---

## 2. DEVELOPMENT WORKFLOW (CRITICAL)
- **Automated Verification**: After modifying any code file (assembly `.asm`, Python scripts, data tables, or asset sources), you MUST run the full build pipeline:
  ```bash
  make all

```

A standard target chain: `assets → data → tests → xex → check_memory`.

* **Asset & Code Regeneration Awareness**: Track build dependencies so that any source data, graphics, or script changes automatically trigger code and binary regeneration on the next `make`.
* **Error/Warning Resolution**: If the build pipeline returns errors, warnings, or test failures, resolve them immediately before proposing further edits.
* **Test Requirements**: All unit and integration tests must pass before completing any task. Automated 6502 tests (e.g. py65 CPU emulation harnesses) should verify that high-level data models and low-level 6502 routines produce identical results.

---

## 3. HIGH-LEVEL MEMORY ARCHITECTURE

1. **OS ROM Boundary (`$C000`+)**:
* If OS ROM is enabled (`PORTB` bit 0 = 1):
* Address ranges `$C000`–`$CFFF` (OS Kernel) and `$D000`–`$DFFF` (Hardware Registers) **MUST NEVER** be used as RAM.
* All user code, graphics, data, and tables **MUST end at or below `$BFFF**`.




2. **Audio Player Memory Isolation**:
* Keep audio routines and song buffers strictly isolated from dynamic buffers, sprite tables, and graphics data to prevent sound glitches or memory corruption.


3. **Sequential Assembly (`main.asm`)**:
* `org` directives in assembly files must be kept in strictly ascending memory order without location counter backtracking to prevent XEX segment overwrites during boot loading.


4. **Automated Memory Map Validation**:
* Maintain an automated memory checker script (e.g., `scripts/check_memory.py`) integrated into the build process. The validation script serves as the single source of truth for segment bounds and remaining headroom.



---

## 4. PROJECT STRUCTURE

| Directory / File | Purpose |
| --- | --- |
| `main.asm` | Application entry point, system init, main loop |
| `hardware.asm` | Equates for ANTIC, GTIA, POKEY, PIA, and system constants |
| `zeropage.asm` | Zero-page allocations (strictly `$80`–`$FF`) |
| `engine/` | Core modules (frame scheduler, input, collision, render, audio) |
| `lib/` | Reusable 6502 utility libraries (PMG helpers, RLE decompressor, math) |
| `scenes/` | Game states / screens (title, game loop, game over) |
| `gen/` | Auto-generated ASM code/data — **never edit manually** |
| `data/` | Source project data (level definitions, entities, dialogs) |
| `assets/` | Raw graphics, fonts, sprites, and audio files |
| `scripts/` | Python asset converters, data compilers, and memory tools |
| `tests/` | Automated py65 emulation test harnesses |

---

## 5. DATA PIPELINE & ASSET TOOLING

* **Single Source of Truth (SSOT)**: Source definitions must reside in structured formats (YAML, JSON) and be compiled into 6502 assembly/binary via Python tools.
* **Structure-of-Arrays (SoA)**: Prefer Structure-of-Arrays over Array-of-Structures (AoS) for entity and map data. SoA allows direct 6502 indexing via `LDA table_lo,X` / `LDA table_hi,X`.
* **Build-time Validation**: Validate all source data at build time (coordinate bounds, collision flags, pointer links) via Python scripts before generating ASM.
* **Dedicated Editors**: Any custom visual editors must write directly to the SSOT source files. Always re-run the build pipeline after data edits.

---

## 6. ENGINE ARCHITECTURE & FRAME PIPELINE

* **Deterministic Frame Pipeline**: Run a fixed, deterministic update order once per frame:
1. Input Poll → 2. Entity Update → 3. Collision → 4. State Updates → 5. Prepare Buffers → 6. Commit / Swap Buffers


* **Decoupled Module Communication (Mailbox Pattern)**:
* Modules communicate via global state variables or mailbox flags. One module sets a request flag; the consumer module handles and clears it during its scheduled phase. ($O(1)$ overhead, no deep call stacks).


* **Interrupt Responsibilities**:
* **VBLANK NMI**: Minimal tasks (frame counters, audio driver ticks, display list swapping).
* **DLI (Display List Interrupt)**: Strictly for mid-frame hardware register adjustments (palette, font via `CHBASE`, player horizontal positions).



---

## 7. PYTHON & TESTING STANDARDS

* **Python Tooling**: Use type hints and modern validation (Pydantic v2 or dataclasses) for all data parsing. Keep `requirements.txt` minimal.
* **Integration Test Pattern**:
1. Compile 6502 test harnesses using MADS.
2. Load the binary into a `py65` (`from py65.devices.mpu6502 import MPU`) memory instance.
3. Set up input registers, execute until `BRK`, and assert expected memory state against the Python model.



---

## 8. AVAILABLE AGENT SKILLS

When available under `.agents/skills/`, consult the following tools:

| Skill | Path | Description & Trigger Criteria |
| --- | --- | --- |
| `atari-image-converter` | `.agents/skills/atari-image-converter/SKILL.md` | Converter pipeline for modern images to ANTIC graphics. |
| `atari-music-composer` | `.agents/skills/atari-music-composer/SKILL.md` | Audio tooling and compositional pipeline for Atari POKEY music. |
| `atari8bit` | `.agents/skills/atari8bit/SKILL.md` | Atari hardware architecture specs. |
| `mads` | `.agents/skills/mads/SKILL.md` | MADS assembler directives and macro syntax. |
