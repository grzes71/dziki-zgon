from pathlib import Path
from typing import List

class Charset:
    def __init__(self):
        self.data = bytearray(1024)

    def load(self, path: Path) -> bool:
        try:
            with open(path, "rb") as f:
                data = f.read(1024)
                if len(data) == 1024:
                    self.data = bytearray(data)
                    return True
        except Exception:
            pass
        return False

    def get_tile_pixels(self, tile_index: int) -> List[List[int]]:
        """
        Zwraca matrycę 8x4 pikseli dla podanego indeksu znaku (0-255).
        Zwraca listę 8 wierszy, każdy wiersz to 4 liczby całkowite 
        (0=Background, 1=PF0, 2=PF1, 3=PF2, 4=PF3_INV).
        """
        if tile_index < 0 or tile_index > 255:
            tile_index = 0
            
        inverse = tile_index >= 128
        base_index = tile_index % 128
        
        offset = base_index * 8
        pixels = []
        for y in range(8):
            byte = self.data[offset + y]
            row = []
            for x in range(4):
                # Ekstrakcja 2 bitów (od najwyższych)
                shift = (3 - x) * 2
                val = (byte >> shift) & 0b11
                if val == 3 and inverse:
                    val = 4
                row.append(val)
            pixels.append(row)
        return pixels
