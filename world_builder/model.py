from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict

class ObjectSize(BaseModel):
    width: int = Field(ge=1, le=16)
    height: int = Field(ge=1, le=16)

class InventoryItemDef(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: int = Field(ge=1, le=255)
    description: str
    charset_position: int = Field(ge=0, le=255, alias="charset_position")

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
    secret: bool = False

class ObjectDefinition(BaseModel):
    id: str
    code: int = Field(ge=1, le=255)
    size: ObjectSize
    flags: ObjectFlags
    tiles: List[int]
    tags: List[str] = Field(default_factory=list)

class ObjectInstance(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    object: str
    x: int = Field(ge=0, le=39)
    y: int = Field(ge=0, le=11)
    repeat_x: int = Field(default=1, alias="repeat-x")
    repeat_y: int = Field(default=1, alias="repeat-y")
    
    type: Optional[str] = None
    conditions_met: Optional[str] = Field(default=None, alias="conditions_met")
    conditions_unmet: Optional[str] = Field(default=None, alias="conditions_unmet")
    message_travel: Optional[str] = Field(default=None, alias="message_travel")
    target_region: Optional[str] = Field(default=None, alias="target_region")
    items_required: Optional[List[int]] = Field(default=None, alias="items_required")
    items_provided: Optional[List[int]] = Field(default=None, alias="items_provided")
    cost_of_travel: Optional[int] = Field(default=None, alias="cost_of_travel")
    game_over: Optional[bool] = Field(default=None, alias="game_over")

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

class PortalEntry(BaseModel):
    screen: str
    x: int = Field(ge=0, le=39)
    y: int = Field(ge=0, le=11)

class RegionDef(BaseModel):
    id: str
    name: str
    layout: RegionLayout
    start_screen: str
    music: str
    damage: int = 10
    portal_entries: Dict[str, PortalEntry] = Field(default_factory=dict)
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
    inventory_items: List[InventoryItemDef] = Field(default_factory=list)
    regions: List[RegionDef] = Field(default_factory=list)
