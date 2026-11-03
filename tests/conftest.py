import os
from pathlib import Path
import shutil
import subprocess

# Set headless Qt platform by default if not already configured
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def get_mads_executable() -> str:
    """Find MADS assembler executable across Windows and Linux environments."""
    if os.environ.get("MADS"):
        return os.environ["MADS"]
    which_mads = shutil.which("mads")
    if which_mads:
        return which_mads
    if os.path.isfile("/usr/local/bin/mads"):
        return "/usr/local/bin/mads"
    return "c:/Apps/Mad-Assembler-2.1.6/bin/windows_x86_64/mads.exe"


_MADS_EXECUTABLE = get_mads_executable()

# Hook subprocess.run so tests hardcoding Windows MADS path run transparently on Linux
_orig_subprocess_run = subprocess.run


def _patched_subprocess_run(cmd, *args, **kwargs):
    if isinstance(cmd, (list, tuple)) and len(cmd) > 0:
        cmd_str = str(cmd[0]).lower()
        if "mads" in cmd_str:
            cmd = list(cmd)
            cmd[0] = _MADS_EXECUTABLE
    return _orig_subprocess_run(cmd, *args, **kwargs)


subprocess.run = _patched_subprocess_run


def pytest_ignore_collect(collection_path, config):
    """Gracefully ignore PySide6 GUI tests if Qt native system libraries are missing."""
    path_str = str(collection_path)
    if "studio" in path_str or "live_region_view" in path_str:
        try:
            import PySide6.QtWidgets  # noqa: F401
            app = PySide6.QtWidgets.QApplication.instance()
            if app is None:
                app = PySide6.QtWidgets.QApplication(["test", "-platform", "offscreen"])
        except Exception:
            return True
    return False
