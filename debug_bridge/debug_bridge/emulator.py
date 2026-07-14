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
from .session import AltirraSession


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
        self.session: Optional[AltirraSession] = None

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
        if not self.executable or not self.temp_dir or not self.xex_path:
            raise AutomationError("Emulator not launched or XEX not loaded.")

        self.session = AltirraSession(self.executable, self.xex_path)

        lines = []
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
            raise AutomationError("Manual wait mode not fully supported for automated artifacts in batch adapter.")
        else:
            raise AutomationError(f"Unknown wait mode: {mode}")

        safe_mem_path = self.session.safe_path(self.mem_dump_path)
        safe_screenshot_path = self.session.safe_path(self.screenshot_path)

        # Correct the capture contract: generate both screenshot and memory dump
        lines.append(f'.saveimage "{safe_screenshot_path}"')
        lines.append(f'.writemem "{safe_mem_path}" 0 10000')
        lines.append(".logclose")
        lines.append(".quit")

        # Determine wait timeout
        timeout_seconds = 10.0
        if mode == "frame" and value:
            timeout_seconds += value / 50.0
        elif mode == "timeout" and value:
            timeout_seconds += value

        # Run script
        self.session.run_script(lines, timeout=timeout_seconds, wait_for_file=self.mem_dump_path)

        # Load memory dump cache
        if self.mem_dump_path.is_file():
            self._memory_cache = self.mem_dump_path.read_bytes()
        else:
            self._memory_cache = b'\x00' * 65536

    def read_memory(self, start_address: int, length: int) -> bytes:
        if not self._memory_cache:
            raise AutomationError("Memory not dumped yet. Ensure wait_until was called.")
        
        if start_address < 0 or start_address + length > len(self._memory_cache):
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
        if self.session:
            self.session.cleanup()
            self.session = None
        if self.temp_dir:
            self.temp_dir.cleanup()
            self.temp_dir = None
