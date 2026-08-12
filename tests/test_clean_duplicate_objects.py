import pytest
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

from scripts.clean_duplicate_objects import main

def test_clean_duplicate_objects(tmp_path, capsys):
    # Set up temp folder layout
    world_dir = tmp_path / "world"
    world_dir.mkdir()
    
    objects_file = world_dir / "objects.yaml"
    objects_data = {
        "objects": [
            {
                "id": "OBJ_A",
                "code": 1,
                "size": {"width": 2, "height": 2},
                "tiles": [10, 11, 12, 13]
            },
            {
                "id": "OBJ_B",
                "code": 2,
                "size": {"width": 2, "height": 2},
                "tiles": [10, 11, 12, 13] # duplicate of A
            },
            {
                "id": "OBJ_C",
                "code": 3,
                "size": {"width": 2, "height": 2},
                "tiles": [20, 21, 22, 23]
            }
        ]
    }
    with objects_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump(objects_data, f)
        
    screens_dir = world_dir / "REGION1" / "screens"
    screens_dir.mkdir(parents=True)
    
    screen_file = screens_dir / "SCREEN1.yaml"
    screen_data = {
        "id": "SCREEN1",
        "objects": [
            {"object": "OBJ_B", "x": 0, "y": 0},
            {"object": "OBJ_C", "x": 4, "y": 4},
            {"object": "OBJ_NON_EXISTENT", "x": 8, "y": 8} # Should be removed
        ]
    }
    with screen_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump(screen_data, f)

    # Mock Path(__file__) chain to return real Path(tmp_path) at parent.parent
    mock_path_instance = MagicMock()
    mock_path_instance.resolve.return_value.parent.parent = tmp_path
    
    # 1. Dry Run test
    with patch("scripts.clean_duplicate_objects.Path", return_value=mock_path_instance), \
         patch.object(sys, "argv", ["clean_duplicate_objects.py"]):
         
        main()
        
    captured = capsys.readouterr()
    assert "Group 1:" in captured.out
    assert "Proper (first occurrence): OBJ_A" in captured.out
    assert "Duplicate: OBJ_B" in captured.out
    assert "remove 1 invalid reference(s)" in captured.out
    assert "Dry-run completed" in captured.out

    # Verify files were NOT modified in dry-run
    with objects_file.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert len(data["objects"]) == 3
    
    with screen_file.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert len(data["objects"]) == 3
    assert data["objects"][0]["object"] == "OBJ_B"

    # 2. Fix mode test
    with patch("scripts.clean_duplicate_objects.Path", return_value=mock_path_instance), \
         patch.object(sys, "argv", ["clean_duplicate_objects.py", "--fix"]):
         
        main()

    captured = capsys.readouterr()
    assert "Updated" in captured.out
    assert "Cleanup Finished" in captured.out
    assert "Duplicate object definitions to remove from objects.yaml: 1" in captured.out
    assert "Duplicate instances to replace in screens: 1" in captured.out
    assert "Invalid object instances to remove from screens: 1" in captured.out

    # Verify objects.yaml was updated (duplicate removed)
    with objects_file.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert len(data["objects"]) == 2
    assert [obj["id"] for obj in data["objects"]] == ["OBJ_A", "OBJ_C"]

    # Verify screen file was updated (OBJ_B replaced with OBJ_A, OBJ_NON_EXISTENT removed)
    with screen_file.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert len(data["objects"]) == 2
    assert data["objects"][0]["object"] == "OBJ_A"
    assert data["objects"][1]["object"] == "OBJ_C"
