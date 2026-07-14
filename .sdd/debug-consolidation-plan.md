## Plan: Consolidate Altirra Debugging

Unify ownership under the installable `debug_bridge` package while retaining distinct snapshot and breakpoint workflows. Keep `debug-bridge run` compatible as the existing config-driven snapshot command; add a direct `debug-bridge break` command that preserves the useful behavior of `scripts/atdbg.py`. Extract shared Altirra process, command-script generation, symbol resolution, and parsing code, then keep `scripts/atdbg.py` as a compatibility shim for one release cycle.

**Steps**
1. Establish the common Altirra automation foundation inside `debug_bridge/debug_bridge/`, keeping all Altirra-specific command syntax and Windows subprocess behavior behind the existing `EmulatorAdapter` boundary. Extract testable units from `scripts/atdbg.py`: temporary-script/log lifecycle, Altirra invocation and timeout handling, safe embedded-path escaping, software/hardware breakpoint construction, trap-expression mapping, and Altirra log parsing.
2. Consolidate label handling by extending the existing `LabParser` in `debug_bridge/debug_bridge/symbols.py` to expose single-label lookup in both formats already accepted by `scripts/atdbg.py` (assignment and table). Make the breakpoint workflow consume this shared parser rather than preserve `resolve_label()` separately.
3. Refactor `AltirraAdapter` in `debug_bridge/debug_bridge/emulator.py` to use the shared command/session layer for snapshot execution. Correct the capture contract: the generated script must create every configured artifact, particularly the screenshot currently requested by `main.py` but not emitted by the script; retain optional 64 KiB RAM dumping and selected-symbol reads.
4. Add a breakpoint workflow module, e.g. `debug_bridge/debug_bridge/breakpoint.py`, which owns a typed request/result model and coordinates: label resolution, debugger script generation, Altirra execution, log parsing, and JSON serialization. Preserve existing debugging features: `--bp`, `--bx`, `--trap-wsync`, `--trap-dli`, `--trap-vbi`, `--hw-regs`, `--disasm`, repeatable memory dumps, `--timeout`, `--warp`, and verbose diagnostic output.
5. Evolve `debug_bridge/debug_bridge/cli.py` into command-specific parsers. Keep `debug-bridge run --config ...` as a compatibility alias for `snapshot`; add `debug-bridge snapshot --config ...` as the explicit name; add `debug-bridge break --xex ...` with direct breakpoint arguments. Standardize new package-facing names on `--xex` and `--lab`, but let the compatibility shim translate legacy `--rom` and `--lab-file` arguments unchanged.
6. Keep output schemas command-specific and versioned rather than forcing a lossy merged schema. Snapshot mode continues writing `debug_state.json`, `debug_report.md`, image artifacts, and optional `memory.bin` under `--out`; break mode prints the established structured JSON to stdout and optionally writes it to `--output-json`. Use the package exporter for deterministic file output where applicable.
7. Replace `scripts/atdbg.py` with a minimal deprecated forwarding wrapper after parity tests pass. The wrapper invokes the packaged break workflow, maps legacy flags to the new names, keeps exit-code behavior stable, and avoids maintaining a second Altirra implementation. Do not delete it in this change; retire it only after one documented release cycle.
8. Expand automated coverage before and during the refactor. Add unit tests for script creation, path escaping, stop-condition/trap mapping, `.lab` label lookup, CPU/flag/instruction/call-stack/disassembly/hexdump log parsing, and error translation. Add CLI tests for `run`, `snapshot`, and `break` argument routing plus legacy-wrapper translation. Use mocked subprocess execution and fixed Altirra log fixtures, so the suite does not require Altirra.
9. Update user and specification documentation: make `debug_bridge/README.md` the primary CLI reference; update `TOOLS.md` examples to show `snapshot` and `break`; reconcile the Debug Bridge MVP scope in `.sdd/debug-bridge.md`; and mark the standalone atdbg specification/walkthrough as historical migration material. Add a concise migration guide documenting old-to-new commands and planned wrapper removal.

**Relevant files**
- `c:/Users/grzes/Documents/Projects/witcher-atari-game/scripts/atdbg.py` — source of the breakpoint contract, script generation, process launch behavior, and log parser; converted to a compatibility wrapper only after extraction.
- `c:/Users/grzes/Documents/Projects/witcher-atari-game/debug_bridge/debug_bridge/cli.py` — split `run` from command parsing and route `run`/`snapshot`/`break` workflows.
- `c:/Users/grzes/Documents/Projects/witcher-atari-game/debug_bridge/debug_bridge/emulator.py` — retain the adapter API while delegating Altirra interaction to shared infrastructure; fix screenshot generation.
- `c:/Users/grzes/Documents/Projects/witcher-atari-game/debug_bridge/debug_bridge/main.py` — preserve snapshot orchestration and artifact/report behavior.
- `c:/Users/grzes/Documents/Projects/witcher-atari-game/debug_bridge/debug_bridge/symbols.py` — make the canonical MADS `.lab` parser and add exact lookup support.
- `c:/Users/grzes/Documents/Projects/witcher-atari-game/debug_bridge/debug_bridge/errors.py` — consolidate command failures and stable exit-code mapping.
- `c:/Users/grzes/Documents/Projects/witcher-atari-game/debug_bridge/debug_bridge/exporter.py` — reuse deterministic JSON output utilities for persisted results.
- `c:/Users/grzes/Documents/Projects/witcher-atari-game/debug_bridge/tests/test_config.py` and `test_symbols.py` — retain and extend existing validation coverage.
- `c:/Users/grzes/Documents/Projects/witcher-atari-game/debug_bridge/tests/test_breakpoint.py` — new script-generation, parser, and breakpoint-result tests.
- `c:/Users/grzes/Documents/Projects/witcher-atari-game/debug_bridge/tests/test_cli.py` — new command-routing and backward-compatibility tests.
- `c:/Users/grzes/Documents/Projects/witcher-atari-game/debug_bridge/README.md`, `TOOLS.md`, `.sdd/debug-bridge.md`, `.sdd/altirra-auto-debugger-basic.sd` — primary user docs, scope alignment, and migration status.

**Verification**
1. Run the project’s configured Python test command and the Debug Bridge tests from the project virtual environment; verify all existing tests remain green plus the new mock-based workflow tests.
2. Exercise parser and script-generation fixtures to prove the exact breakpoint command chains for software breakpoints, arbitrary hardware expressions, the three predefined traps, hardware-register captures, disassembly, and multiple memory ranges.
3. Run `debug-bridge run --config debug_bridge/debug.yaml` with a valid local Altirra installation and verify `debug_state.json`, `debug_report.md`, requested screenshot, and configured RAM dump/artifacts are actually created.
4. Run `debug-bridge break --xex dziki_zgon.xex --bp <known label> --lab gen/game.lab --output-json <path>` and verify CPU state, resolved breakpoint metadata, and a nonempty JSON report; repeat using one hardware trap.
5. Invoke legacy `python scripts/atdbg.py` with documented examples and confirm it delegates correctly and preserves JSON shape and meaningful exit codes.

**Decisions**
- Consolidation means one implementation/package, not one overloaded configuration model: snapshot and breakpoint remain separate subcommands because their triggers and outputs differ materially.
- `debug-bridge run` is retained as a snapshot alias to avoid breaking current documentation and automation; `snapshot` is the clearer canonical command going forward.
- `break` uses direct CLI flags rather than adding breakpoint syntax to `debug.yaml`; this keeps reproducible snapshot configuration focused and direct debugging ergonomic.
- The existing `atdbg.py` JSON schema remains the break-mode compatibility contract for the first release. Snapshot output remains separately versioned.
- The migration includes the screenshot-capture bug because the refactored shared Altirra execution path must meet the advertised snapshot artifact contract.
- Excluded from this change: full scenario execution, joystick/input control, video capture, multi-shot sessions, emulator abstraction for non-Altirra backends, and removal of the compatibility wrapper.

**Further Considerations**
1. Use `break` rather than `breakpoint` as the canonical new command. It is concise and leaves room for future `watch` or `trace` commands; document `breakpoint` as an optional alias only if that reads better for the team.
2. Do not introduce PyYAML or Pillow into the breakpoint-only path. `debug_bridge` already owns those optional snapshot dependencies, but the core breakpoint parsing/execution modules should remain standard-library based and independently testable.
