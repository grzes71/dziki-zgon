import json
import pytest
from pathlib import Path
from scripts.export_portal_data import (
    PortalDataPipeline,
    GamePortalData,
    WorldPortalData,
    ObjectsPortalData,
    SpritesPortalData,
    AssetsPortalData,
    MusicPortalData,
    MemoryPortalData,
    ReleasesPortalData,
    LatestPortalData,
)

def test_portal_data_generation_and_schemas(tmp_path):
    root_dir = Path(__file__).resolve().parent.parent
    out_dir = tmp_path / "portal"

    pipeline = PortalDataPipeline(root_dir=root_dir, output_dir=out_dir)
    pipeline.run()

    expected_files = [
        "game.json",
        "world.json",
        "objects.json",
        "sprites.json",
        "assets.json",
        "music.json",
        "memory.json",
        "releases.json",
        "latest.json",
    ]

    for fname in expected_files:
        fpath = out_dir / fname
        assert fpath.exists(), f"Missing {fname}"
        assert fpath.stat().st_size > 0, f"Empty {fname}"

        content = json.loads(fpath.read_text(encoding="utf-8"))
        assert isinstance(content, dict), f"{fname} is not a JSON object"

    # Validate against models dynamically without hardcoding volatile counts
    game = GamePortalData.model_validate_json((out_dir / "game.json").read_text(encoding="utf-8"))
    assert game.title == "Dziki Zgon"
    assert game.stats.regions_count > 0
    assert game.stats.screens_count > 0

    world = WorldPortalData.model_validate_json((out_dir / "world.json").read_text(encoding="utf-8"))
    assert len(world.regions) == game.stats.regions_count
    assert world.screens_count == game.stats.screens_count
    assert len(world.transitions) > 0

    objects = ObjectsPortalData.model_validate_json((out_dir / "objects.json").read_text(encoding="utf-8"))
    assert objects.total_unique_objects > 0
    assert objects.total_unique_enemies > 0
    assert objects.total_unique_items > 0

    sprites = SpritesPortalData.model_validate_json((out_dir / "sprites.json").read_text(encoding="utf-8"))
    assert sprites.sprites_count > 0
    assert len(sprites.pmg_bitmaps) == 2

    music = MusicPortalData.model_validate_json((out_dir / "music.json").read_text(encoding="utf-8"))
    assert music.tracks_count >= 5

    mem = MemoryPortalData.model_validate_json((out_dir / "memory.json").read_text(encoding="utf-8"))
    assert len(mem.segments) > 0
    assert len(mem.zero_page) > 0
    assert mem.safe_free_headroom_bytes > 0
    assert mem.reserved_headroom_bytes > 0
    assert mem.safe_free_headroom_bytes + mem.reserved_headroom_bytes == mem.free_headroom_bytes
    assert mem.total_mapped_bytes + mem.free_headroom_bytes == 49152
    assert mem.binary_provenance is not None
