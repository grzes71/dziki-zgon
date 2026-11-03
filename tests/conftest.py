import os
from pathlib import Path

# Set headless Qt platform by default if not already configured
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def pytest_ignore_collect(collection_path, config):
    """Gracefully ignore PySide6 GUI tests if Qt native system libraries (e.g. libEGL) are missing."""
    path_str = str(collection_path)
    if "studio" in path_str or "live_region_view" in path_str:
        try:
            import PySide6.QtWidgets  # noqa: F401
        except Exception:
            return True
    return False

