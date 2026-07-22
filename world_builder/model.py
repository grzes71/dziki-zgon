from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

class ObjectSize(BaseModel):
    width: int = Field(ge=1, le=16)
    height: int = Field(ge=1, le=16)

class EnemyDef(BaseModel):
    id: str
    name: str
    damage: int = 1

class EnemyInstance(BaseModel):
    enemy: str
    x: int = Field(ge=0, le=39)
    y: int = Field(ge=0, le=11)
    strategy: str = "vertical"
    speed: str = "medium"
    color: str = "white"

class ObjectFlags(BaseModel):
    blocking: bool = False
    interactive: bool = False

class ObjectDefinition(BaseModel):
    id: str
    code: int = Field(ge=1, le=255)
    size: ObjectSize
    flags: ObjectFlags
    tiles: List[int]

class ObjectInstance(BaseModel):
    object: str
    x: int = Field(ge=0, le=39)
    y: int = Field(ge=0, le=11)

class ScreenExits(BaseModel):
    north: Optional[str]
    south: Optional[str]
    east: Optional[str]
    west: Optional[str]

class ScreenDef(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    exits: ScreenExits
    objects: List[ObjectInstance] = Field(default_factory=list)
    enemies: List[EnemyInstance] = Field(default_factory=list)

class RegionLayout(BaseModel):
    rows: int
    columns: int

class RegionDef(BaseModel):
    id: str
    name: str
    layout: RegionLayout
    start_screen: str
    music: str
    damage: int = 1
    screens: List[ScreenDef] = Field(default_factory=list)
    palette: dict = Field(default_factory=dict)
    # the directory name for matching validation
    _dir_name: str = ""

class StartPosition(BaseModel):
    x: int = Field(ge=0, le=39)
    y: int = Field(ge=0, le=11)

class WorldConfig(BaseModel):
    start_region: str
    start_screen: str
    start_position: StartPosition

class GameWorld(BaseModel):
    model_config = ConfigDict(extra="ignore")
    world: WorldConfig
    objects: List[ObjectDefinition] = Field(default_factory=list)
    enemies: List[EnemyDef] = Field(default_factory=list)
    enemy_colors: dict = Field(default_factory=dict)
    regions: List[RegionDef] = Field(default_factory=list)
