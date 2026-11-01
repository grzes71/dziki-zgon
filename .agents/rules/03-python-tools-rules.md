---
trigger: always_on
---

# Domain: Python Tooling & Build Pipeline

## 1. Architecture & Paradigms
- **Purpose:** You are writing Python scripts for asset conversion, memory mapping, and build automation. Focus on maintainability, clear type hints, and robust error handling.
- **Data Models:** Use `pydantic` v2 or modern `dataclasses` for parsing configuration files (YAML/JSON) and asset definitions.
- **Structure-of-Arrays (SoA):** When compiling data for the 6502 engine, ALWAYS output data in a Structure-of-Arrays format, not Array-of-Structures, to facilitate easy indexed addressing on the Atari.

## 2. Style & Quality
- **Type Hinting:** All functions and methods must have complete Python type hints.
- **Dependencies:** Keep external dependencies minimal and explicitly documented in `requirements.txt`.
- **CLI Design:** Scripts should have clean command-line interfaces (using `argparse` or `click`) and return appropriate exit codes (0 for success, non-zero for failure) to integrate seamlessly with `make`.

## 3. Testing
- **Emulation:** When writing integration tests, use `py65` to emulate the CPU, load the generated binary, and verify memory states against the expected Python models.