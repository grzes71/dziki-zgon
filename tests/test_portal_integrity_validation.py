import pytest
from world_builder.model import GameWorld, WorldConfig, StartPosition, RegionDef, RegionLayout, ScreenDef, ScreenExits, ObjectInstance, ObjectDefinition, ObjectSize, ObjectFlags, PortalEntry
from world_builder.validator import WorldValidator, ValidationError

def test_world_validator_portal_integrity_success():
    obj_def = ObjectDefinition(
        id="PORT", code=1, size=ObjectSize(width=1, height=1),
        flags=ObjectFlags(interactive=True), tiles=[0]
    )
    
    empty_exits = ScreenExits(north=None, south=None, east=None, west=None)
    
    screen_a = ScreenDef(
        id="S_A", exits=empty_exits,
        objects=[ObjectInstance(object="PORT", x=5, y=5, type="portal", target_region="R_B", message_travel="Go")]
    )
    
    region_a = RegionDef(
        id="R_A", name="Region A", layout=RegionLayout(rows=1, columns=1),
        start_screen="S_A", music="NONE", screens=[screen_a]
    )
    
    screen_b = ScreenDef(id="S_B", exits=empty_exits, objects=[])
    region_b = RegionDef(
        id="R_B", name="Region B", layout=RegionLayout(rows=1, columns=1),
        start_screen="S_B", music="NONE", screens=[screen_b],
        portal_entries={"R_A": PortalEntry(screen="S_B", x=2, y=2)}
    )
    
    world_cfg = WorldConfig(start_region="R_A", start_screen="S_A", start_position=StartPosition(x=0, y=0))
    world = GameWorld(world=world_cfg, objects=[obj_def], regions=[region_a, region_b])
    
    validator = WorldValidator(world)
    validator.validate()  # Should pass clean


def test_world_validator_portal_integrity_missing_portal_entry():
    obj_def = ObjectDefinition(
        id="PORT", code=1, size=ObjectSize(width=1, height=1),
        flags=ObjectFlags(interactive=True), tiles=[0]
    )
    
    empty_exits = ScreenExits(north=None, south=None, east=None, west=None)
    
    screen_a = ScreenDef(
        id="S_A", exits=empty_exits,
        objects=[ObjectInstance(object="PORT", x=5, y=5, type="portal", target_region="R_B", message_travel="Go")]
    )
    
    region_a = RegionDef(
        id="R_A", name="Region A", layout=RegionLayout(rows=1, columns=1),
        start_screen="S_A", music="NONE", screens=[screen_a]
    )
    
    screen_b = ScreenDef(id="S_B", exits=empty_exits, objects=[])
    # Region B does NOT have portal_entries for R_A!
    region_b = RegionDef(
        id="R_B", name="Region B", layout=RegionLayout(rows=1, columns=1),
        start_screen="S_B", music="NONE", screens=[screen_b],
        portal_entries={}
    )
    
    world_cfg = WorldConfig(start_region="R_A", start_screen="S_A", start_position=StartPosition(x=0, y=0))
    world = GameWorld(world=world_cfg, objects=[obj_def], regions=[region_a, region_b])
    
    validator = WorldValidator(world)
    with pytest.raises(ValidationError, match="does not have a PORTAL ENTRY for region 'R_A'"):
        validator.validate()
