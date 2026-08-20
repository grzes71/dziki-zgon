import pytest
import yaml
from pathlib import Path
from world_studio.project_manager import ProjectManager
from world_studio.models import InventoryItemDef
from world_builder.parser import parse_world_dir

def test_inventory_items_load_save(tmp_path):
    world_dir = tmp_path / "world"
    world_dir.mkdir(parents=True, exist_ok=True)
    
    # Create minimal world.yaml
    (world_dir / "world.yaml").write_text("world:\n  start_region: R1\n  start_screen: S1\n  start_position: {x: 1, y: 1}\n", encoding="utf-8")
    (world_dir / "objects.yaml").write_text("objects: []\n", encoding="utf-8")
    (world_dir / "enemies.yaml").write_text("enemies: []\n", encoding="utf-8")

    pm = ProjectManager()
    assert pm.load_project(world_dir) is True
    assert len(pm.inventory_items) == 0

    # Add items to PM
    item1 = InventoryItemDef(id=1, description="Klucz do kwatery", charset_position=15, consumable=True)
    item2 = InventoryItemDef(id=2, description="Mieszek złota", charset_position=20, consumable=False)
    pm.inventory_items = [item1, item2]

    # Save project
    assert pm.save_project() is True

    items_yaml_path = world_dir / "items.yaml"
    assert items_yaml_path.exists() is True

    # Verify content of items.yaml
    content = items_yaml_path.read_text(encoding="utf-8")
    assert "Klucz do kwatery" in content
    assert "charset_position: 15" in content
    assert "consumable: true" in content or "consumable: True" in content or "consumable: false" in content

    # Reload in fresh ProjectManager
    pm2 = ProjectManager()
    assert pm2.load_project(world_dir) is True
    assert len(pm2.inventory_items) == 2
    assert pm2.inventory_items[0].id == 1
    assert pm2.inventory_items[0].description == "Klucz do kwatery"
    assert pm2.inventory_items[0].charset_position == 15
    assert pm2.inventory_items[0].consumable is True
    assert pm2.inventory_items[1].id == 2
    assert pm2.inventory_items[1].description == "Mieszek złota"
    assert pm2.inventory_items[1].consumable is False

def test_world_builder_parse_items_yaml(tmp_path):
    world_dir = tmp_path / "world"
    world_dir.mkdir(parents=True, exist_ok=True)
    
    (world_dir / "world.yaml").write_text("world:\n  start_region: R1\n  start_screen: S1\n  start_position: {x: 1, y: 1}\n", encoding="utf-8")
    (world_dir / "objects.yaml").write_text("objects: []\n", encoding="utf-8")
    
    items_data = {
        "items": [
            {"id": 1, "description": "Miecz wiedźmiński", "charset_position": 40, "consumable": False},
            {"id": 2, "description": "Eliksir Jaskółka", "charset_position": 41, "consumable": True}
        ]
    }
    with open(world_dir / "items.yaml", "w", encoding="utf-8") as f:
        yaml.dump(items_data, f, allow_unicode=True)

    r_dir = world_dir / "R1"
    r_dir.mkdir(parents=True, exist_ok=True)
    (r_dir / "region.yaml").write_text("id: R1\nname: Region 1\nlayout: {rows: 1, columns: 1}\nstart_screen: S1\nmusic: NONE\n", encoding="utf-8")
    
    s_dir = r_dir / "screens"
    s_dir.mkdir(parents=True, exist_ok=True)
    (s_dir / "S1.yaml").write_text("id: S1\nexits: {north: null, south: null, east: null, west: null}\nobjects: []\n", encoding="utf-8")

    game_world = parse_world_dir(world_dir)
    assert len(game_world.inventory_items) == 2
    assert game_world.inventory_items[0].id == 1
    assert game_world.inventory_items[0].description == "Miecz wiedźmiński"
    assert game_world.inventory_items[0].charset_position == 40
    assert game_world.inventory_items[0].consumable is False
    assert game_world.inventory_items[1].consumable is True
