from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict

class ObjectSize(BaseModel):
    width: int = Field(ge=1, le=16)
    height: int = Field(ge=1, le=16)

class EnemyDef(BaseModel):
    id: str
    name: str

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
    model_config = ConfigDict(populate_by_name=True)
    
    object: str
    x: int = Field(ge=0, le=39)
    y: int = Field(ge=0, le=11)
    repeat_x: int = Field(default=1, alias="repeat-x")
    repeat_y: int = Field(default=1, alias="repeat-y")

class ScreenExits(BaseModel):
    north: Optional[str] = None
    south: Optional[str] = None
    east: Optional[str] = None
    west: Optional[str] = None

class ScreenDef(BaseModel):
    id: str
    grid_x: Optional[int] = None
    grid_y: Optional[int] = None
    exits: ScreenExits = Field(default_factory=ScreenExits)
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

class StartPosition(BaseModel):
    x: int = Field(ge=0, le=39)
    y: int = Field(ge=0, le=11)

class WorldConfig(BaseModel):
    start_region: str
    start_screen: str
    start_position: StartPosition
