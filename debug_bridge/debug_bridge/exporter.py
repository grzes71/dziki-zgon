"""
JSON Exporting.
"""

import json
from pathlib import Path
from typing import Any, Dict

from .errors import ExportError

def export_json(path: str | Path, data: Dict[str, Any]) -> None:
    """
    Exports a dictionary to a JSON file deterministically.
    """
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Deterministic output: sorted keys, indent 4
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, sort_keys=True)
    except Exception as e:
        raise ExportError(f"Failed to export JSON to {path}: {e}")
