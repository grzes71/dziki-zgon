# Debug Bridge Specification (Spec-Driven Development)

Version: 1.1

---

## Purpose

Debug Bridge is a desktop command-line tool that automates debugging of Atari 8-bit games running in the Altirra emulator.

Its purpose is to expose internal game state in an AI-friendly format.

Debug Bridge is a bridge between:
- MADS
- Altirra
- AI development tools

It is not part of the game engine.

---

## Scope (MVP)

MVP includes:
- launching Altirra automatically
- loading and running one XEX
- waiting for one configured stop condition
- capturing one screenshot
- reading selected symbol values from RAM
- optional full RAM dump
- exporting deterministic JSON and Markdown outputs

MVP excludes:
- breakpoints
- trace logging
- CPU profiling
- watchpoints
- video capture
- multi-shot sessions
- scenario mode execution (post-MVP, architecture-ready)

---

## Technology

- Python 3.12+
- Standard library preferred
- Suggested libraries:
    - pathlib
    - subprocess
    - json
    - dataclasses
    - argparse
    - Pillow
    - pyyaml

Platform model:
- core logic is platform-independent
- emulator adapter may be platform-specific

---

## Emulator Integration Contract

Debug Bridge shall provide an Emulator Adapter interface:

- launch(config) -> session handle
- load_xex(session, path)
- run(session)
- wait_until(session, condition)
- capture_screenshot(session, output_path)
- read_memory(session, start_address, length) -> bytes
- get_metadata(session) -> emulator_version and runtime info
- stop(session)

Reserved for post-MVP scenario execution:
- set_joystick(session, direction)
- clear_joystick(session)
- press_button(session, button)
- release_button(session, button)

Important:
- the adapter must be the only place with Altirra-specific logic
- if Altirra automation is unavailable on a platform, tool must fail with a clear unsupported-platform error code and message

---

## Inputs

Required:
- game.xex
- debug.yaml

Optional:
- game.lab

---

## Configuration (debug.yaml)

### Schema

Required keys:
- emulator.executable: string, absolute or relative path
- game.executable: string, path to XEX
- output.directory: string, output directory path
- capture.screenshot: boolean
- capture.state: boolean

Optional keys:
- wait.mode: enum: frame | timeout | manual
- symbols.file: string
- symbols.include: list of symbol names
- capture.memory_dump: boolean, default false
- wait.frame: integer, required when wait.mode is frame
- wait.timeout_seconds: number, required when wait.mode is timeout
- scenario: list of scenario steps (post-MVP)
- deterministic.seed: integer, default 0
- deterministic.emulator_speed: enum: full | realtime, default realtime
- deterministic.disable_random_inputs: boolean, default true

### Validation rules

- wait.frame > 0
- wait.timeout_seconds > 0
- if symbols.include is provided, symbols.file must be provided
- exactly one control flow method must be configured: wait.mode or scenario
- unknown keys should raise config validation error

---

## Execution Flow

1. validate config
2. resolve input and output paths
3. launch emulator
4. load XEX
5. run
6. wait using configured mode
7. capture artifacts
8. export JSON and report
9. stop emulator
10. exit with status code

---

## Waiting Modes

### frame
- wait until emulated frame counter reaches configured value
- frame counting starts after XEX run starts

### timeout
- wait for wall-clock timeout_seconds from run start

### manual
- wait until emulator process exits

Future:
- breakpoint mode

---

## Scenario Mode (Post-MVP, Architecture Included)

Scenario mode allows deterministic scripted interaction with the game before capture.

Status:
- not implemented in MVP
- configuration, validation hooks, and architecture shall be prepared now

### Scenario Goal

Scenario mode should enable:
- reproducible bug playback
- deterministic regression checks across full toolchain
- AI-driven state reproduction before capture

### Scenario DSL (planned)

Example:

```yaml
scenario:
    - wait_frames: 50
    - joystick: RIGHT
        frames: 40
    - joystick: DOWN
        frames: 20
    - press: FIRE
    - wait_frames: 100
    - capture: screenshot
    - capture: state
```

Supported planned step types:
- wait_frames
- joystick with duration in frames
- press and optional release
- capture actions

### Planned validation rules

- steps must be a non-empty list
- unknown step keys should raise config validation error
- joystick direction must be one of: UP, DOWN, LEFT, RIGHT, NONE
- frame-based step values must be positive integers
- capture action must be one of: screenshot, state, memory_dump

### Planned execution semantics

- each scenario step is executed strictly in order
- frame counters are emulated-frame based, not wall-clock based
- capture steps execute at exact scenario timeline points
- scenario run produces the same JSON outputs for identical inputs/config

---

## Symbol Extraction

- parse MADS LAB file
- resolve symbol name to one address
- address range must be validated against Atari RAM map

Conflict handling:
- missing symbol: warning, value set to null in debug_state.json
- duplicate symbol definitions: error unless identical address
- out-of-range address: warning, value set to null

---

## Memory Reading

- read 1 byte per symbol by default
- future extension may support typed reads (u16, arrays)
- optional full RAM dump:
    - memory.bin
    - exact size and layout must be documented by adapter

---

## Output Artifacts

Output directory contains:
- debug_state.json
- debug_report.md
- screenshots.json
- frame_NNNNNN.png if screenshot enabled
- symbols.json if symbols enabled
- memory.bin if memory dump enabled

---

## JSON Contracts

### debug_state.json

Required top-level fields:
- spec_version: string
- tool_version: string
- emulator: object
- run: object
- capture: object
- symbols: object
- warnings: array of strings

Minimum example:

```json
{
    "spec_version": "1.1",
    "tool_version": "0.1.0",
    "emulator": {
        "name": "Altirra",
        "version": "4.40"
    },
    "run": {
        "wait_mode": "frame",
        "frame": 500,
        "timeout_seconds": null
    },
    "capture": {
        "screenshot": "frame_000500.png",
        "memory_dump": null
    },
    "symbols": {
        "PlayerX": 15,
        "PlayerY": 7,
        "CurrentScreen": 1
    },
    "warnings": []
}
```

### screenshots.json

Map emulated frame number string to screenshot filename:

```json
{
    "500": "frame_000500.png"
}
```

### symbols.json

Map symbol name to numeric address:

```json
{
    "PlayerX": 130,
    "PlayerY": 131,
    "CurrentScreen": 180
}
```

---

## Determinism Requirements

To satisfy deterministic output:
- same input files and config must produce byte-identical JSON outputs
- key order in JSON must be stable
- timestamps in output must be omitted or normalized
- emulator speed mode must be controlled by config
- no nondeterministic/random input injection
- warnings order must be stable

Screenshot determinism is best-effort and may vary by host GPU; JSON determinism is mandatory.

---

## Error Model and Exit Codes

- 0: success
- 2: config validation error
- 3: missing input file
- 4: emulator launch error
- 5: emulator automation error
- 6: symbol parsing error
- 7: capture error
- 8: export error
- 9: unsupported platform/adapter

On failure:
- debug_report.md should still be generated when possible
- report must include failure stage and error details

---

## CLI

Command:
- debug-bridge run --config debug.yaml

Optional overrides:
- --xex path
- --lab path
- --out dir
- --wait-frame N
- --wait-timeout S

CLI override precedence:
- CLI flags override config file

---

## Architecture

debug_bridge/
- cli.py
- config.py
- emulator.py
- scenario.py
- screenshot.py
- symbols.py
- memory.py
- report.py
- exporter.py
- main.py

Module responsibilities:
- single responsibility per module
- no game-specific logic in core modules
- scenario.py owns scenario parsing, validation, and step orchestration (post-MVP)

---

## Quality Gates

- Ruff passes
- Black passes
- mypy passes in strict mode
- unit tests pass

Suggested pinned tool versions in project config.

---

## Test Plan (Minimum)

Unit tests:
- config schema validation
- LAB parser success and error cases
- stable JSON serialization order
- path resolution and output generation
- error code mapping

Integration tests (adapter-mocked):
- full run flow frame mode
- timeout mode
- manual mode
- missing symbol handling
- artifact generation matrix by capture flags

Planned post-MVP integration tests:
- scenario playback with deterministic input timeline
- scenario capture checkpoints
- invalid scenario step validation

Determinism tests:
- two identical runs produce identical debug_state.json and screenshots.json

---

## Acceptance Criteria

Implementation is accepted only if:

- launches Altirra automatically (or returns unsupported platform error with clear message)
- loads and runs XEX
- waits correctly in frame, timeout, and manual modes
- captures screenshot when enabled
- reads symbol addresses from LAB and resolves values from RAM
- exports debug_state.json, screenshots.json, debug_report.md
- produces deterministic JSON outputs for repeated identical runs
- applies defined exit codes on failure
- passes Ruff, Black, mypy strict, and test suite

Scenario mode acceptance is deferred to post-MVP and tracked as a separate milestone.

---

## Milestones

### MVP (current target)

Scope:
- emulator launch and XEX run
- wait modes: frame, timeout, manual
- single screenshot capture
- symbol read from LAB and RAM
- deterministic JSON exports
- Markdown report

Definition of done:
- all MVP acceptance criteria pass
- CI quality gates pass (Ruff, Black, mypy, tests)

### M1: Scenario Mode

Scope:
- implement scenario parser and executor
- deterministic input timeline (joystick/button/wait)
- capture checkpoints inside scenario timeline
- adapter input primitives activated

Definition of done:
- scenario integration tests pass
- deterministic replay confirmed across repeated runs
- scenario-specific acceptance criteria added and passing

### M2: Breakpoints and Advanced Debugging

Scope:
- breakpoint-based stop condition
- optional trace hooks (if supported by adapter)
- richer diagnostics in report and JSON

Definition of done:
- breakpoint workflow stable in integration tests
- error model updated for breakpoint-specific failures
- backward compatibility of output schemas maintained

---

## Design Principles

- Single Responsibility Principle
- deterministic outputs first
- read-only access to emulator state
- AI-friendly structured JSON
- no game-specific logic
- CI/CD friendly