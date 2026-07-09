"""
Memory reading utilities.
"""

from typing import Dict, Optional, Tuple
from .emulator import EmulatorAdapter

def read_symbols_from_memory(adapter: EmulatorAdapter, symbols: Dict[str, int]) -> Tuple[Dict[str, Optional[int]], list]:
    """
    Reads symbol values from memory. Returns values dict and warnings list.
    """
    values: Dict[str, Optional[int]] = {}
    warnings: list = []
    
    for name, address in symbols.items():
        if address < 0 or address > 0xFFFF:
            warnings.append(f"Symbol {name} address out of range: {address}")
            values[name] = None
            continue
            
        try:
            data = adapter.read_memory(address, 1)
            if data and len(data) == 1:
                values[name] = data[0]
            else:
                values[name] = None
                warnings.append(f"Failed to read memory for symbol {name} at address {address}")
        except Exception as e:
            values[name] = None
            warnings.append(f"Error reading symbol {name}: {e}")
            
    return values, warnings
