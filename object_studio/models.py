from dataclasses import dataclass, field
from typing import List

@dataclass
class ObjectSize:
    width: int = 1
    height: int = 1

@dataclass
class ObjectFlags:
    blocking: bool = False
    interactive: bool = False

@dataclass
class ObjectDefinition:
    id: str
    code: int
    size: ObjectSize = field(default_factory=ObjectSize)
    flags: ObjectFlags = field(default_factory=ObjectFlags)
    tiles: List[int] = field(default_factory=list)

@dataclass
class Project:
    objects: List[ObjectDefinition] = field(default_factory=list)
