import pytest
from pathlib import Path
from world_studio.project_manager import ProjectManager
from world_studio.models import PortalEntry

def test_portal_entry_model_and_save(tmp_path):
    # Setup test project directory
    world_dir = tmp_path / "world"
    world_dir.mkdir()
    (world_dir / "world.yaml").write_text("world:\n  start_region: R1\n  start_screen: S1\n  start_position: {x: 1, y: 1}\n", encoding="utf-8")
    
    r1_dir = world_dir / "R1"
    r1_dir.mkdir()
    (r1_dir / "region.yaml").write_text("id: R1\nname: Region 1\nlayout: {rows: 1, columns: 1}\nstart_screen: S1\nmusic: NONE\n", encoding="utf-8")
    (r1_dir / "screens").mkdir()
    (r1_dir / "screens" / "S1.yaml").write_text("id: S1\nexits: {}\nobjects: []\n", encoding="utf-8")

    pm = ProjectManager()
    assert pm.load_project(world_dir) is True

    # Set portal entry from R2
    region = pm.regions["R1"]
    region.portal_entries["R2"] = PortalEntry(screen="S1", x=10, y=5)

    assert pm.save_project() is True

    # Reload project and verify portal entry
    pm2 = ProjectManager()
    assert pm2.load_project(world_dir) is True
    reloaded_reg = pm2.regions["R1"]
    assert "R2" in reloaded_reg.portal_entries
    entry = reloaded_reg.portal_entries["R2"]
    assert entry.screen == "S1"
    assert entry.x == 10
    assert entry.y == 5
