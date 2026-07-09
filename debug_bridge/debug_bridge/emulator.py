"""
Emulator Adapter for Altirra.
"""

from abc import ABC, abstractmethod
import subprocess
import tempfile
import os
from pathlib import Path
import shutil
from typing import Optional, Dict

from .errors import EmulatorLaunchError, AutomationError
from .config import DebugBridgeConfig

class EmulatorAdapter(ABC):
    @abstractmethod
    def launch(self, config: DebugBridgeConfig) -> None:
        pass

    @abstractmethod
    def load_xex(self, path: str | Path) -> None:
        pass

    @abstractmethod
    def wait_until(self, mode: str, value: Optional[int] = None) -> None:
        pass

    @abstractmethod
    def read_memory(self, start_address: int, length: int) -> bytes:
        pass

    @abstractmethod
    def capture_screenshot(self, output_path: str | Path) -> None:
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, str]:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass


class AltirraAdapter(EmulatorAdapter):
    def __init__(self):
        self.executable: Optional[Path] = None
        self.xex_path: Optional[Path] = None
        self.temp_dir: Optional[tempfile.TemporaryDirectory] = None
        self.mem_dump_path: Optional[Path] = None
        self.screenshot_path: Optional[Path] = None
        self._memory_cache: Optional[bytes] = None

    def launch(self, config: DebugBridgeConfig) -> None:
        self.executable = Path(config.emulator.executable)
        if not self.executable.is_file():
            raise EmulatorLaunchError(f"Emulator executable not found: {self.executable}")
        
        self.temp_dir = tempfile.TemporaryDirectory(prefix="debug_bridge_")
        self.mem_dump_path = Path(self.temp_dir.name) / "mem.bin"
        self.screenshot_path = Path(self.temp_dir.name) / "screenshot.png"

    def load_xex(self, path: str | Path) -> None:
        self.xex_path = Path(path)
        if not self.xex_path.is_file():
            raise AutomationError(f"XEX file not found: {self.xex_path}")

    def wait_until(self, mode: str, value: Optional[int] = None) -> None:
        if not self.executable or not self.temp_dir:
            raise AutomationError("Emulator not launched.")

        # Build the .atdbg script
        script_path = Path(self.temp_dir.name) / "run.atdbg"
        
        lines = []
        if self.xex_path:
            xex_abs = str(self.xex_path.absolute()).replace('\\', '\\\\')
            # Altirra debug command to load executable is 'l' or just pass via CLI
            # But via script we can use 'l'
            # Actually, it's safer to pass XEX via CLI to let Altirra handle boot
            pass 

        if mode == "frame":
            if value is None or value <= 0:
                raise AutomationError("Frame mode requires a positive frame value.")
            for _ in range(value):
                lines.append("gf")
        elif mode == "timeout":
            frames = int((value or 0) * 50)
            for _ in range(frames):
                lines.append("gf")
        elif mode == "manual":
            # We don't break, we just run. But if we run, the script will execute the dump commands immediately.
            # Manual mode implies the user closes the emulator. We can't dump after user closes.
            # So manual mode is fundamentally incompatible with batch script dumping at exit.
            # For MVP, we will just start Altirra without a script and return empty memory.
            raise AutomationError("Manual wait mode not fully supported for automated artifacts in batch adapter.")
        else:
            raise AutomationError(f"Unknown wait mode: {mode}")

        mem_dump_abs = str(self.mem_dump_path.absolute()).replace('\\', '\\\\')
        screenshot_abs = str(self.screenshot_path.absolute()).replace('\\', '\\\\')

        lines.append(f'.writemem "{mem_dump_abs}" 0 10000')
        
        lines.append(".quit")

        script_path.write_text("\n".join(lines), encoding="utf-8")

        script_abs = str(script_path.absolute()).replace('\\', '\\\\')
        cmd = [
            str(self.executable),
            str(self.xex_path.absolute()) if self.xex_path else "",
            "/debugcmd",
            f".read \"{script_abs}\""
        ]

        import time
        try:
            proc = subprocess.Popen(cmd)
            
            # Altirra does not auto-exit, so we wait for the artifact files to appear.
            # Timeout depends on the number of frames (approx 50 fps).
            timeout_seconds = 10
            if mode == "frame" and value:
                timeout_seconds += value / 50.0
            elif mode == "timeout" and value:
                timeout_seconds += value
                
            start_time = time.time()
            while True:
                if self.mem_dump_path.is_file() :
                    # Let file handles flush
                    time.sleep(0.5)
                    proc.kill()
                    break
                if time.time() - start_time > timeout_seconds:
                    proc.kill()
                    raise AutomationError("Timeout waiting for emulator to generate artifacts.")
                
                # If process died unexpectedly
                if proc.poll() is not None:
                    break
                    
                time.sleep(0.1)
                
        except Exception as e:
            if 'proc' in locals() and proc.poll() is None:
                proc.kill()
            raise AutomationError(f"Failed to launch emulator: {e}")

        # After execution, read the memory dump
        if self.mem_dump_path and self.mem_dump_path.is_file():
            self._memory_cache = self.mem_dump_path.read_bytes()
        else:
            self._memory_cache = b'\x00' * 65536 # Default if dump failed

    def read_memory(self, start_address: int, length: int) -> bytes:
        if not self._memory_cache:
            raise AutomationError("Memory not dumped yet. Ensure wait_until was called.")
        
        if start_address < 0 or start_address + length > len(self._memory_cache):
            # Out of bounds, return zeros or slice what we can
            return b'\x00' * length
            
        return self._memory_cache[start_address:start_address+length]

    def capture_screenshot(self, output_path: str | Path) -> None:
        if not self.screenshot_path or not self.screenshot_path.is_file():
            raise AutomationError("Screenshot not generated. Ensure wait_until was called.")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(self.screenshot_path, output_path)

    def get_metadata(self) -> Dict[str, str]:
        return {
            "name": "Altirra",
            "version": "Unknown (via batch adapter)"
        }

    def stop(self) -> None:
        if self.temp_dir:
            self.temp_dir.cleanup()
            self.temp_dir = None
