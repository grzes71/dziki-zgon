import subprocess
import time
from pathlib import Path
from .exceptions import EmulatorLaunchError, EmulatorCrashedError

class AltirraProcess:
    def __init__(self):
        self._process: subprocess.Popen | None = None

    def start(self, emulator_path: Path, xex_path: Path) -> None:
        """Starts the Altirra emulator with the specified XEX file."""
        try:
            # Using /singleinstance to avoid multiple Altirra windows stacking up
            # Using /run to immediately load and run the executable
            cmd = [
                str(emulator_path),
                "/singleinstance",
                "/run",
                str(xex_path)
            ]
            self._process = subprocess.Popen(cmd)
        except OSError as e:
            raise EmulatorLaunchError(f"Altirra could not be started: {e}")

    def wait(self, timeout: float) -> None:
        """Waits for the emulator to run. Raises exception if it crashes early."""
        if not self._process:
            raise EmulatorLaunchError("Process was not started.")
            
        try:
            exit_code = self._process.wait(timeout=timeout)
            # If the process exited before the timeout, it might be a crash
            # Altirra usually stays open unless it crashes or the user closes it.
            if exit_code != 0:
                raise EmulatorCrashedError(f"Altirra terminated unexpectedly with exit code {exit_code}.")
        except subprocess.TimeoutExpired:
            # This is the expected happy path for a smoke test.
            # The emulator is still running happily after the timeout.
            pass

    def terminate(self) -> None:
        """Gracefully terminates the emulator, killing it if necessary."""
        if not self._process:
            return
            
        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
