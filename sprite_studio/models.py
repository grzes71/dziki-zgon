from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Union

@dataclass
class Frame:
    pixels: List[str] = field(default_factory=list)

@dataclass
class Animation:
    frame_duration: int = 4
    loop: bool = True

@dataclass
class Sprite:
    id: Union[int, str] = 1
    description: str = ""
    width: int = 8
    height: int = 24
    color: int = 0
    color_mode: int = 2  # 2 = 2-color (single player), 4 = 4-color (dual player overlap)
    color2: int = 0      # Color for Player B (Layer 1) in 4-color mode
    animation: Animation = field(default_factory=Animation)
    frames: List[Frame] = field(default_factory=list)

    def is_4color(self) -> bool:
        return self.color_mode == 4

    def get_overlap_color(self) -> int:
        return (self.color | self.color2) & 0xFF

    def get_layer_pixels(self, frame_idx: int, layer: int) -> List[str]:
        """
        Extract 1-bit PMG rows ('0' or '1') for a given layer:
        - layer 0 (Player 0 / A): '1' when pixel is '1' or '3'
        - layer 1 (Player 1 / B): '1' when pixel is '2' or '3'
        """
        if not (0 <= frame_idx < len(self.frames)):
            return []
        target_chars = ('1', '3') if layer == 0 else ('2', '3')
        result: List[str] = []
        for row in self.frames[frame_idx].pixels:
            result.append("".join("1" if c in target_chars else "0" for c in row))
        return result

    @staticmethod
    def combine_layer_frames(p0_frames: List[Frame], p1_frames: List[Frame]) -> List[Frame]:
        """
        Combine two sets of 1-bit frames (Player 0 and Player 1) into 4-color frames.
        Pixel mapping:
          P0=0, P1=0 -> '0'
          P0=1, P1=0 -> '1'
          P0=0, P1=1 -> '2'
          P0=1, P1=1 -> '3'
        """
        max_frames = max(len(p0_frames), len(p1_frames))
        combined: List[Frame] = []

        for f_idx in range(max_frames):
            f0 = p0_frames[f_idx] if f_idx < len(p0_frames) else None
            f1 = p1_frames[f_idx] if f_idx < len(p1_frames) else None

            h0 = len(f0.pixels) if f0 else 0
            h1 = len(f1.pixels) if f1 else 0
            height = max(h0, h1)

            rows: List[str] = []
            for y in range(height):
                r0 = f0.pixels[y] if (f0 and y < h0) else "00000000"
                r1 = f1.pixels[y] if (f1 and y < h1) else "00000000"
                r0 = r0.ljust(8, '0')[:8]
                r1 = r1.ljust(8, '0')[:8]

                combined_row = []
                for x in range(8):
                    b0 = 1 if r0[x] in ('1', '3') else 0
                    b1 = 1 if r1[x] in ('1', '2', '3') else 0
                    val = (b1 << 1) | b0
                    combined_row.append(str(val))
                rows.append("".join(combined_row))
            combined.append(Frame(pixels=rows))
        return combined

@dataclass
class Project:
    version: int = 1
    sprites: List[Sprite] = field(default_factory=list)
