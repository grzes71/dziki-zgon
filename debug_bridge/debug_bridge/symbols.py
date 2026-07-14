"""
MADS .lab file parser.
"""
from typing import Dict, List, Optional
from pathlib import Path
import re
from .errors import SymbolError

class LabParser:
    def __init__(self, include_list: Optional[List[str]] = None):
        self.include_list = set(include_list) if include_list else None

    def parse(self, path: str | Path) -> Dict[str, int]:
        path = Path(path)
        if not path.is_file():
            raise SymbolError(f"LAB file not found: {path}")

        symbols: Dict[str, int] = {}
        # MADS LAB format:
        # NAME = $ADDRESS
        # NAME = $ADDRESS (BANK=X)
        # Or label table format:
        # BANK ADDRESS NAME
        # ADDRESS NAME

        assignment_pattern = re.compile(r"^([a-zA-Z0-9_]+)\s*=\s*\$?([0-9a-fA-F]+)")

        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith(";"):
                        continue
                    
                    # Try assignment format
                    match = assignment_pattern.match(line)
                    if match:
                        name = match.group(1)
                        address_hex = match.group(2)
                    else:
                        # Try table format
                        parts = line.split()
                        if len(parts) >= 2:
                            # Is the first part a valid hex string?
                            is_parts0_hex = all(c in "0123456789abcdefABCDEF" for c in parts[0])
                            is_parts1_hex = all(c in "0123456789abcdefABCDEF" for c in parts[1])
                            
                            is_parts1_id = re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", parts[1]) is not None
                            is_parts2_id = len(parts) >= 3 and re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", parts[2]) is not None
                            
                            if len(parts) >= 3 and is_parts0_hex and is_parts1_hex and is_parts2_id:
                                name = parts[2]
                                address_hex = parts[1]
                            elif is_parts0_hex and is_parts1_id:
                                name = parts[1]
                                address_hex = parts[0]
                            else:
                                continue
                        else:
                            continue
                            
                    if self.include_list is not None and name not in self.include_list:
                        continue
                        
                    address = int(address_hex, 16)
                    
                    if name in symbols and symbols[name] != address:
                        raise SymbolError(f"Duplicate symbol definition with different addresses: {name}")
                        
                    symbols[name] = address
        except Exception as e:
            if isinstance(e, SymbolError):
                raise
            raise SymbolError(f"Error parsing LAB file: {e}")

        # Check for missing symbols if an include list was provided
        if self.include_list is not None:
            missing = self.include_list - set(symbols.keys())
            if missing:
                pass

        return symbols

    def resolve_label(self, path: str | Path, label: str) -> str:
        """Resolves a label name to a hex address using a MADS .lab file."""
        if label.startswith("$"):
            return label
        
        symbols = self.parse(path)
        if label in symbols:
            return f"${symbols[label]:04X}"
            
        raise ValueError(f"Label '{label}' not found in '{path}'.")
