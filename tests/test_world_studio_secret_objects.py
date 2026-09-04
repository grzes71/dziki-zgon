import pytest
import sys
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import Qt, QPointF

from world_studio.widgets.secret_item_dialog import SecretItemSelectionDialog
from world_studio.widgets.screen_canvas import ScreenCanvasWidget
from world_studio.models import (
    ScreenDef, ObjectDefinition, ObjectSize, ObjectFlags, ObjectInstance, RegionDef, InventoryItemDef
)
from world_studio.project_manager import ProjectManager
from world_builder.validator import WorldValidator, ValidationError
from world_builder.model import (
    GameWorld, ObjectDefinition as WBObjectDef, ObjectSize as WBObjectSize,
    ObjectFlags as WBObjectFlags, RegionDef as WBRegionDef, RegionLayout,
    ScreenDef as WBScreenDef, ScreenExits, ObjectInstance as WBObjectInstance,
    WorldConfig, StartPosition
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def test_secret_item_dialog_blocks_duplicate_selection(qapp):
    items = [
        InventoryItemDef(id=1, description="18000 orenów", charset_position=35, consumable=True),
        InventoryItemDef(id=18, description="kompas", charset_position=47, consumable=True),
    ]
    placed_secrets = {
        18: {"region_id": "OLD_WYZIMA", "screen_id": "LOWER_MIDDLE_3", "object": "SECRET2"}
    }

    dialog = SecretItemSelectionDialog(items, initial_item_id=None, placed_secrets=placed_secrets)

    # Find item 18 in combo box
    idx_18 = dialog.combo_items.findData(18)
    dialog.combo_items.setCurrentIndex(idx_18)

    with patch("world_studio.widgets.secret_item_dialog.QMessageBox.warning") as mock_warn:
        dialog._on_accept()
        assert mock_warn.called
        args, _ = mock_warn.call_args
        assert "Przedmiot Secret już istnieje" in args[1]
        assert "kompas" in args[2]
        assert "OLD_WYZIMA" in args[2]
        assert "LOWER_MIDDLE_3" in args[2]
        assert dialog.selected_item_id is None

    # Now select item 1 (which is free)
    idx_1 = dialog.combo_items.findData(1)
    dialog.combo_items.setCurrentIndex(idx_1)
    dialog._on_accept()
    assert dialog.selected_item_id == 1


def test_secret_item_dialog_allows_keeping_own_item_on_edit(qapp):
    items = [
        InventoryItemDef(id=18, description="kompas", charset_position=47, consumable=True),
    ]
    placed_secrets = {
        18: {"region_id": "OLD_WYZIMA", "screen_id": "LOWER_MIDDLE_3", "object": "SECRET2"}
    }

    # Editing existing secret that already owns item 18
    dialog = SecretItemSelectionDialog(items, initial_item_id=18, placed_secrets=placed_secrets)
    dialog._on_accept()
    assert dialog.selected_item_id == 18


def test_screen_canvas_blocks_placing_duplicate_secret_item(qapp):
    canvas = ScreenCanvasWidget()
    pm = ProjectManager()

    secret_obj = ObjectDefinition(
        id="SECRET2",
        code=164,
        size=ObjectSize(width=2, height=2),
        flags=ObjectFlags(blocking=False, interactive=False, secret=True),
        tiles=[0, 0, 0, 0],
        tags=["secret"]
    )
    pm.objects = [secret_obj]
    pm.inventory_items = [
        InventoryItemDef(id=18, description="kompas", charset_position=47, consumable=True)
    ]

    # Screen 1 already has secret with kompas (ID 18)
    screen1 = ScreenDef(
        id="SCREEN_1",
        grid_x=0,
        grid_y=0,
        exits={"north": None, "south": None, "east": None, "west": None},
        objects=[
            ObjectInstance(object="SECRET2", x=10, y=4, items_provided=[18], **{"repeat-x": 1, "repeat-y": 1})
        ]
    )
    # Screen 2 is empty
    screen2 = ScreenDef(
        id="SCREEN_2",
        grid_x=1,
        grid_y=0,
        exits={"north": None, "south": None, "east": None, "west": None},
        objects=[]
    )

    region = RegionDef(
        id="OLD_WYZIMA",
        name="Stara Wyżyma",
        layout={"rows": 1, "columns": 2},
        start_screen="SCREEN_1",
        music="MUSIC"
    )
    pm.regions = {"OLD_WYZIMA": region}
    pm.screens = {"OLD_WYZIMA": {"SCREEN_1": screen1, "SCREEN_2": screen2}}

    canvas.set_data(screen_def=screen2, project=pm, charset=None, region_id="OLD_WYZIMA")
    canvas.active_tool = "SECRET2"

    event = MagicMock()
    event.position.return_value = QPointF(160.0, 160.0)
    event.button.return_value = Qt.LeftButton

    # Attempting to place SECRET2 when all items (18) are taken should show warning and block
    with patch("world_studio.widgets.screen_canvas.QMessageBox.warning") as mock_warn:
        canvas.mousePressEvent(event)
        assert mock_warn.called
        args, _ = mock_warn.call_args
        assert "Brak dostępnych przedmiotów Secret" in args[1]
        assert len(screen2.objects) == 0


def test_world_validator_raises_error_on_duplicate_secret_item():
    obj_def = WBObjectDef(
        id="SECRET2",
        code=164,
        size=WBObjectSize(width=2, height=2),
        flags=WBObjectFlags(blocking=False, interactive=False, secret=True),
        tiles=[0, 0, 0, 0]
    )

    scr1 = WBScreenDef(
        id="SCR1",
        exits=ScreenExits(north=None, south=None, east=None, west=None),
        objects=[
            WBObjectInstance(object="SECRET2", x=10, y=4, items_provided=[18])
        ]
    )
    scr2 = WBScreenDef(
        id="SCR2",
        exits=ScreenExits(north=None, south=None, east=None, west=None),
        objects=[
            WBObjectInstance(object="SECRET2", x=10, y=4, items_provided=[18])
        ]
    )

    reg = WBRegionDef(
        id="REG1",
        name="Region 1",
        layout=RegionLayout(rows=1, columns=2),
        start_screen="SCR1",
        music="MUSIC",
        screens=[scr1, scr2]
    )

    gw = GameWorld(
        world=WorldConfig(
            start_region="REG1",
            start_screen="SCR1",
            start_position=StartPosition(x=0, y=0)
        ),
        regions=[reg],
        objects=[obj_def]
    )

    validator = WorldValidator(gw)
    with pytest.raises(ValidationError) as exc:
        validator.validate()
    assert "Duplicate secret item ID 18" in str(exc.value)
