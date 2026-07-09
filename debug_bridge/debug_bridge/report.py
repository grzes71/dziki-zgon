"""
Markdown Report Generation.
"""

from pathlib import Path
from typing import Dict, Any, List

def generate_report(path: str | Path, state: Dict[str, Any]) -> None:
    """
    Generates a markdown debug report from the debug state.
    """
    path = Path(path)
    
    lines = [
        "# Debug Bridge Report",
        "",
        f"**Spec Version:** {state.get('spec_version')}",
        f"**Tool Version:** {state.get('tool_version')}",
        "",
        "## Emulator",
        f"- **Name:** {state.get('emulator', {}).get('name')}",
        f"- **Version:** {state.get('emulator', {}).get('version')}",
        "",
        "## Run Configuration",
        f"- **Wait Mode:** {state.get('run', {}).get('wait_mode')}",
        f"- **Frame:** {state.get('run', {}).get('frame')}",
        f"- **Timeout Seconds:** {state.get('run', {}).get('timeout_seconds')}",
        "",
        "## Captures",
        f"- **Screenshot:** {state.get('capture', {}).get('screenshot')}",
        f"- **Memory Dump:** {state.get('capture', {}).get('memory_dump')}",
        "",
        "## Symbols",
    ]

    symbols = state.get('symbols', {})
    if symbols:
        lines.append("| Symbol | Value (Dec) | Value (Hex) |")
        lines.append("|---|---|---|")
        for name, value in sorted(symbols.items()):
            val_str = str(value) if value is not None else "null"
            hex_str = f"0x{value:02X}" if value is not None else "null"
            lines.append(f"| `{name}` | {val_str} | {hex_str} |")
    else:
        lines.append("*No symbols captured.*")

    warnings: List[str] = state.get("warnings", [])
    if warnings:
        lines.append("")
        lines.append("## Warnings")
        for w in warnings:
            lines.append(f"- {w}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
