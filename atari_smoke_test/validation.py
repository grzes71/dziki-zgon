from pathlib import Path
from .exceptions import EmulatorNotFoundError, XexNotFoundError

def validate_emulator_path(emulator_path: str | Path) -> Path:
    """Verifies that the emulator executable exists and is a file."""
    path = Path(emulator_path)
    if not path.is_file():
        raise EmulatorNotFoundError(
            f"Altirra executable not found.\nExpected:\n{path.resolve()}"
        )
    return path

def validate_xex_path(xex_path: str | Path) -> Path:
    """Verifies that the XEX file exists and is a file."""
    path = Path(xex_path)
    if not path.is_file():
        raise XexNotFoundError(
            f"XEX file not found.\nExpected:\n{path.resolve()}"
        )
    return path
