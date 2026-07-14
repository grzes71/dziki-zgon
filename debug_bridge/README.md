# Altirra Debug Bridge

The Debug Bridge provides automation facilities for driving the Altirra Atari emulator, enabling automated snapshot testing, register captures, and scriptable breakpoints.

## Installation

Install the package in your Python environment:
```bash
pip install -e ./debug_bridge
```

## CLI Usage

The package exposes a unified CLI called `debug-bridge` (also runnable via `python -m debug_bridge.cli`).

### 1. Snapshot Mode (`snapshot` or legacy `run`)
Captures an emulated snapshot at a given point in time (frame-based or time-based), writing memory dumps, screenshots, and symbol files to an output directory.

```bash
# Run using config file
debug-bridge snapshot --config debug_bridge/debug.yaml

# Overriding settings
debug-bridge snapshot --config debug.yaml --xex my_game.xex --wait-frame 100 --out custom_out/
```

Options:
* `--config`: Path to `debug.yaml` config (required)
* `--xex`: Override path to Atari executable
* `--lab`: Override path to MADS `.lab` file
* `--out`: Override output directory path
* `--wait-frame`: Step exactly N frames before snapshot
* `--wait-timeout`: Run emulator for N seconds before snapshot

### 2. Breakpoint Mode (`break`)
Executes the emulator and halts on a specified software or hardware breakpoint, capturing the registers, call stack, instruction disassembly, and optional memory ranges. Outputs a clean JSON report.

```bash
# Halt at software breakpoint label
debug-bridge break --xex game.xex --bp START_GAME --lab gen/game.lab

# Halt at hardware write register breakpoint
debug-bridge break --xex game.xex --bx "write($D40E)"

# Halt on WSYNC register write with GTIA/POKEY register dumps
debug-bridge break --xex game.xex --trap-wsync --hw-regs --mem-dump "$0600:L$40"
```

Options:
* `--xex`: Path to `.xex` or `.atr` executable (required)
* `--bp`: Software breakpoint (hex address like `$4000` or label name)
* `--bx`: Hardware breakpoint expression (e.g. `write($D40E)`)
* `--trap-wsync`: Trap on WSYNC ($D40A) writes
* `--trap-dli` / `--trap-vbi`: Trap on DLI / VBI routines
* `--hw-regs`: Dump antic/gtia/pokey/pia hardware registers
* `--disasm N`: Disassemble N instructions at breakpoint location
* `--mem-dump ADDR:L$LEN`: Add memory dump range(s) (e.g., `--mem-dump "$0600:L$40"`)
* `--altirra PATH`: Path to `Altirra64.exe` executable
* `--timeout SECS`: Execution timeout (default: 15)
* `--lab PATH`: Path to MADS `.lab` labels file
* `--output-json PATH`: Save JSON results to file
* `--warp`: Run emulator at max speed until breakpoint is hit
* `--verbose`: Output execution progress to stderr

---

## Configuration File (`debug.yaml`)

You can configure snapshot execution using a YAML file. Here is a fully-commented example:

```yaml
emulator:
  executable: "C:/Apps/Altirra-4.40/Altirra64.exe"  # Path to emulator executable

game:
  executable: "dziki_zgon.xex"  # Target Atari executable

output:
  directory: "out"              # Folder where snapshots and logs are stored

capture:
  screenshot: true              # Take a screen capture (.png)
  memory_dump: true             # Generate a RAM dump (.bin)

wait:
  mode: "frame"                 # Wait mode: "frame" or "timeout"
  frame: 5                      # Number of frames to step before capturing
  timeout_seconds: 10           # Hard time-based timeout limit

symbols:
  file: "dziki_zgon.lab"        # Read MADS labels from this file
  include:                      # Retrieve specific values from RAM at snapshot time
    - "SCORE"
    - "PLAYER_LIVES"
```

---

## Breakpoint Mode Output Format (JSON)

When running `debug-bridge break` (or via the shim), it writes a structured JSON report to `stdout`.

```json
{
    "tool": "altirra-auto-debugger-basic",
    "version": "3.0",
    "status": "ok",
    "breakpoint": {
        "type": "software",
        "address": "$4000",
        "label": "START_GAME"
    },
    "cpu": {
        "PC": 16384,
        "A": 10,
        "X": 255,
        "Y": 32,
        "S": 253,
        "flags": {
            "N": false,
            "V": false,
            "B": true,
            "D": false,
            "I": true,
            "Z": false,
            "C": false
        },
        "current_instruction": "LDA #$0A"
    },
    "call_stack": [
        "$4000",
        "$3050"
    ],
    "memory_dumps": [
        {
            "address": "$0600",
            "length": 64,
            "hex": "A9 FF 8D 00 D0 A9 10 8D 01 D0 A9 20 8D 02 D0 A9 30 8D 03 D0 A9 40 8D 04 D0 A9 50 8D 05 D0 A9 60 8D 06 D0 60",
            "raw_base64": "qf+NAA9BkaARkaAikaMoaMDkaMEkaMJkaMQA"
        }
    ],
    "timestamp": "2026-07-14T09:50:00.123456",
    "duration_seconds": 0.452
}
```

---

## Python API Usage

You can also programmatically drive the adapter directly within Python scripts:

```python
from pathlib import Path
from debug_bridge.emulator import AltirraAdapter
from debug_bridge.config import DebugBridgeConfig

# 1. Load config
config = DebugBridgeConfig.from_yaml("debug_bridge/debug.yaml")

# 2. Launch adapter
adapter = AltirraAdapter()
try:
    adapter.launch(config)
    adapter.load_xex(config.game.executable)

    # 3. Emulate until frame 100
    adapter.wait_until("frame", 100)

    # 4. Programmatically inspect RAM values
    lives_byte = adapter.read_memory(start_address=0x0080, length=1)
    print(f"Player lives remaining: {lives_byte[0]}")

    # 5. Capture screenshot
    adapter.capture_screenshot("out/frame_100.png")
finally:
    adapter.stop()
```

---

## Backward Compatibility

The legacy auto-debugger script `scripts/atdbg.py` is maintained as a forwarding shim. It automatically translates options (`--rom` -> `--xex`, `--lab-file` -> `--lab`) and routes them directly to `debug-bridge break`.

```bash
python scripts/atdbg.py --rom game.xex --bp GAME_LOOP
```
