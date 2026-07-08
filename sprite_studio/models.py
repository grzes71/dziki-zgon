from dataclasses import dataclass, field
from typing import List

@dataclass
class Frame:
    pixels: List[str] = field(default_factory=list)

@dataclass
class Animation:
    frame_duration: int = 4
    loop: bool = True

@dataclass
class Sprite:
    id: str = "NEW_SPRITE"
    width: int = 8
    height: int = 24
    color: int = 0
    animation: Animation = field(default_factory=Animation)
    frames: List[Frame] = field(default_factory=list)

@dataclass
class Project:
    version: int = 1
    sprites: List[Sprite] = field(default_factory=list)
