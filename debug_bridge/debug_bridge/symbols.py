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
        # We need to extract NAME and ADDRESS.

        pattern = re.compile(r"^([a-zA-Z0-9_]+)\s*=\s*\$([0-9a-fA-F]+)")

        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith(";"):
                        continue
                    
                    match = pattern.match(line)
                    if match:
                        name = match.group(1)
                        address_hex = match.group(2)
                        
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
                # Warning is handled at the higher level, but we should make sure the caller knows
                pass

        return symbols
