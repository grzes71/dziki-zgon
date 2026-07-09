"""
Execution Flow Coordinator.
"""

import sys
from pathlib import Path
from typing import Optional

from .errors import DebugBridgeError, ExitCode
from .config import DebugBridgeConfig
from .symbols import LabParser
from .emulator import AltirraAdapter
from .memory import read_symbols_from_memory
from .screenshot import generate_screenshots_map
from .exporter import export_json
from .report import generate_report

TOOL_VERSION = "0.1.0"
SPEC_VERSION = "1.1"

def run_bridge(config: DebugBridgeConfig) -> None:
    # 2. resolve input and output paths
    out_dir = Path(config.output.directory)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    symbols_map = {}
    if config.symbols.file:
        # 5. (moved up) parse symbols if configured
        parser = LabParser(include_list=config.symbols.include)
        symbols_map = parser.parse(config.symbols.file)
        if config.symbols.include:
            export_json(out_dir / "symbols.json", symbols_map)

    # 3. launch emulator
    adapter = AltirraAdapter()
    try:
        adapter.launch(config)
        
        # 4. load XEX
        adapter.load_xex(config.game.executable)
        
        # 5. run & 6. wait using configured mode
        wait_val = config.wait.frame if config.wait.mode == "frame" else config.wait.timeout_seconds
        adapter.wait_until(config.wait.mode, wait_val)
        
        warnings = []
        state_capture = {"screenshot": None, "memory_dump": None}
        
        # 7. capture artifacts
        if config.capture.screenshot:
            screenshot_name = f"frame_{config.wait.frame:06d}.png" if config.wait.frame else "screenshot.png"
            screenshot_path = out_dir / screenshot_name
            adapter.capture_screenshot(screenshot_path)
            state_capture["screenshot"] = screenshot_name
            
            screenshots_map = generate_screenshots_map(config.wait.frame or 0, screenshot_name)
            export_json(out_dir / "screenshots.json", screenshots_map)

        if config.capture.memory_dump:
            # We already have mem.bin in the temp dir, we can copy it out
            if adapter.mem_dump_path and adapter.mem_dump_path.is_file():
                import shutil
                shutil.copy(adapter.mem_dump_path, out_dir / "memory.bin")
                state_capture["memory_dump"] = "memory.bin"

        symbol_values, sym_warnings = read_symbols_from_memory(adapter, symbols_map)
        warnings.extend(sym_warnings)
        
        # 8. export JSON and report
        debug_state = {
            "spec_version": SPEC_VERSION,
            "tool_version": TOOL_VERSION,
            "emulator": adapter.get_metadata(),
            "run": {
                "wait_mode": config.wait.mode,
                "frame": config.wait.frame,
                "timeout_seconds": config.wait.timeout_seconds
            },
            "capture": state_capture,
            "symbols": symbol_values,
            "warnings": warnings
        }
        
        export_json(out_dir / "debug_state.json", debug_state)
        generate_report(out_dir / "debug_report.md", debug_state)
        
    finally:
        # 9. stop emulator
        adapter.stop()
